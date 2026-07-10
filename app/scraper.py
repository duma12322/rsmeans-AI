import asyncio
import re
from playwright.async_api import async_playwright

from app.db import init_db, save_to_db, log_error
from app.utils import clean_number, format_currency
from app.navigator import (
    find_path,
    needs_clarification,
    build_clarification_response,
    build_item_clarification,
    build_broad_clarification,
    search_term,
)
from app.tree_ai import suggest_refinements
from app.session import is_session_valid, save_session, SESSION_FILE
from app.config import RS_EMAIL, RS_PASSWORD
from app.cancellation import ScrapeCancelled, check_cancel as _check_cancel


# RSMeans credentials, read from .env (RS_EMAIL / RS_PASSWORD). Re-exported under
# these names because app/record_scraper.py imports EMAIL/PASSWORD from here.
EMAIL = RS_EMAIL
PASSWORD = RS_PASSWORD


# =========================
# NORMALIZE
# =========================
def normalize(t):
    return " ".join(t.split()).strip() if t else ""


# =========================
# LOGIN (VERIFIED)
# =========================
class LoginError(Exception):
    """RSMeans rejected the login, the flow changed, or credentials are missing.

    Raised instead of silently saving an invalid session and then scraping the
    wrong grid — a stale/failed login must never look like success.
    """


async def perform_login(page, context, email, password):
    """Log into RSMeans and verify it actually worked BEFORE caching the session.

    The old flow just clicked through and waited a fixed 5s, so a wrong password
    or a changed login page would still `save_session` and the scrape would walk
    a grid behind a logged-out wall. Here we submit, then wait for the page to
    settle into EITHER the post-login catalog link (success) or the site's
    `#errorMessage` alert (e.g. "Invalid email or password") and raise on the
    latter. Caller is expected to be on https://www.rsmeansonline.com/.
    """
    if not email or not password:
        raise LoginError(
            "RSMeans login no configurado: define RS_EMAIL y RS_PASSWORD en el "
            "archivo .env."
        )

    await page.click("#btnLogin")
    await page.fill("#username", email)
    await page.click("button[type='submit']")
    await page.fill("#password", password)
    await page.click("#btnTerms")

    # Wait until the page resolves into one of the two known outcomes: the
    # logged-in catalog link, or the error alert. wait_for_selector defaults to
    # state="visible", so the always-in-DOM-but-hidden error div won't match
    # until it's actually shown.
    try:
        await page.wait_for_selector(
            "#errorMessage, a#\\/SearchData",
            timeout=20000,
        )
    except Exception as e:
        raise LoginError(
            "Tiempo de espera agotado durante el login de RSMeans (el flujo de "
            "login pudo haber cambiado)."
        ) from e

    error_el = await page.query_selector("#errorMessage")
    if error_el and await error_el.is_visible():
        detail = normalize(await error_el.inner_text())
        # El sitio responde en inglés ("Invalid email or password"); lo mostramos
        # en español. El texto crudo del sitio queda en el log para diagnóstico.
        if detail:
            print(f"[login] RSMeans error message: {detail}")
        if not detail or "invalid email or password" in detail.lower():
            reason = "email o contraseña inválidos"
        else:
            reason = detail
        raise LoginError(f"RSMeans rechazó el login: {reason}.")

    # Verified: now it's safe to cache the session.
    await save_session(context)


# =========================
# TREE READY
# =========================
async def wait_tree_ready(page):
    for _ in range(30):
        node = await page.query_selector("#leftTreeMenu > ul > li")
        if node:
            txt = (await node.inner_text()).strip()
            if "Loading" not in txt:
                return
        await asyncio.sleep(1)

    raise Exception("TREE NOT READY")


