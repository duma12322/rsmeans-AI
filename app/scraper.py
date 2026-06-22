import asyncio
from playwright.async_api import async_playwright

from app.db import init_db, save_to_db, log_error
from app.utils import clean_number
from app.navigator import (
    find_path,
    needs_clarification,
    build_clarification_response,
    build_item_clarification,
)
from app.session import is_session_valid, save_session, SESSION_FILE
from app.config import RS_EMAIL, RS_PASSWORD


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
    except:
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
    except:
        pass

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
}


async def _col_value(row, col_id):
    cell = await row.query_selector(f'td[aria-describedby="{col_id}"]')
    if not cell:
        return ""
    return normalize(await get_cell_value(cell))


async def scrape_grid(page):

    await wait_rsmeans_data(page)

    rows = await page.query_selector_all(
        "table.ui-jqgrid-btable tr.jqgrow"
    )

    data = []

    for row in rows:

        description = await _col_value(row, _GRID_COLS["description"])

        # Rows without a description are grid chrome, not line-items.
        if not description:
            continue

        data.append({
            "line_number": await _col_value(row, _GRID_COLS["line_number"]),
            "description": description,
            "unit": await _col_value(row, _GRID_COLS["unit"]),
            "bare_total": clean_number(await _col_value(row, _GRID_COLS["bare_total"])),
            "total_op": clean_number(await _col_value(row, _GRID_COLS["total_op"])),
        })

    return data


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
async def navigate_path(page, path):
    """
    Click down the tree following the codes in `path`, to whatever depth the
    leaf lives at (no hardcoded number of levels).

    Returns True if every code was found and clicked, False otherwise.
    """
    nodes = await page.query_selector_all("#leftTreeMenu > ul > li")
    siblings = await parse_nodes(nodes)

    for code in path:
        by_code = {n["code"]: n for n in siblings}
        target = by_code.get(code)
        if not target:
            print(f"[navigate] code {code} not found in current level")
            return False

        await target["node"].click()
        await page.wait_for_timeout(1200)

        # Children of the node we just opened become the next level.
        child_nodes = await target["node"].query_selector_all(":scope > ul > li")
        siblings = await parse_nodes(child_nodes)

    return True


# =========================
# ROUTING (OFFLINE, NO BROWSER)
# =========================
def route_question(question, start_path=None):
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
    """
    route = find_path(question, start_path=start_path)

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
async def scrape_route(question, route):
    """
    Open the browser, walk the already-chosen route, scrape and return.

    Any live-site failure (login flow changed, grid never loads, a timeout, or a
    path code missing from the live tree) is caught and turned into a useful
    `status: "error"` response instead of a raw exception that would kill the
    request with no message. The browser is always closed.
    """
    init_db()

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

            browser = await p.chromium.launch(headless=False)

            context = await browser.new_context(
                storage_state=SESSION_FILE if is_session_valid() else None
            )

            page = await context.new_page()

            await page.goto("https://www.rsmeansonline.com/")

            # ================= LOGIN =================
            if not is_session_valid():
                if not EMAIL or not PASSWORD:
                    return _error(
                        "RSMeans login no configurado: define RS_EMAIL y "
                        "RS_PASSWORD en el archivo .env."
                    )
                await page.click("#btnLogin")
                await page.fill("#username", EMAIL)
                await page.click("button[type='submit']")
                await page.fill("#password", PASSWORD)
                await page.click("#btnTerms")

                await page.wait_for_timeout(5000)
                await save_session(context)

            # ================= NAV =================
            await page.click("a#\\/SearchData")

            await wait_tree_ready(page)

            print("\nCHOSEN PATH:", " -> ".join(path))
            print("ROUTE CONFIDENCE:", route["confidence"])

            # ================= NAVIGATE THE CHOSEN PATH (VARIABLE DEPTH) =======
            navigated = await navigate_path(page, path)
            if not navigated:
                # A code in our snapshot path was not found in the live tree
                # (tree.json went stale). Don't scrape the wrong grid — say so.
                return _error(
                    "No pude seguir la ruta elegida en el catalogo en vivo de "
                    "RSMeans (la taxonomia pudo haber cambiado). Intenta "
                    "reformular la consulta o vuelve a intentar."
                )

            # IMPORTANT: WAIT FOR REAL DATA
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
                "rows": rows,
                "matched_line": matched_line,
                "path": path,
                "final_code": path[-1],
                "final_name": final_name,
                "confidence": route["confidence"],
                "fallback_used": route["fallback_used"] or not navigated,
                "clarify_questions": route.get("clarify_questions", []),
            }

    except Exception as e:  # noqa: BLE001 - any live-site failure -> useful error
        return _error(
            "Hubo un problema al consultar RSMeans en vivo (login, carga de la "
            "grilla o tiempo de espera agotado). Por favor intenta de nuevo en "
            "un momento.",
            exc=e,
        )
    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass


# =========================
# SINGLE-SHOT ENTRY (route offline first, browser only if confident)
# =========================
async def start_browser(question, start_path=None):
    route, clarification = route_question(question, start_path=start_path)
    if clarification is not None:
        return clarification
    return await scrape_route(question, route)