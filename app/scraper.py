import asyncio
import os
import readchar
from playwright.async_api import async_playwright

from app.db import save_to_db, save_divisions, init_db
from app.session import is_session_valid, save_session
from app.utils import clean_number


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

                if "Loading" not in text:
                    print("TREE READY")
                    return

        except:
            pass

        await asyncio.sleep(1)

    raise Exception("TREE FAILED")


# ===================================================
# MENU CON FLECHAS (FIXED WINDOWS UI)
# ===================================================
def menu(title, options):

    current = 0

    while True:

        # 🔥 LIMPIA PANTALLA REAL
        os.system("cls")

        print("======================")
        print(title)
        print("======================\n")

        for i, opt in enumerate(options):
            code, name = opt
            prefix = "👉" if i == current else "  "
            print(f"{prefix} [{i}] {code} - {name}")

        print("\n↑ ↓ mover | ENTER seleccionar")

        key = readchar.readkey()

        if key == readchar.key.UP:
            current = max(0, current - 1)

        elif key == readchar.key.DOWN:
            current = min(len(options) - 1, current + 1)

        elif key == readchar.key.ENTER:
            return current


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
# MAIN SCRAPER
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

            print("LOGIN OK")

            await page.wait_for_timeout(5000)
            await save_session(context)

        await page.click("a#\\/SearchData")
        await page.wait_for_selector("#leftTreeMenu")
        await wait_tree_ready(page)

        while True:

            # ===================================================
            # LEVEL 1
            # ===================================================
            level1_nodes = await page.query_selector_all("#leftTreeMenu > ul > li")

            divisions = []

            for node in level1_nodes:
                text = normalize((await node.inner_text()).split("\n")[0])
                code, *name = text.split(" ", 1)
                name = name[0] if name else ""
                divisions.append((code, name))

            idx1 = menu("SELECT DIVISION", divisions)
            level1 = level1_nodes[idx1]

            save_divisions([divisions[idx1]])

            await safe_click(await level1.query_selector(".dynatree-expander"))
            await page.wait_for_timeout(1500)

            # ===================================================
            # LEVEL 2
            # ===================================================
            level2_nodes = await level1.query_selector_all(":scope > ul > li")

            level2_map = {}
            for node in level2_nodes:
                text = normalize((await node.inner_text()).split("\n")[0])
                code = text.split(" ")[0]
                name = " ".join(text.split(" ")[1:])
                level2_map[code] = (node, name)

            level2_list = [(k, v[1]) for k, v in level2_map.items()]

            idx2 = menu("SELECT LEVEL 2", level2_list)
            code2 = level2_list[idx2][0]
            level2 = level2_map[code2][0]

            await safe_click(await level2.query_selector(".dynatree-expander"))
            await page.wait_for_timeout(1500)

            # ===================================================
            # LEVEL 3
            # ===================================================
            level3_nodes = await level2.query_selector_all(":scope > ul > li")

            level3_map = {}
            for node in level3_nodes:
                text = normalize((await node.inner_text()).split("\n")[0])
                code = text.split(" ")[0]
                name = " ".join(text.split(" ")[1:])
                level3_map[code] = (node, name)

            level3_list = [(k, v[1]) for k, v in level3_map.items()]

            idx3 = menu("SELECT LEVEL 3", level3_list)
            code3 = level3_list[idx3][0]
            level3 = level3_map[code3][0]

            await safe_click(await level3.query_selector(".dynatree-expander"))
            await page.wait_for_timeout(1500)

            # ===================================================
            # LEVEL 4
            # ===================================================
            level4_nodes = await level3.query_selector_all(":scope > ul > li")

            level4_map = {}
            for node in level4_nodes:
                text = normalize((await node.inner_text()).split("\n")[0])
                code = text.split(" ")[0]
                name = " ".join(text.split(" ")[1:])
                level4_map[code] = (node, name)

            level4_list = [(k, v[1]) for k, v in level4_map.items()]

            idx4 = menu("SELECT LEVEL 4", level4_list)
            code4 = level4_list[idx4][0]
            level4 = level4_map[code4][0]

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
                print("NO DATA FOUND")

            again = input("\nAgain? (y/n): ").strip().lower()

            if again not in ["y", "yes"]:
                await browser.close()
                return