# =========================
# SAFE CELL VALUE (FULL FALLBACK)
# =========================
async def get_cell_value(cell):
    try:
        txt = (await cell.inner_text()).strip()
        if txt and txt not in ["—", "-", ""]:
            return txt

        title = await cell.get_attribute("title")
        if title:
            return title.strip()

        data_value = await cell.get_attribute("data-value")
        if data_value:
            return data_value.strip()

        input_el = await cell.query_selector("input")
        if input_el:
            val = await input_el.get_attribute("value")
            if val:
                return val.strip()

        return ""
    except Exception as e:
        # Tolerate an unreadable cell (don't blow up the whole scrape) but leave a
        # trace: a silent "" here used to hide RSMeans DOM changes / detached nodes.
        print(f"[scraper] no se pudo leer una celda (devuelvo vacio): {e}")
        return ""


# =========================
# WAIT FOR REAL RSMeans DATA (CRITICAL FIX)
# =========================
async def wait_rsmeans_data(page):

    # espera request real de jqGrid / search
    try:
        await page.wait_for_response(lambda r:
            ("jqgrid" in r.url.lower() or "search" in r.url.lower())
        , timeout=15000)
    except Exception as e:
        # The XHR may have fired before we started listening, so this isn't fatal —
        # we still wait on the DOM below. But log it: a timeout here can also mean
        # the grid never loaded, and we don't want that to pass unnoticed.
        print(f"[scraper] no observe la XHR de jqGrid/search en 15s "
              f"(sigo esperando el DOM): {e}")

    # espera render DOM final
    await page.wait_for_function("""
    () => {
        const rows = document.querySelectorAll('tr.jqgrow');
        if (!rows.length) return false;

        return Array.from(rows).some(r =>
            r.innerText.includes('$') ||
            /\\d+\\.\\d+/.test(r.innerText)
        );
    }
    """, timeout=20000)

    await page.wait_for_timeout(2000)


# =========================
# COLUMN DETECTION (NO INDEXES)
# =========================
async def get_column_map(page):
    headers = await page.query_selector_all("table.ui-jqgrid-htable th")

    col_map = {}

    for i, h in enumerate(headers):
        text = normalize(await h.inner_text()).lower()
        col_map[text] = i

    return col_map


def find_col(col_map, keyword):
    for k, v in col_map.items():
        if keyword.lower() in k:
            return v
    return None


# =========================
# SCRAPE GRID (ROBUST)
# =========================
# jqGrid identifies every column with aria-describedby="grid_<Column>". Selecting
# cells by that id is robust to column reordering and hidden columns, unlike the
# old positional indexes. Note: grid_UnitLineNumber is the VISIBLE line number
# (grid_LineNumber is a separate, hidden, empty column).
_GRID_COLS = {
    "line_number": "grid_UnitLineNumber",
    "description": "grid_Description",
    "unit": "grid_UnitOfMeasureCode",
    "bare_total": "grid_Total",
    "total_op": "grid_TotalOP",
    # Hidden per-row flag: "true" when Bare Total / Total O&P are PERCENTAGES (a
    # cost adjustment / add-on), not dollar amounts. Drives how the UI formats them.
    "percent_line": "grid_PercentLine",
}


async def _col_value(row, col_id):
    cell = await row.query_selector(f'td[aria-describedby="{col_id}"]')
    if not cell:
        return ""
    return normalize(await get_cell_value(cell))


async def _read_description(row):
    """
    Return (text, indent) for the Description cell.

    RSMeans encodes the outline nesting as a CSS class on an inner div:
    `<div class="ind2">Aluminum pole, 8' high</div>`. A deeper sub-item has a
    higher number; a top-level header has no `indN` div (indent 0). We surface
    that depth so the UI can reproduce the indented outline the site shows,
    instead of flattening every row to the left margin.
    """
    cell = await row.query_selector(f'td[aria-describedby="{_GRID_COLS["description"]}"]')
    if not cell:
        return "", 0

    text = normalize(await get_cell_value(cell))

    indent = 0
    inner = await cell.query_selector('div[class*="ind"]')
    if inner:
        cls = await inner.get_attribute("class") or ""
        m = re.search(r"\bind(\d+)\b", cls)
        if m:
            indent = int(m.group(1))
    return text, indent


