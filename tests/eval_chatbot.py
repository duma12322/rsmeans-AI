"""
Chatbot input-coverage eval — 30 questions across 3 difficulty bands.

Drives the REAL conversation flow (`_prepare_turn` -> routing -> `_finalize_turn`,
including multi-turn clarification) but stops just before the browser: the scrape
step is replaced by `route_question`, which is the same offline decision the live
service makes before it ever opens Chromium. So this measures the AI layer —
routing, ambiguity detection and refinement — not the grid scraping.

Three bands, all phrased in English and deliberately varied in structure
(questions, imperatives, sentence fragments, first-person, colloquial):

  SPECIFIC  (10) — full detail (material + size + action). Should land on the
                   right division. Asking a follow-up here is over-cautious.
  NORMAL    (10) — everyday phrasing, one clear object. Should also land right;
                   a clarifying question is tolerable but not ideal.
  AMBIGUOUS (10) — one-word / property-only / no object named. MUST ask instead
                   of guessing. Routing straight to a price here is a FAILURE.

Every non-ambiguous case carries `expect_div`: the MasterFormat division(s) a
correct answer must land in. This is the point of the eval — "it routed" is not
a pass, "it routed to the RIGHT division" is. For a case that pauses, we still
check whether the #1 candidate offered was the correct division, which
distinguishes an over-cautious pause (right answer, asked anyway) from a genuine
miss (wrong answer AND asked).

Cases carrying `followups` continue the conversation: each follow-up is sent as
an `answer` on the open session, exercising the refinement path end-to-end.

Results stream to tests/eval_chatbot_results.json after every case, so a long
run is never lost.

Run:  python -m tests.eval_chatbot
"""
import json
import os
import sys
import tempfile

import app.main as api
from app.scraper import route_question

# --------------------------------------------------------------------------
# Isolation: never touch the real conversations.json while evaluating.
# --------------------------------------------------------------------------
api.CONVERSATIONS_FILE = os.path.join(tempfile.gettempdir(), "eval_conversations.json")
api._SESSIONS.clear()

RESULTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "eval_chatbot_results.json")

ASK_OUTCOMES = ("ASK_NARROW", "ASK_ITEM", "ASK_DIVISION", "ASK_SUBJECT")
RESOLVE_OUTCOMES = ("ROUTED", "ASK_ITEM")


def _offline_turn(question, start_path, progress=None, cancel=None):
    """The offline half of `start_browser` — decide, but never open a browser."""
    route, clarification = route_question(question, start_path=start_path)
    if clarification is not None:
        return clarification
    return {
        "status": "ok",
        "_routed": True,
        "_path": route["path"],
        "_confidence": route["confidence"],
        "_leaf": route["hops"][-1]["name"] if route["hops"] else "",
    }


# Swap the scraping call for the offline decision.
api._run_scraper = _offline_turn


# --------------------------------------------------------------------------
# The 30 cases.
#   expect:     "resolve" -> should land on a division / concrete items
#               "ask"     -> must stop and ask; routing to a price would be wrong
#   expect_div: acceptable MasterFormat division(s); None for ambiguous cases
# --------------------------------------------------------------------------
CASES = [
    # ---------------- SPECIFIC (10) ----------------
    ("specific", "Install 6 inch cast iron soil pipe, no hub, buried in a trench",
     "resolve", {"22", "33"}, []),
    ("specific", "What is the cost per square foot to install 5/8 inch gypsum board on metal studs?",
     "resolve", {"9"}, []),
    ("specific", "Replace 235 lb asphalt strip shingles on a residential roof",
     "resolve", {"7"}, []),
    ("specific", "Price a 3 foot by 7 foot hollow metal door frame, 16 gauge",
     "resolve", {"8"}, []),
    ("specific", "Pour and finish a 4 inch thick reinforced concrete slab on grade",
     "resolve", {"3"}, []),
    ("specific", "How much does welded wire fabric 6x6 W1.4/W1.4 cost per square foot?",
     "resolve", {"3"}, []),
    ("specific", "Install a 200 amp 42 circuit panelboard with a main breaker",
     "resolve", {"26"}, []),
    ("specific", "2 inch rigid galvanized steel conduit run exposed on a wall",
     "resolve", {"26"}, []),
    ("specific", "Suspended acoustical ceiling tile, 2x4 panels on 15/16 inch grid",
     "resolve", {"9"}, []),
    ("specific", "Excavate a trench 4 feet deep and 2 feet wide using a backhoe",
     "resolve", {"31"}, []),

    # ---------------- NORMAL (10) ----------------
    ("normal", "Cost to paint interior walls", "resolve", {"9"}, []),
    ("normal", "I need to replace a residential water heater", "resolve", {"22"}, []),
    ("normal", "How much is asphalt paving for a parking lot?", "resolve", {"32"}, []),
    ("normal", "Install a fire sprinkler system", "resolve", {"21"}, []),
    ("normal", "We're demolishing an interior partition wall - what does that run?",
     "resolve", {"2"}, []),
    ("normal", "CMU block wall installation", "resolve", {"4"}, []),
    ("normal", "Rooftop HVAC unit replacement cost", "resolve", {"23"}, []),
    ("normal", "Run Cat6 data cabling in an office", "resolve", {"27"}, []),
    ("normal", "smoke detectors for a fire alarm system", "resolve", {"28"}, []),
    ("normal", "What would a passenger elevator cost?", "resolve", {"14"}, []),

    # ---------------- AMBIGUOUS (10) ----------------
    # Several carry follow-ups: when the bot asks for more characteristics, we
    # supply them and the conversation must then advance.
    ("ambiguous", "pipe", "ask", None, ["cast iron, 4 inch, for drainage"]),
    ("ambiguous", "steel", "ask", None, ["galvanized mesh mats for reinforcement"]),
    ("ambiguous", "How much for a gate?", "ask", None, ["chain link, 12 foot wide, galvanized"]),
    ("ambiguous", "6 inches deep", "ask", None, ["excavation for a footing"]),
    ("ambiguous", "galvanized", "ask", None, []),
    ("ambiguous", "I need something for the roof", "ask", None, []),
    ("ambiguous", "insulation", "ask", None, ["6 inch fiberglass batt for exterior walls"]),
    ("ambiguous", "What about the doors?", "ask", None, ["hollow metal, interior, 3 by 7"]),
    ("ambiguous", "heavy duty, 24 inches, painted", "ask", None, []),
    ("ambiguous", "cost of flooring", "ask", None, []),
]


