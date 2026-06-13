import asyncio
import json
from playwright.async_api import async_playwright

TREE = {}


# =========================
# NODE SETTER (estructura correcta)
# =========================
def set_node(path, code, name):
    node = TREE

    for p in path:
        if p not in node:
            node[p] = {"_name": "", "_children": {}}
        node = node[p]["_children"]

    node[code] = {
        "_name": name,
        "_children": {}
    }


# =========================
# NORMALIZAR TEXTO
# =========================
def normalize(t):
    return " ".join(t.split()).strip()


# =========================
# PARSE NODES DEL DOM
# =========================
async def parse_nodes(nodes):
    result = []

    for n in nodes:
        t = await n.inner_text()
        t = normalize(t)

        if not t:
            continue

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
# EXPANDIR UN NODO
# =========================
async def expand(node):
    try:
        await node.click()
        await asyncio.sleep(1.2)
    except:
        pass


# =========================
# DFS RECURSIVO
# =========================
async def crawl(page, node, path):
    children = await node.query_selector_all(":scope > ul > li")
    parsed = await parse_nodes(children)

    for c in parsed:

        print("SCRAPING:", path + [c["code"]], c["name"])

        set_node(path, c["code"], c["name"])

        await expand(c["node"])

        await crawl(page, c["node"], path + [c["code"]])


# =========================
# MAIN SCRAPER
# =========================
async def main():

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto("https://www.rsmeansonline.com/")

        input("🔐 LOGEA MANUALMENTE Y PRESIONA ENTER...")

        await page.click("a#\\/SearchData")
        await asyncio.sleep(3)

        # =========================
        # ROOT LEVEL
        # =========================
        level1 = await page.query_selector_all("#leftTreeMenu > ul > li")
        parsed1 = await parse_nodes(level1)

        for c1 in parsed1:

            print("\nROOT:", c1["code"], c1["name"])

            set_node([], c1["code"], c1["name"])

            await expand(c1["node"])

            await crawl(page, c1["node"], [c1["code"]])

        # =========================
        # SAVE JSON
        # =========================
        with open("tree.json", "w", encoding="utf-8") as f:
            json.dump(TREE, f, indent=2, ensure_ascii=False)

        print("\nTREE COMPLETO ✔")

        await browser.close()


asyncio.run(main())