async def _read_grid_rows(page):
    """Read the line-items currently rendered in the jqGrid body — no waiting.
    Split out from scrape_grid so the search path can re-read the grid after it
    asks for a bigger page, without paying wait_rsmeans_data's XHR wait again."""
    rows = await page.query_selector_all(
        "table.ui-jqgrid-btable tr.jqgrow"
    )

    data = []

    for row in rows:

        description, indent = await _read_description(row)

        # Rows without a description are grid chrome, not line-items.
        if not description:
            continue

        is_percent = (
            await _col_value(row, _GRID_COLS["percent_line"])
        ).strip().lower() == "true"

        data.append({
            "line_number": await _col_value(row, _GRID_COLS["line_number"]),
            "description": description,
            "indent": indent,
            "unit": await _col_value(row, _GRID_COLS["unit"]),
            "bare_total": clean_number(await _col_value(row, _GRID_COLS["bare_total"])),
            "total_op": clean_number(await _col_value(row, _GRID_COLS["total_op"])),
            "is_percent": is_percent,
        })

    return data


async def scrape_grid(page):
    await wait_rsmeans_data(page)
    return await _read_grid_rows(page)


# =========================
# SEARCH RESULT COUNT / PAGE SIZE
# =========================
# The site's own results counter reads "Total 719 records found". Above this many
# hits we pull more than the default first page (up to SEARCH_MAX_ROWS); above the
# max we stop and tell the user to narrow the search instead of dumping thousands.
SEARCH_BUMP_THRESHOLD = 50
SEARCH_MAX_ROWS = 200


async def _read_total_records(page):
    """Parse the grid pager's 'Total N records found' counter. Returns the int,
    or None when it isn't present/parseable (then we just scrape the first page)."""
    try:
        el = await page.query_selector(".ui-paging-info")
        if not el:
            return None
        txt = (await el.inner_text()) or ""
        m = re.search(r"(\d[\d,]*)\s*records", txt, re.I) or re.search(r"(\d[\d,]*)", txt)
        return int(m.group(1).replace(",", "")) if m else None
    except Exception as e:  # noqa: BLE001
        print(f"[search] no pude leer el contador de resultados: {e}")
        return None


async def _load_more_rows(page, target):
    """Ask the jqGrid to fetch up to `target` rows in a single page and reload, so
    it renders more than the default first page. The grid id is 'grid' — the same
    prefix the column ids use (aria-describedby='grid_<Column>')."""
    await page.evaluate(
        """(n) => {
            if (window.jQuery && jQuery('#grid').length) {
                jQuery('#grid').jqGrid('setGridParam', {rowNum: n, page: 1})
                               .trigger('reloadGrid');
            }
        }""",
        target,
    )


async def _wait_row_count(page, at_least, timeout=40000):
    """Wait until the grid has rendered at least `at_least` rows (after a bigger
    page was requested), then let the render settle. Best-effort: on timeout we
    scrape whatever loaded rather than fail the search."""
    try:
        await page.wait_for_function(
            "(n) => document.querySelectorAll("
            "'table.ui-jqgrid-btable tr.jqgrow').length >= n",
            arg=at_least,
            timeout=timeout,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[search] no alcance {at_least} filas a tiempo "
              f"(sigo con las cargadas): {e}")
    await page.wait_for_timeout(1500)


