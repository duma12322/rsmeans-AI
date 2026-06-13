import asyncio
from playwright.async_api import async_playwright

from app.db import init_db, save_to_db
from app.utils import clean_number
from app.navigator import select_level
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

        path = []

        # ================= LEVEL 1 =================
        l1_nodes = await page.query_selector_all("#leftTreeMenu > ul > li")
        l1 = await parse_nodes(l1_nodes)

        c1, n1 = select_level(question, path)
        path.append(c1)

        await l1[[x["code"] for x in l1].index(c1)]["node"].click()
        await page.wait_for_timeout(1200)

        # ================= LEVEL 2 =================
        l2_nodes = await page.query_selector_all("#leftTreeMenu > ul > li > ul > li")
        l2 = await parse_nodes(l2_nodes)

        c2, n2 = select_level(question, path)
        path.append(c2)

        await l2[[x["code"] for x in l2].index(c2)]["node"].click()
        await page.wait_for_timeout(1200)

        # ================= LEVEL 3 =================
        l3_nodes = await page.query_selector_all("#leftTreeMenu li li li")
        l3 = await parse_nodes(l3_nodes)

        c3, n3 = select_level(question, path)
        path.append(c3)

        await l3[[x["code"] for x in l3].index(c3)]["node"].click()
        await page.wait_for_timeout(1200)

        # ================= LEVEL 4 =================
        l4_nodes = await page.query_selector_all("#leftTreeMenu li li li li")
        l4 = await parse_nodes(l4_nodes)

        c4, n4 = select_level(question, path)
        path.append(c4)

        await l4[[x["code"] for x in l4].index(c4)]["node"].click()

        # 🔥 IMPORTANT: WAIT FOR REAL DATA
        await wait_rsmeans_data(page)

        # ================= GRID =================
        rows = await scrape_grid(page)

        if rows:
            save_to_db(
                rows=rows,
                question=question,
                c3=c3,
                c4=c4,
                final_code=c4,
                final_name=n4
            )

        await browser.close()

        print("\nFINAL PATH:", " -> ".join(path))
        print(f"FINAL NODE: {c4} - {n4}")

        return rows