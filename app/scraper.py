import asyncio
from playwright.async_api import async_playwright

from app.db import init_db, save_to_db
from app.utils import clean_number
from app.navigator import select_level
from app.session import is_session_valid, save_session, SESSION_FILE

EMAIL = "thk40@scarletmail.rutgers.edu"
PASSWORD = "x12345Clear_12345x12345"


def normalize(t):
    return " ".join(t.split()).strip()


async def wait_tree_ready(page):
    for _ in range(30):
        node = await page.query_selector("#leftTreeMenu > ul > li")
        if node:
            txt = (await node.inner_text()).strip()
            if "Loading" not in txt:
                return
        await asyncio.sleep(1)

    raise Exception("TREE NOT READY")


async def scrape_grid(page):
    await page.wait_for_selector("table.ui-jqgrid-btable tr.jqgrow")
    rows = await page.query_selector_all("table.ui-jqgrid-btable tr.jqgrow")

    data = []

    for row in rows:
        cells = await row.query_selector_all("td")

        if len(cells) < 21:
            continue

        data.append({
            "description": normalize(await cells[6].inner_text()),
            "unit": normalize(await cells[8].inner_text()),
            "bare_total": clean_number(await cells[17].inner_text()),
            "total_op": clean_number(await cells[20].inner_text())
        })

    return data


async def parse_nodes(nodes):
    result = []

    for n in nodes:
        t = await n.inner_text()
        t = " ".join(t.split()).strip()

        code = t.split(" ")[0]
        name = " ".join(t.split(" ")[1:])

        result.append({
            "code": code,
            "name": name,
            "node": n
        })

    return result


async def start_browser(question):

    init_db()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        context = await browser.new_context(
            storage_state=SESSION_FILE if is_session_valid() else None
        )

        page = await context.new_page()
        await page.goto("https://www.rsmeansonline.com/")

        if not is_session_valid():
            await page.click("#btnLogin")
            await page.fill("#username", EMAIL)
            await page.click("button[type='submit']")
            await page.fill("#password", PASSWORD)
            await page.click("#btnTerms")
            await page.wait_for_timeout(5000)
            await save_session(context)

        await page.click("a#\\/SearchData")
        await wait_tree_ready(page)

        # ================= LEVEL 1 =================
        l1_nodes = await page.query_selector_all("#leftTreeMenu > ul > li")
        l1 = await parse_nodes(l1_nodes)

        path = []

        c1, n1 = select_level(question, path)

        print(f"\nLEVEL 1")
        print(f"CODE : {c1}")
        print(f"NAME : {n1}")

        path.append(c1)

        await l1[[x["code"] for x in l1].index(c1)]["node"].click()
        await page.wait_for_timeout(1200)

        # ================= LEVEL 2 =================
        l2_nodes = await page.query_selector_all("#leftTreeMenu > ul > li > ul > li")
        l2 = await parse_nodes(l2_nodes)

        c2, n2 = select_level(question, path)

        print(f"\nLEVEL 2")
        print(f"CODE : {c2}")
        print(f"NAME : {n2}")

        path.append(c2)

        await l2[[x["code"] for x in l2].index(c2)]["node"].click()
        await page.wait_for_timeout(1200)

        # ================= LEVEL 3 =================
        l3_nodes = await page.query_selector_all("#leftTreeMenu li li li")
        l3 = await parse_nodes(l3_nodes)

        c3, n3 = select_level(question, path)

        print(f"\nLEVEL 3")
        print(f"CODE : {c3}")
        print(f"NAME : {n3}")

        path.append(c3)

        await l3[[x["code"] for x in l3].index(c3)]["node"].click()
        await page.wait_for_timeout(1200)

        # ================= LEVEL 4 =================
        l4_nodes = await page.query_selector_all("#leftTreeMenu li li li li")
        l4 = await parse_nodes(l4_nodes)

        c4, n4 = select_level(question, path)

        print(f"\nLEVEL 4")
        print(f"CODE : {c4}")
        print(f"NAME : {n4}")

        path.append(c4) 

        await l4[[x["code"] for x in l4].index(c4)]["node"].click()
        await page.wait_for_timeout(2000)

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
        print("\nFINAL PATH")
        print(" -> ".join(path))

        print("\nFINAL NODE")
        print(f"{c4} - {n4}")
        
        return rows