# =========================
# MATCH A SCRAPED ROW TO AN EXPLICIT LINE NUMBER
# =========================
def match_scraped_line(rows, code):
    """
    Find the scraped grid row whose visible Line Number matches the requested
    RSMeans code, for a direct code lookup. Matching is digits-only (so
    "265613102870", "26 56 13. 10 2870", etc. all match the same row). Prefers
    an exact line, otherwise the first line that starts with the code (a short /
    section-level code). Returns the row dict (line_number, description, costs)
    or None.
    """
    if not rows or not code:
        return None

    code = "".join(ch for ch in str(code) if ch.isdigit())
    if not code:
        return None

    prefix_hit = None
    for r in rows:
        line = "".join(ch for ch in str(r.get("line_number", "")) if ch.isdigit())
        if not line:
            continue
        if line == code:
            return r
        if prefix_hit is None and line.startswith(code):
            prefix_hit = r
    return prefix_hit


def _with_display(row):
    """Attach human-readable display strings without losing the raw numeric values.
    Percentage rows (`is_percent`) render as "10%", everything else as currency
    ("$1,234.50"); `bare_total`/`total_op` stay raw floats for sorting or math."""
    if not row:
        return row

    def _display(value):
        if row.get("is_percent"):
            if value in (None, "", 0):
                return None
            try:
                return f"{float(value):g}%"
            except (TypeError, ValueError):
                return None
        return format_currency(value)

    return {
        **row,
        "bare_total_display": _display(row.get("bare_total")),
        "total_op_display": _display(row.get("total_op")),
    }


def build_breadcrumb(hops):
    """The chosen route as an ordered list of {code, name} so the frontend can
    render the taxonomy path specifically (e.g. "23 - Electrical" > "2301 - ...")."""
    return [{"code": h["code"], "name": h["name"]} for h in hops]


def filter_rows_by_code(rows, code):
    """
    Keep only the rows whose visible Line Number starts with the requested code
    (digits-only). A full 12-digit line number returns a single row; a shorter
    section code (e.g. "265613.10") is a prefix of every line in its grid, so it
    returns them all. When no code was given, or nothing matches, return `rows`
    unchanged so we never hand back an empty result.
    """
    if not rows or not code:
        return rows

    code = "".join(ch for ch in str(code) if ch.isdigit())
    if not code:
        return rows

    filtered = [
        r for r in rows
        if "".join(ch for ch in str(r.get("line_number", "")) if ch.isdigit()).startswith(code)
    ]
    return filtered or rows


# =========================
# PARSE TREE
# =========================
async def parse_nodes(nodes):
    result = []

    for n in nodes:
        t = normalize(await n.inner_text())
        parts = t.split(" ", 1)

        code = parts[0]
        name = parts[1] if len(parts) > 1 else ""

        result.append({
            "code": code,
            "name": name,
            "node": n
        })

    return result


# =========================
# NAVIGATE A CHOSEN PATH (VARIABLE DEPTH)
# =========================
async def _read_level(page, parent):
    """(Re)read the nodes that make up the current tree level: the root list when
    `parent` is None, otherwise the children of the node we last opened. Used both
    for the initial read and to refresh a level that a slow render left stale."""
    if parent is None:
        nodes = await page.query_selector_all("#leftTreeMenu > ul > li")
    else:
        nodes = await parent.query_selector_all(":scope > ul > li")
    return await parse_nodes(nodes)


async def navigate_path(page, path, cancel=None, retries=2):
    """
    Click down the tree following the codes in `path`, to whatever depth the
    leaf lives at (no hardcoded number of levels).

    Returns True if every code was found and clicked, False otherwise. Checks the
    cancel token before each hop so a paused request stops mid-walk.

    Each hop is retried with exponential backoff: a click that times out or a
    child level that hasn't rendered yet is usually just slowness, so we back off
    and re-read the level instead of letting one hiccup doom the whole walk.
    """
    parent = None  # node whose children are the current level; None == root
    siblings = await _read_level(page, parent)

    for code in path:
        _check_cancel(cancel)

        for attempt in range(retries + 1):
            _check_cancel(cancel)
            try:
                by_code = {n["code"]: n for n in siblings}
                target = by_code.get(code)
                if target is None:
                    # May just not have rendered yet after the previous click;
                    # treat as transient so the retry below re-reads the level.
                    raise LookupError(f"code {code} not in current level yet")

                await target["node"].click()
                await page.wait_for_timeout(1200)

                # Children of the node we just opened become the next level.
                siblings = await _read_level(page, target["node"])
                parent = target["node"]
                break  # hop succeeded
            except ScrapeCancelled:
                raise
            except Exception as e:
                print(f"[navigate] hop {code} fallo "
                      f"(intento {attempt + 1}/{retries + 1}): {e}")
                if attempt >= retries:
                    print(f"[navigate] code {code} irrecuperable tras "
                          f"{retries + 1} intentos -> abandono la ruta")
                    return False
                await page.wait_for_timeout(int(1000 * (2 ** attempt)))
                # Refresh the current level from the DOM in case a slow render is
                # why the node was missing or the click didn't take.
                siblings = await _read_level(page, parent)

    return True