def _div_of(code):
    """Normalize a tree/line code to its top-level division ('0322' -> '3')."""
    digits = "".join(c for c in str(code) if c.isdigit())
    if not digits:
        return ""
    return str(int(digits[:2])) if len(digits) >= 2 else str(int(digits))


def _classify(result):
    """Collapse a response into (outcome, detail, top_division, candidate_codes)."""
    if not isinstance(result, dict):
        return "error", "", "", []

    if result.get("_routed"):
        path = result.get("_path") or []
        div = _div_of(path[0]) if path else ""
        return ("ROUTED", f"{' > '.join(path)}  [{result.get('_confidence')}]",
                div, [div])

    if result.get("status") == "needs_clarification":
        kind = result.get("match_type", "division")
        cands = result.get("candidates") or []
        qs = len(result.get("clarify_questions") or result.get("refine_questions") or [])
        label = {"too_broad": "ASK_NARROW", "item": "ASK_ITEM"}.get(kind, "ASK_DIVISION")

        if kind == "item":
            # Item candidates carry a line number and the path they live in.
            codes = [_div_of(c.get("path", [""])[0] if c.get("path") else c.get("line", ""))
                     for c in cands]
            names = [f"{c.get('line')} {str(c.get('name'))[:34]}" for c in cands[:3]]
        else:
            codes = [_div_of(c.get("code", "")) for c in cands]
            names = [f"{c.get('code')} {str(c.get('name'))[:30]}" for c in cands[:3]]

        codes = [c for c in codes if c]
        top = codes[0] if codes else ""
        detail = f"{len(cands)} cand, {qs} q" + (f" | top: {names[0]}" if names else "")
        return label, detail, top, codes

    if result.get("status") == "needs_subject":
        # Properties but no object ("6 inches deep"): the service asks the user
        # to name the subject. That IS correct ask-don't-guess behaviour, just a
        # different response shape than needs_clarification.
        qs = len(result.get("clarify_questions") or [])
        cats = len(result.get("categories") or [])
        return "ASK_SUBJECT", f"{cats} categories, {qs} questions", "", []

    if result.get("status") == "error":
        return "error", str(result.get("message", ""))[:80], "", []
    return result.get("status", "unknown"), "", "", []


def _ask(question=None, session_id=None, answer=None):
    """One turn through the real endpoint logic (sans browser)."""
    req = api.AskRequest(question=question, session_id=session_id, answer=answer)
    sid, sess, combined, error = api._prepare_turn(req)
    if error is not None:
        return error
    result = api._run_scraper(combined, list(sess["locked_path"]))
    return api._finalize_turn(sid, sess, result)


def _turn_record(sent, result, is_followup=False):
    outcome, detail, top, codes = _classify(result)
    return {
        "sent": sent, "outcome": outcome, "detail": detail,
        "top_division": top, "candidate_divisions": codes,
        "is_followup": is_followup,
    }


# Ranked ask-progress: a refinement that moves DOWN this ladder has advanced the
# conversation even when it hasn't resolved yet.
_PROGRESS = {"ASK_SUBJECT": 0, "ASK_NARROW": 1, "ASK_DIVISION": 2,
             "ASK_ITEM": 3, "ROUTED": 4}


