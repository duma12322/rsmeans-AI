"""
Record scraper for keyword enrichment.

Uses tree.json as the map and walks the live RSMeans hierarchy section by
section. At every LEAF section it scrapes all the grid line-items and keeps
their `description` text, grouped by top-level division. That real line-item
vocabulary (materials, sizes, actions like "install"/"replace") is far richer
than the branch titles, and feeds app/keyword_extractor.py.

Output:
    division_records.json           {division_code: [description, ...]}
    division_records.progress.json  {"done": [leaf path strings]}  (for resume)

The full 24-division scrape is long, so progress is flushed after every leaf and
already-scraped leaves are skipped on a re-run.

Run a single division (validate first):
    python -m app.record_scraper 22
Run everything:
    python -m app.record_scraper all
"""
import sys
import json
import os
import asyncio

from playwright.async_api import async_playwright

from app.scraper import (
    EMAIL, PASSWORD, normalize, parse_nodes,
    wait_tree_ready, wait_rsmeans_data, scrape_grid,
)
from app.session import is_session_valid, save_session, SESSION_FILE
from app.tree_loader import load_tree
from app.keyword_extractor import generate as generate_keywords

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDS_PATH = os.path.join(BASE_DIR, "division_records.json")
PROGRESS_PATH = os.path.join(BASE_DIR, "division_records.progress.json")


# =========================
# PERSISTENCE (resumable)
# =========================
def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


class Store:
    """Accumulates descriptions per division and flushes after every leaf."""

    def __init__(self):
        self.records = _load_json(RECORDS_PATH, {})
        self.done = set(_load_json(PROGRESS_PATH, {}).get("done", []))

    def already_done(self, leaf_key):
        return leaf_key in self.done

    def add(self, division, leaf_key, descriptions):
        bucket = self.records.setdefault(division, [])
        bucket.extend(descriptions)
        self.done.add(leaf_key)
        self._flush()

    def _flush(self):
        with open(RECORDS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.records, f, indent=2, ensure_ascii=False)
        with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
            json.dump({"done": sorted(self.done)}, f, indent=2, ensure_ascii=False)


# =========================
# NAVIGATION
# =========================
async def _expand(node):
    try:
        await node.click()
        await asyncio.sleep(1.2)
    except Exception:
        pass


async def _scrape_leaf(page, division, leaf_key, store):
    """A node with no children: its grid holds the actual line-items."""
    try:
        await wait_rsmeans_data(page)
        rows = await scrape_grid(page)
    except Exception as e:
        print(f"  [leaf] {leaf_key}: no grid data ({e})")
        store.add(division, leaf_key, [])
        return

    descriptions = [r["description"] for r in rows if r.get("description")]
    print(f"  [leaf] {leaf_key}: {len(descriptions)} records")
    store.add(division, leaf_key, descriptions)


async def _dfs(page, li, path, division, store):
    """Depth-first walk of one division's subtree, scraping every leaf grid."""
    await _expand(li)

    children = await li.query_selector_all(":scope > ul > li")
    leaf_key = " > ".join(path)

    if not children:
        if store.already_done(leaf_key):
            print(f"  [skip] {leaf_key} (already scraped)")
            return
        await _scrape_leaf(page, division, leaf_key, store)
        return

    parsed = await parse_nodes(children)
    for c in parsed:
        await _dfs(page, c["node"], path + [c["code"]], division, store)


async def _login_and_open_tree(page, context):
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


async def _scrape_one_division(code, store):
    """One full browser lifecycle for a single division (chapter).

    A fresh browser is opened, the division is scraped, and the browser is
    closed before returning — this keeps each session short so the RSMeans
    page/API never has to hold up under one long continuous crawl.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            storage_state=SESSION_FILE if is_session_valid() else None
        )
        page = await context.new_page()

        await _login_and_open_tree(page, context)

        l1_nodes = await page.query_selector_all("#leftTreeMenu > ul > li")
        l1 = await parse_nodes(l1_nodes)
        by_code = {n["code"]: n for n in l1}

        target = by_code.get(code)
        if not target:
            print(f"[division {code}] NOT FOUND in tree menu, skipping")
            await browser.close()
            return False

        print(f"\n{'=' * 60}\nDIVISION {code} - {target['name']}\n{'=' * 60}")
        await _dfs(page, target["node"], [code], code, store)

        await browser.close()
        return True


async def scrape_divisions(division_codes):
    """Scrape divisions one at a time: open -> scrape -> add keywords -> close.

    Each section runs in its own browser lifecycle, and keywords are
    regenerated after every section closes, so progress (records AND keywords)
    survives even if a later section fails or the page falls over.
    """
    store = Store()

    for code in division_codes:
        scraped = await _scrape_one_division(code, store)
        if scraped:
            # Browser is now closed; fold this section's fresh records into
            # the keyword layer before moving on to the next one.
            generate_keywords()
            print(f"[division {code}] keywords updated\n")

    total = sum(len(v) for v in store.records.values())
    print(f"\nDONE. {total} descriptions across {len(store.records)} divisions "
          f"-> {RECORDS_PATH}")
    return store.records


# =========================
# WINDOWS-SAFE RUNNER
# =========================
def run(division_codes):
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(scrape_divisions(division_codes))
    finally:
        loop.close()


def _resolve_targets(arg):
    if arg in (None, "", "all"):
        return list(load_tree().keys())
    return [c.strip() for c in arg.split(",") if c.strip()]


if __name__ == "__main__":
    targets = _resolve_targets(sys.argv[1] if len(sys.argv) > 1 else "22")
    run(targets)