# =========================
# ROUTING (OFFLINE, NO BROWSER)
# =========================
def route_question(question, start_path=None, cancel=None):
    """
    Decide the route fully offline — no browser. Returns (route, clarification):

    - clarification is None and `route` is a confident path to a leaf, OR
    - clarification is a needs_clarification response (candidates + questions)
      when the request is too ambiguous to scrape; `route` may still carry the
      candidates we found.

    `start_path` locks a branch the user already committed to during a
    multi-turn clarification, so routing drills down from there.

    Doing this BEFORE launching Chromium means clarification turns are fast and
    never open a browser — the browser only ever walks a single chosen path.

    `cancel` (a threading.Event) lets the beam search stop deliberating mid-way
    when the client disconnects, instead of running every AI hop first.
    """
    route = find_path(question, start_path=start_path, cancel=cancel)

    # Single broad word ("steel"): ask the user to add a detail instead of
    # navigating or dumping the whole catalog.
    if route and route.get("match_type") == "too_broad":
        return route, build_broad_clarification(
            question, route.get("term"), route.get("broad_kind", "property")
        )

    # Text-match candidates: present the real items found, not divisions.
    if route and route.get("match_type") == "item" and route.get("ambiguous"):
        return route, build_item_clarification(question, route["candidates"])

    route_meta = {
        "confidence": route["confidence"] if route else "low",
        "candidates": route["candidates"] if route else [],
        "clarify_questions": route["clarify_questions"] if route else [],
        "ambiguous": route["ambiguous"] if route else True,
    }
    if route is None or not route["path"] or needs_clarification(route_meta):
        print("\n[BEAM] ruta no confiable -> se presentan candidatos y preguntas")
        clarification = build_clarification_response(
            question, route["path"] if route else [], route_meta
        )
        return route, clarification
    return route, None


