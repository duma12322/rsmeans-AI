import asyncio
from playwright.async_api import async_playwright

from app.db import save_to_db, save_divisions, init_db
from app.session import is_session_valid, save_session
from app.utils import validate_int, validate_code, clean_number


EMAIL = "thk40@scarletmail.rutgers.edu"
PASSWORD = "x12345Clear_12345x12345"


# ===================================================
# CLEAN TEXT
# ===================================================
def normalize(text):
    return " ".join(text.split()).strip()


# ===================================================
# SCRAPE GRID
# ===================================================
async def scrape_grid(page):

    await page.wait_for_selector("table.ui-jqgrid-btable tr.jqgrow")
    rows = await page.query_selector_all("table.ui-jqgrid-btable tr.jqgrow")

    data = []

    for row in rows:
        try:
            cells = await row.query_selector_all("td")

            if len(cells) < 21:
                continue

            data.append({
                "description": normalize(await cells[6].inner_text()),
                "unit": normalize(await cells[8].inner_text()),
                "bare_total": clean_number(await cells[17].inner_text()),
                "total_op": clean_number(await cells[20].inner_text())
            })

        except Exception as e:
            print("ROW ERROR:", e)

    return data


# ===================================================
# WAIT TREE
# ===================================================
async def wait_tree_ready(page):

    print("\n⏳ Waiting tree to load...")

    for _ in range(30):
        try:
            node = await page.query_selector("#leftTreeMenu > ul > li")

            if node:
                text = (await node.inner_text()).strip()
                print("TREE STATUS:", text)

                if "Loading" not in text:
                    print("✅ Tree ready")
                    return

        except:
            pass

        await asyncio.sleep(1)

    raise Exception("❌ Tree failed")


# ===================================================
# SAFE CLICK
# ===================================================
async def safe_click(locator):
    if locator:
        try:
            await locator.click(force=True)
            return True
        except:
            return False
    return False


# ===================================================
# MAIN
# ===================================================
async def start_browser():

    init_db()

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=False)

        context = await browser.new_context(
            storage_state="session.json" if is_session_valid() else None
        )

        page = await context.new_page()
        await page.goto("https://www.rsmeansonline.com/")

        # LOGIN
        if not is_session_valid():

            await page.click("#btnLogin")
            await page.fill("#username", EMAIL)
            await page.click("button[type='submit']")
            await page.fill("#password", PASSWORD)
            await page.click("#btnTerms")

            print("✅ LOGIN SUCCESS")

            await page.wait_for_timeout(5000)
            await save_session(context)

        await page.click("a#\\/SearchData")
        await page.wait_for_selector("#leftTreeMenu")
        await wait_tree_ready(page)

        while True:

            print("\n======================")
            print("MASTERFORMAT DIVISIONS")
            print("======================\n")

            # ===================================================
            # LEVEL 1
            # ===================================================
            level1_nodes = await page.query_selector_all("#leftTreeMenu > ul > li")

            level1_map = []
            divisions = []

            for i, node in enumerate(level1_nodes):

                text = normalize((await node.inner_text()).split("\n")[0])
                code, *name = text.split(" ", 1)
                name = name[0] if name else ""

                print(f"{i} {code} {name}")

                level1_map.append(node)
                divisions.append((code, name))

            idx1 = validate_int(input("\nSELECT DIVISION: "), len(level1_map))
            if idx1 is None:
                print("❌ INVALID DIVISION")
                continue

            save_divisions([divisions[idx1]])

            level1 = level1_map[idx1]

            await safe_click(await level1.query_selector(".dynatree-expander"))
            await page.wait_for_timeout(1500)

            # ===================================================
            # LEVEL 2 (REPEAT ON ERROR)
            # ===================================================
            level2_nodes = await level1.query_selector_all(":scope > ul > li")
            level2_map = {}

            for node in level2_nodes:
                text = normalize((await node.inner_text()).split("\n")[0])
                code = text.split(" ")[0]
                level2_map[code] = node
                print(text)

            while True:
                code2 = validate_code(input("\nLEVEL 2 CODE: "), level2_map)

                if code2 in level2_map:
                    break
                print("❌ INVALID LEVEL 2 - TRY AGAIN")

            level2 = level2_map[code2]

            await safe_click(await level2.query_selector(".dynatree-expander"))
            await page.wait_for_timeout(1500)

            # ===================================================
            # LEVEL 3 (REPEAT ON ERROR)
            # ===================================================
            level3_nodes = await level2.query_selector_all(":scope > ul > li")
            level3_map = {}

            for node in level3_nodes:
                text = normalize((await node.inner_text()).split("\n")[0])
                code = text.split(" ")[0]
                level3_map[code] = node
                print(text)

            while True:
                code3 = validate_code(input("\nLEVEL 3 CODE: "), level3_map)

                if code3 in level3_map:
                    break
                print("❌ INVALID LEVEL 3 - TRY AGAIN")

            level3 = level3_map[code3]

            await safe_click(await level3.query_selector(".dynatree-expander"))
            await page.wait_for_timeout(1500)

            # ===================================================
            # LEVEL 4 (REPEAT ON ERROR)
            # ===================================================
            level4_nodes = await level3.query_selector_all(":scope > ul > li")
            level4_map = {}

            for node in level4_nodes:
                text = normalize((await node.inner_text()).split("\n")[0])
                code = text.split(" ")[0]
                level4_map[code] = node
                print(text)

            while True:
                code4 = validate_code(input("\nFINAL CODE: "), level4_map)

                if code4 in level4_map:
                    break
                print("❌ INVALID FINAL CODE - TRY AGAIN")

            level4 = level4_map[code4]

            print(f"\nFINAL CODE: {code4}")

            await safe_click(await level4.query_selector(".dynatree-title"))
            await page.wait_for_timeout(4000)

            # ===================================================
            # GRID
            # ===================================================
            await page.click("a#\\/SearchData")
            await wait_tree_ready(page)

            print("\nSCRAPING GRID...")

            rows = await scrape_grid(page)


            if rows:
                save_to_db(rows, code3, code4)
            else:
                print("❌ NO DATA FOUND")

            again = input("\nDo you want another search? (y/n): ").strip().lower()

            if again not in ["y", "yes"]:
                print("\n👋 EXIT")
                await browser.close()
                return