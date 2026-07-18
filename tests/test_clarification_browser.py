"""
Regression tests: when does an ambiguous question open a browser?

The rule, and why it matters:

  * FIRST turn (nothing locked) -> run the live keyword search. This is the
    deliberate "behave like the RSMeans search box" feature for queries like
    "scissor", where there is no single right leaf.

  * REFINEMENT turn (the user already picked a branch) -> NO browser. Running the
    search again was a real bug: the codes the user picks are stripped when the
    search term is built, so every turn retyped the SAME term and reopened
    Chromium for an identical, fruitless search. Worse, the search ignores the
    locked branch entirely, so a hit could come back from division 23 right after
    the user chose 22 — silently overriding their own choice.

`route_question` is stubbed so these tests are deterministic and free: no AI
call, no network, no browser. They assert the branching in `start_browser`, which
is exactly where the bug lived.

Run with:  python -m pytest tests/test_clarification_browser.py
"""
import asyncio

import pytest

import app.scraper as sc

CLARIFICATION = {"status": "needs_clarification", "candidates": [], "question": "q"}
AMBIGUOUS_ROUTE = {"path": [], "match_type": "division", "ambiguous": True}
TOO_BROAD_ROUTE = {"path": [], "match_type": "too_broad", "term": "steel",
                   "ambiguous": True}


@pytest.fixture
def spy(monkeypatch):
    """Record browser entry points instead of launching Chromium."""
    calls = []

    async def fake_search(question, term, progress=None, cancel=None):
        calls.append(("search", term))
        return {"status": "ok", "rows": []}       # "found nothing"

    async def fake_route(question, route, progress=None, cancel=None):
        calls.append(("route", tuple(route.get("path") or ())))
        return {"status": "ok", "rows": []}

    monkeypatch.setattr(sc, "scrape_search", fake_search)
    monkeypatch.setattr(sc, "scrape_route", fake_route)
    return calls


def _stub_route(monkeypatch, route, clarification):
    monkeypatch.setattr(sc, "route_question",
                        lambda q, start_path=None, cancel=None: (route, clarification))


def test_first_ambiguous_turn_runs_the_live_search(spy, monkeypatch):
    _stub_route(monkeypatch, AMBIGUOUS_ROUTE, CLARIFICATION)
    asyncio.run(sc.start_browser("water heater", start_path=[]))
    assert [c[0] for c in spy] == ["search"]


def test_refinement_turn_does_not_open_a_browser(spy, monkeypatch):
    """The bug: this used to reopen Chromium and repeat the identical search."""
    _stub_route(monkeypatch, AMBIGUOUS_ROUTE, CLARIFICATION)
    result = asyncio.run(sc.start_browser("water heater 22", start_path=["22"]))
    assert spy == []
    assert result["status"] == "needs_clarification"


def test_deeper_refinement_also_stays_offline(spy, monkeypatch):
    _stub_route(monkeypatch, AMBIGUOUS_ROUTE, CLARIFICATION)
    asyncio.run(sc.start_browser("water heater 2233", start_path=["22", "2233"]))
    assert spy == []


def test_too_broad_never_opens_a_browser(spy, monkeypatch):
    """A single broad word asks for detail — it must not dump a live search."""
    _stub_route(monkeypatch, TOO_BROAD_ROUTE, CLARIFICATION)
    asyncio.run(sc.start_browser("steel", start_path=[]))
    assert spy == []


def test_confident_route_still_scrapes(spy, monkeypatch):
    """A confident route must still walk the tree and scrape — unchanged."""
    route = {"path": ["22", "2233"], "match_type": "division", "ambiguous": False}
    _stub_route(monkeypatch, route, None)
    asyncio.run(sc.start_browser("40 gallon electric water heater", start_path=[]))
    assert spy == [("route", ("22", "2233"))]
