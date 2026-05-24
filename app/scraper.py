import asyncio
from playwright.async_api import async_playwright

from app.db import (
    save_to_db
)

from app.session import (
    is_session_valid,
    save_session
)

from app.utils import (
    validate_int,
    validate_code,
    clean_number
)

EMAIL = "thk40@scarletmail.rutgers.edu"
PASSWORD = "x12345Clear_12345x12345"


# ---------------------------------------------------
# SCRAPE GRID
# ---------------------------------------------------
async def scrape_grid(page):

    await page.wait_for_selector(
        "table.ui-jqgrid-btable tr.jqgrow"
    )

    rows = await page.query_selector_all(
        "table.ui-jqgrid-btable tr.jqgrow"
    )

    data = []

    print(f"\nROWS DETECTED: {len(rows)}")

    for row in rows:

        try:

            cells = await row.query_selector_all("td")

            if len(cells) < 21:
                continue

            description = (
                await cells[6].inner_text()
            ).strip()

            unit = (
                await cells[8].inner_text()
            ).strip()

            bare_total = (
                await cells[17].inner_text()
            ).strip()

            total_op = (
                await cells[20].inner_text()
            ).strip()

            print(
                "DESCRIPTION:",
                description
            )

            item = {
                "description": description,
                "unit": unit,
                "bare_total": clean_number(
                    bare_total
                ),
                "total_op": clean_number(
                    total_op
                )
            }

            data.append(item)

        except Exception as e:

            print("ROW ERROR:", e)

    return data