# =========================
# SCRAPE A CONFIDENT ROUTE (BROWSER)
# =========================
async def scrape_route(question, route, progress=None, cancel=None):
    """
    Open the browser, walk the already-chosen route, scrape and return.

    Any live-site failure (login flow changed, grid never loads, a timeout, or a
    path code missing from the live tree) is caught and turned into a useful
    `status: "error"` response instead of a raw exception that would kill the
    request with no message. The browser is always closed.

    `cancel` is an optional threading.Event: when the API marks it (client
    disconnected), the next checkpoint raises ScrapeCancelled, the browser is
    closed in `finally`, and we return a `status: "cancelled"` response instead of
    finishing the whole scrape in the background.
    """
    init_db()
    emit = progress or (lambda *a, **k: None)

    path = route["path"]
    hops = route["hops"]
    final_name = hops[-1]["name"] if hops else ""

    def _error(message, exc=None):
        if exc is not None:
            print(f"[scrape] ERROR: {exc}")
        log_error(question, path, message, exc)
        return {
            "status": "error",
            "message": message,
            "error": str(exc) if exc is not None else None,
            "path": path,
            "confidence": route.get("confidence"),
            "clarify_questions": route.get("clarify_questions", []),
        }

    browser = None
    try:
        async with async_playwright() as p:

            _check_cancel(cancel)
            emit("opening")  # entrando al sitio en vivo de RSMeans
            browser = await p.chromium.launch(headless=False)

            context = await browser.new_context(
                storage_state=SESSION_FILE if is_session_valid() else None
            )

            page = await context.new_page()

            await page.goto("https://www.rsmeansonline.com/")

            # ================= LOGIN =================
            if not is_session_valid():
                _check_cancel(cancel)
                emit("login")  # sesion expirada: autenticando de nuevo
                try:
                    await perform_login(page, context, EMAIL, PASSWORD)
                except LoginError as e:
                    # Don't scrape behind a logged-out wall: surface the reason.
                    return _error(str(e), exc=e)

            # ================= NAV =================
            _check_cancel(cancel)
            await page.click("a#\\/SearchData")

            await wait_tree_ready(page)

            print("\nCHOSEN PATH:", " -> ".join(path))
            print("ROUTE CONFIDENCE:", route["confidence"])

            # ================= NAVIGATE THE CHOSEN PATH (VARIABLE DEPTH) =======
            emit("navigating")  # recorriendo la ruta elegida en el catalogo
            navigated = await navigate_path(page, path, cancel=cancel)
            if not navigated:
                # A code in our snapshot path was not found in the live tree
                # (tree.json went stale). Don't scrape the wrong grid — say so.
                return _error(
                    "No pude seguir la ruta elegida en el catalogo en vivo de "
                    "RSMeans (la taxonomia pudo haber cambiado). Intenta "
                    "reformular la consulta o vuelve a intentar."
                )

            # IMPORTANT: WAIT FOR REAL DATA
            _check_cancel(cancel)
            emit("scraping")  # esperando y leyendo la grilla de precios en vivo
            await wait_rsmeans_data(page)

            # ================= GRID =================
            rows = await scrape_grid(page)

            if rows:
                save_to_db(
                    rows=rows,
                    question=question,
                    c3=path[-2] if len(path) >= 2 else None,
                    c4=path[-1],
                    final_code=path[-1],
                    final_name=final_name,
                    path=path,
                )

            # If the user asked for an explicit code (direct code lookup), narrow
            # the rows we RETURN to exactly what was asked. We always SAVE the
            # full grid above (richer knowledge base); only the response is
            # focused:
            #   - full 12-digit line number -> just that one line
            #   - shorter section code (e.g. 265613.10) -> all lines under it
            # The whole grid is kept under `all_rows` so nothing is lost.
            requested_code = route.get("requested_code")
            all_rows = rows
            rows = filter_rows_by_code(all_rows, requested_code)

            # The single best (exact) line, for a one-shot "line + costs" answer.
            matched_line = match_scraped_line(all_rows, route.get("matched_line"))

            print("\nFINAL PATH:", " -> ".join(path))
            print(f"FINAL NODE: {path[-1]} - {final_name}")
            if requested_code:
                print(f"CODIGO PEDIDO: {requested_code} -> devuelvo {len(rows)} "
                      f"linea(s) de {len(all_rows)} en la seccion")
            if matched_line:
                print(f"LINEA EXACTA: {matched_line['line_number']} - "
                      f"{matched_line['description']} | "
                      f"bare={matched_line['bare_total']} O&P={matched_line['total_op']}")

            return {
                "status": "ok",
                "rows": [_with_display(r) for r in rows],
                "matched_line": _with_display(matched_line),
                "breadcrumb": build_breadcrumb(hops),
                "path": path,
                "final_code": path[-1],
                "final_name": final_name,
                "confidence": route["confidence"],
                "fallback_used": route["fallback_used"] or not navigated,
                "clarify_questions": route.get("clarify_questions", []),
            }

    except ScrapeCancelled:
        # Client disconnected (Stop in the UI): unwind to `finally` to close the
        # browser. Not an error — don't log it; the caller discards this response.
        print("[scrape] cancelado por el cliente (peticion pausada)")
        return {
            "status": "cancelled",
            "message": "Consulta pausada: el cliente detuvo la peticion.",
            "path": path,
        }
    except Exception as e:  # noqa: BLE001 - any live-site failure -> useful error
        return _error(
            "There was a problem querying RSMeans live (login, grid loading, or "
            "a timeout). Please try again in a moment.",
            exc=e,
        )
    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception as e:
                # A failed close shouldn't mask the real result, but log it so a
                # leaked browser process isn't completely invisible.
                print(f"[scraper] error al cerrar el navegador (ignorado): {e}")


