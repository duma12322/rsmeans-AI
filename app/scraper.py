import asyncio
from playwright.async_api import async_playwright

from app.db import init_db, save_to_db
from app.utils import clean_number
from app.navigator import (
    find_path,
    needs_clarification,
    build_clarification_response,
)
from app.session import is_session_valid, save_session, SESSION_FILE


EMAIL = "thk40@scarletmail.rutgers.edu"
PASSWORD = "x12345Clear_12345x12345"


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
async def scrape_grid(page):

    await wait_rsmeans_data(page)

    rows = await page.query_selector_all(
        "table.ui-jqgrid-btable tr.jqgrow"
    )

    data = []

    for row in rows:

        cells = await row.query_selector_all("td")

        if len(cells) < 23:
            continue

        description = normalize(
            await get_cell_value(cells[6])
        )

        unit = normalize(
            await get_cell_value(cells[8])
        )

        # RSMeans REAL
        raw_bare_total = await get_cell_value(cells[18])

        raw_total_op = await get_cell_value(cells[21])

        data.append({
            "description": description,
            "unit": unit,
            "bare_total": clean_number(raw_bare_total),
            "total_op": clean_number(raw_total_op)
        })

    return data


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
# MAIN
# =========================
async def start_browser(question):

    init_db()

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=False)

        context = await browser.new_context(
            storage_state=SESSION_FILE if is_session_valid() else None
        )

        page = await context.new_page()

        await page.goto("https://www.rsmeansonline.com/")

        # ================= LOGIN =================
        if not is_session_valid():
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

        # ===== DECIDE THE ROUTE (BEAM SEARCH WITH BACKTRACKING, OFFLINE) =====
        # Explore tree.json with backtracking and pick the best full path to a
        # leaf BEFORE touching the browser.
        route = find_path(question)

        # Clarification gate: if not even the best route is trustworthy
        # (fallback, or ambiguous + low confidence), stop and ask the user
        # instead of navigating to a confidently wrong cost.
        route_meta = {
            "confidence": route["confidence"] if route else "low",
            "clarify": (route["clarifications"][0]
                        if route and route["clarifications"] else None),
            "fallback": route["fallback_used"] if route else True,
        }
        if route is None or not route["path"] or needs_clarification(route_meta):
            await browser.close()
            print("\n[BEAM] ruta no confiable -> se pide clarificación al usuario")
            return build_clarification_response(
                question, route["path"] if route else [], route_meta
            )

        path = route["path"]
        hops = route["hops"]
        final_name = hops[-1]["name"]

        print("\nCHOSEN PATH:", " -> ".join(path))
        print("ROUTE CONFIDENCE:", route["confidence"])

        # ================= NAVIGATE THE CHOSEN PATH (VARIABLE DEPTH) =================
        navigated = await navigate_path(page, path)

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

        await browser.close()

        print("\nFINAL PATH:", " -> ".join(path))
        print(f"FINAL NODE: {path[-1]} - {final_name}")

        return {
            "rows": rows,
            "path": path,
            "final_code": path[-1],
            "final_name": final_name,
            "confidence": route["confidence"],
            "fallback_used": route["fallback_used"] or not navigated,
            "clarifications": route["clarifications"],
        }