# ---------------------------------------------------
# WAIT TREE READY
# ---------------------------------------------------
async def wait_tree_ready(page):

    print("\n⏳ Waiting tree to load...")

    for _ in range(30):

        try:

            node = await page.query_selector(
                "#leftTreeMenu > ul > li"
            )

            if node:

                text = (
                    await node.inner_text()
                ).strip()

                print("TREE STATUS:", text)

                if "Loading" not in text:

                    print("✅ Tree ready")
                    return

        except:
            pass

        await asyncio.sleep(1)

    raise Exception(
        "❌ Tree failed to load"
    )


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
async def start_browser():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False
        )

        # ---------------------------------------------------
        # SESSION
        # ---------------------------------------------------
        if is_session_valid():

            print("♻️ SESSION ACTIVE")

            context = await browser.new_context(
                storage_state="session.json"
            )

        else:

            print("🆕 NEW LOGIN")

            context = await browser.new_context()

        page = await context.new_page()

        # ---------------------------------------------------
        # OPEN WEBSITE
        # ---------------------------------------------------
        await page.goto(
            "https://www.rsmeansonline.com/"
        )

        # ---------------------------------------------------
        # LOGIN
        # ---------------------------------------------------
        if not is_session_valid():

            await page.wait_for_selector(
                "#btnLogin"
            )

            await page.click("#btnLogin")

            await page.fill(
                "#username",
                EMAIL
            )

            await page.click(
                "button[type='submit']"
            )

            await page.fill(
                "#password",
                PASSWORD
            )

            await page.click("#btnTerms")

            print("✅ LOGIN SUCCESS")

            await page.wait_for_timeout(5000)

            await save_session(context)

        # ---------------------------------------------------
        # OPEN SEARCH DATA
        # ---------------------------------------------------
        await page.wait_for_selector(
            "a#\\/SearchData"
        )

        await page.click(
            "a#\\/SearchData"
        )

        await page.wait_for_selector(
            "#leftTreeMenu"
        )

        await wait_tree_ready(page)

        # ===================================================
        # MAIN LOOP
        # ===================================================
        while True:

            # ===================================================
            # LEVEL 1
            # ===================================================
            while True:

                print("\n======================")
                print("MASTERFORMAT DIVISIONS")
                print("======================\n")

                level1_nodes = await page.query_selector_all(
                    "#leftTreeMenu > ul > li"
                )

                level1_map = []

                for i, node in enumerate(level1_nodes):

                    text = (
                        await node.inner_text()
                    ).strip()

                    first_line = text.split("\n")[0]

                    print(f"{i} {first_line}")

                    level1_map.append(node)

                idx1 = validate_int(
                    input("\nSELECT DIVISION: "),
                    len(level1_map)
                )

                if idx1 is not None:
                    break

                print("❌ INVALID DIVISION")

            level1 = level1_map[idx1]

            expander = await level1.query_selector(
                ".dynatree-expander"
            )

            if expander:
                await expander.click(force=True)

            await page.wait_for_timeout(1500)

            # ===================================================
            # LEVEL 2
            # ===================================================
            while True:

                level2_nodes = await level1.query_selector_all(
                    ":scope > ul > li"
                )

                level2_map = {}

                print("\n======================")
                print("LEVEL 2")
                print("======================\n")

                for node in level2_nodes:

                    text = (
                        await node.inner_text()
                    ).strip()

                    first_line = text.split("\n")[0]

                    code = first_line.split(" ")[0]

                    level2_map[code] = node

                    print(first_line)

                code2 = validate_code(
                    input("\nLEVEL 2 CODE: "),
                    level2_map
                )

                if code2:
                    break

                print("❌ INVALID LEVEL 2")

            level2 = level2_map[code2]

            expander = await level2.query_selector(
                ".dynatree-expander"
            )

            if expander:
                await expander.click(force=True)

            await page.wait_for_timeout(1500)

            # ===================================================
            # LEVEL 3
            # ===================================================
            while True:

                level3_nodes = await level2.query_selector_all(
                    ":scope > ul > li"
                )

                level3_map = {}

                print("\n======================")
                print("LEVEL 3")
                print("======================\n")

                for node in level3_nodes:

                    text = (
                        await node.inner_text()
                    ).strip()

                    first_line = text.split("\n")[0]

                    code = first_line.split(" ")[0]

                    level3_map[code] = node

                    print(first_line)

                code3 = validate_code(
                    input("\nLEVEL 3 CODE: "),
                    level3_map
                )

                if code3:
                    break

                print("❌ INVALID LEVEL 3")

            level3 = level3_map[code3]

            expander = await level3.query_selector(
                ".dynatree-expander"
            )

            if expander:
                await expander.click(force=True)

            await page.wait_for_timeout(1500)

            # ===================================================
            # LEVEL 4
            # ===================================================
            while True:

                level4_nodes = await level3.query_selector_all(
                    ":scope > ul > li"
                )

                level4_map = {}

                print("\n======================")
                print("LEVEL 4")
                print("======================\n")

                for node in level4_nodes:

                    text = (
                        await node.inner_text()
                    ).strip()

                    first_line = text.split("\n")[0]

                    code = first_line.split(" ")[0]

                    level4_map[code] = node

                    print(first_line)

                code4 = validate_code(
                    input("\nFINAL CODE: "),
                    level4_map
                )

                if code4:
                    break

                print("❌ INVALID FINAL CODE")

            level4 = level4_map[code4]

            print(f"\nFINAL CODE: {code4}")

            # ===================================================
            # CLICK REAL TITLE
            # ===================================================
            title = await level4.query_selector(
                ".dynatree-title"
            )

            await title.click(force=True)

            # ===================================================
            # WAIT GRID LOAD
            # ===================================================
            await page.wait_for_selector(
                "table.ui-jqgrid-btable tr.jqgrow"
            )

            await page.wait_for_timeout(2000)

            # ===================================================
            # SCRAPE GRID
            # ===================================================
            print("\nSCRAPING GRID...")

            rows = await scrape_grid(page)

            print(f"ROWS FOUND: {len(rows)}")

            # ===================================================
            # SAVE SQLITE
            # ===================================================
            if rows:

                save_to_db(
                    rows,
                    code3,
                    code4
                )

            else:

                print("❌ NO DATA FOUND")

            print("\n✅ SEARCH COMPLETED")

            # ===================================================
            # ANOTHER SEARCH
            # ===================================================
            again = input(
                "\nDo you want to perform another search? (y/n): "
            ).strip().lower()

            if again not in ["y", "yes"]:

                print("\n👋 Goodbye!")

                await browser.close()

                return

            # ===================================================
            # RESET SEARCH
            # ===================================================
            await page.click("a#\\/SearchData")

            await page.wait_for_timeout(2000)

            await wait_tree_ready(page)