# =========================
# KEYWORD SEARCH (BROWSER) — mirrors the RSMeans search box
# =========================
async def scrape_search(question, term, progress=None, cancel=None):
    """
    Type `term` into the RSMeans search box and scrape the whole results grid —
    the app doing exactly what a user would do in the site's search field. Used
    for keyword queries ("scissor") where there's no single right leaf: instead
    of asking "which do you mean?", we return every matching line so the user
    browses and picks, like a real search.

    Reuses the same login, grid scraping and currency formatting as the
    navigate-and-scrape path; only the "how we reach the grid" differs (search
    box vs walking the tree).
    """
    init_db()
    emit = progress or (lambda *a, **k: None)

    def _error(message, exc=None):
        if exc is not None:
            print(f"[search] ERROR: {exc}")
        log_error(question, [], message, exc)
        return {"status": "error", "message": message,
                "error": str(exc) if exc is not None else None}

    browser = None
    try:
        async with async_playwright() as p:
            _check_cancel(cancel)
            emit("opening")
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                storage_state=SESSION_FILE if is_session_valid() else None
            )
            page = await context.new_page()
            await page.goto("https://www.rsmeansonline.com/")

            if not is_session_valid():
                _check_cancel(cancel)
                emit("login")
                try:
                    await perform_login(page, context, RS_EMAIL, RS_PASSWORD)
                except LoginError as e:
                    return _error(str(e), exc=e)

            _check_cancel(cancel)
            await page.click("a#\\/SearchData")
            await wait_tree_ready(page)

            # ===== TYPE THE KEYWORD AND RUN THE SITE SEARCH =====
            _check_cancel(cancel)
            emit("navigating")  # escribiendo el termino en el buscador de RSMeans
            print(f"\n>>> BUSQUEDA EN VIVO: escribiendo {term!r} en el buscador")
            await page.fill("#searchTextBox", term)
            # "all" = a line matches only if it contains EVERY word (an AND), which
            # is also the site's own default. This is what makes "add a
            # characteristic to narrow it down" actually work: refining "pipe" to
            # "pipe steel" must SHRINK the set to lines carrying both words, not
            # broaden it. ("any" is an OR — adding a word would return MORE rows,
            # contradicting the guided-narrowing UX.) The SEARCH_MAX_ROWS cap + the
            # "add more detail" notice still handle a single broad word.
            try:
                await page.select_option("#drpSearch", "all")
            except Exception:
                pass  # keep the site's default preference if the select changed
            await page.click("#search-btn1")

            _check_cancel(cancel)
            emit("scraping")

            # The first page is in. Read the site's own counter to decide how many
            # rows to pull: <=50 -> the first page is fine; >50 -> load up to
            # SEARCH_MAX_ROWS; beyond that -> load the cap and tell the user to
            # narrow the search.
            await wait_rsmeans_data(page)
            total = await _read_total_records(page)
            truncated = False
            notice = None

            if total is not None and total > SEARCH_BUMP_THRESHOLD:
                target = min(total, SEARCH_MAX_ROWS)
                print(f">>> {total} registros encontrados -> cargo hasta {target} filas")
                _check_cancel(cancel)
                await _load_more_rows(page, target)
                await _wait_row_count(page, min(target, total))
                truncated = total > SEARCH_MAX_ROWS

            rows = await _read_grid_rows(page)

            refine_questions = []
            refinements = []
            if truncated:
                notice = (
                    f"Found {total:,} matches — showing the first {len(rows)}. "
                    "That's a lot to be exact about; add more detail (the object, "
                    "material, size, or type) to get a shorter, more precise list."
                )
                # Guide the narrowing: ask the model, using the rows we actually
                # pulled, which dimensions vary and what to add. Best-effort — a
                # failure just leaves the plain notice above.
                _check_cancel(cancel)
                hints = suggest_refinements(
                    question, [r.get("description", "") for r in rows]
                )
                refine_questions = hints["questions"]
                refinements = hints["refinements"]

            if rows:
                save_to_db(
                    rows=rows, question=question, c3=None, c4=None,
                    final_code=None, final_name=f"search: {term}", path=None,
                )

            print(f">>> BUSQUEDA {term!r} -> {len(rows)} fila(s) de "
                  f"{total if total is not None else '?'} totales"
                  f"{' (truncado, pido acotar)' if truncated else ''}")
            return {
                "status": "ok",
                "mode": "search",
                "search_term": term,
                "rows": [_with_display(r) for r in rows],
                "matched_line": None,
                "breadcrumb": [],
                "path": [],
                "final_code": None,
                "final_name": f"Search results for “{term}”",
                "confidence": "high",
                "fallback_used": False,
                "clarify_questions": [],
                "total_records": total,
                "shown_records": len(rows),
                "truncated": truncated,
                "notice": notice,
                # When truncated: AI-suggested ways to narrow, shown as clickable
                # chips + follow-up questions that append to the original query.
                "refine_questions": refine_questions,
                "refinements": refinements,
            }

    except ScrapeCancelled:
        print("[search] cancelado por el cliente (peticion pausada)")
        return {"status": "cancelled",
                "message": "Consulta pausada: el cliente detuvo la peticion."}
    except Exception as e:  # noqa: BLE001
        return _error(
            "There was a problem running the RSMeans search (login, grid "
            "loading, or a timeout). Please try again in a moment.",
            exc=e,
        )
    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception as e:
                print(f"[search] error al cerrar el navegador (ignorado): {e}")