def run_case(band, question, expect, expect_div, followups):
    result = _ask(question=question)
    turns = [_turn_record(question, result)]
    sid = result.get("session_id")

    for extra in followups:
        if turns[-1]["outcome"] not in ASK_OUTCOMES:
            break                                   # nothing left to answer
        result = _ask(session_id=sid, answer=extra)
        turns.append(_turn_record(extra, result, is_followup=True))
        sid = result.get("session_id", sid)

    first = turns[0]
    outcome = first["outcome"]
    asked = outcome in ASK_OUTCOMES
    resolved = outcome in RESOLVE_OUTCOMES

    # Did we land on / offer the RIGHT division? That is the real question.
    div_correct = None
    if expect_div:
        div_correct = first["top_division"] in expect_div
        in_top3 = any(c in expect_div for c in first["candidate_divisions"][:3])
    else:
        in_top3 = None

    if expect == "resolve":
        if resolved:
            verdict = "PASS" if div_correct else "FAIL"     # routed to the WRONG place
        elif asked:
            # Paused. Over-cautious (right answer offered) vs a genuine miss.
            verdict = "SOFT" if div_correct else "MISS"
        else:
            verdict = "FAIL"
    else:
        verdict = "PASS" if asked else "FAIL"

    followup_state = None
    if len(turns) > 1:
        start = _PROGRESS.get(turns[0]["outcome"], -1)
        end = _PROGRESS.get(turns[-1]["outcome"], -1)
        if turns[-1]["outcome"] in RESOLVE_OUTCOMES:
            followup_state = "resolved"
        elif end > start:
            followup_state = "advanced"
        else:
            followup_state = "stalled"

    return {
        "band": band, "question": question, "expect": expect,
        "expect_div": sorted(expect_div) if expect_div else None,
        "turns": turns, "verdict": verdict,
        "top_division_correct": div_correct, "correct_in_top3": in_top3,
        "followup_state": followup_state,
    }


def main():
    results = []
    for i, (band, question, expect, expect_div, followups) in enumerate(CASES, 1):
        print("\n" + "#" * 78)
        print(f"# CASE {i}/{len(CASES)}  [{band.upper()}]  {question!r}")
        print("#" * 78)
        try:
            res = run_case(band, question, expect, expect_div, followups)
        except Exception as exc:                      # keep the run alive
            res = {"band": band, "question": question, "expect": expect,
                   "expect_div": sorted(expect_div) if expect_div else None,
                   "turns": [{"sent": question, "outcome": "error",
                              "detail": f"{type(exc).__name__}: {exc}",
                              "top_division": "", "candidate_divisions": []}],
                   "verdict": "FAIL", "top_division_correct": None,
                   "correct_in_top3": None, "followup_state": None}
        results.append(res)
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:   # flush per case
            json.dump(results, f, indent=2, ensure_ascii=False)
        t0 = res["turns"][0]
        print(f"--> {res['verdict']}: {t0['outcome']} ({t0['detail']})")

    # ------------------------------- summary -------------------------------
    print("\n" + "=" * 78)
    print("SUMMARY BY BAND")
    print("=" * 78)
    print(f"{'BAND':<12}{'PASS':>6}{'SOFT':>6}{'MISS':>6}{'FAIL':>6}{'TOTAL':>7}")
    for band in ("specific", "normal", "ambiguous"):
        rows = [r for r in results if r["band"] == band]
        c = {v: sum(r["verdict"] == v for r in rows)
             for v in ("PASS", "SOFT", "MISS", "FAIL")}
        print(f"{band:<12}{c['PASS']:>6}{c['SOFT']:>6}{c['MISS']:>6}"
              f"{c['FAIL']:>6}{len(rows):>7}")
    tot = {v: sum(r["verdict"] == v for r in results)
           for v in ("PASS", "SOFT", "MISS", "FAIL")}
    print("-" * 78)
    print(f"{'ALL':<12}{tot['PASS']:>6}{tot['SOFT']:>6}{tot['MISS']:>6}"
          f"{tot['FAIL']:>6}{len(results):>7}")

    judged = [r for r in results if r["top_division_correct"] is not None]
    if judged:
        ok = sum(r["top_division_correct"] for r in judged)
        top3 = sum(bool(r["correct_in_top3"]) for r in judged)
        print(f"\nCorrect division as the #1 answer/candidate: {ok}/{len(judged)}")
        print(f"Correct division among the top 3:            {top3}/{len(judged)}")

    fups = [r for r in results if r["followup_state"]]
    if fups:
        for state in ("resolved", "advanced", "stalled"):
            n = sum(r["followup_state"] == state for r in fups)
            print(f"Follow-up refinements {state:<9}: {n}/{len(fups)}")

    print("\nDETAIL OF NON-PASSING CASES")
    for r in results:
        if r["verdict"] != "PASS":
            t0 = r["turns"][0]
            print(f"  [{r['verdict']}] ({r['band']}) {r['question'][:58]!r}")
            print(f"        -> {t0['outcome']} {t0['detail']}")
            print(f"        expected div {r['expect_div']}, got #1 "
                  f"{t0['top_division']!r}, top3 {t0['candidate_divisions'][:3]}")

    print(f"\nResults written to {RESULTS_FILE}")
    return 1 if (tot["FAIL"] or tot["MISS"]) else 0


if __name__ == "__main__":
    sys.exit(main())