# =========================
# SINGLE-SHOT ENTRY (route offline first, browser only if confident)
# =========================
async def start_browser(question, start_path=None, progress=None, cancel=None):
    emit = progress or (lambda *a, **k: None)
    try:
        emit("analyzing")  # IA recorriendo el arbol offline (todavia sin navegador)
        _check_cancel(cancel)
        route, clarification = route_question(question, start_path=start_path, cancel=cancel)
        if clarification is not None:
            # A single broad word ("steel"): don't open a browser at all — ask the
            # user to add a detail and complete the search (no live search dump).
            if route and route.get("match_type") == "too_broad":
                print("[start] termino demasiado amplio -> pido aclaracion "
                      "(sin abrir navegador)")
                return clarification
            # Ambiguous keyword query: behave like the RSMeans search box — type
            # the keyword, scrape ALL matches, let the user browse. Only fall back
            # to the follow-up questions if the live search finds nothing.
            term = search_term(question)
            if term:
                print(f"[start] consulta ambigua -> BUSQUEDA en vivo con {term!r}")
                results = await scrape_search(
                    question, term, progress=progress, cancel=cancel
                )
                if results.get("status") == "ok" and results.get("rows"):
                    return results
                if results.get("status") == "cancelled":
                    return results
            return clarification
        return await scrape_route(question, route, progress=progress, cancel=cancel)
    except ScrapeCancelled:
        # Cancelled during offline analysis (before the browser opened): nothing
        # to clean up. scrape_route handles cancellation during the browser phase.
        print("[analysis] cancelado por el cliente (peticion pausada)")
        return {
            "status": "cancelled",
            "message": "Consulta pausada: el cliente detuvo la peticion.",
        }