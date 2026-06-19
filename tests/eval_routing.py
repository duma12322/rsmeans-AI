"""
Division-routing accuracy eval.

Runs a set of natural-language questions through the REAL AI navigator at the
top (division) level and checks whether each lands on the expected division.
This is how we measure whether changes to the knowledge layer or prompt
actually improve accuracy — run it before and after a change.

Requires DEEPSEEK_API_KEY / MARCE_API_URL (it hits the live model), but does
NOT open a browser — it only tests level-1 selection against tree.json.

Run with:  python -m tests.eval_routing
"""
from app.navigator import select_level

# (question, expected_division_code)
CASES = [
    ("Cost to paint interior walls", "9"),
    ("Install a 200 amp electrical panel", "26"),
    ("Replace a residential water heater", "22"),
    ("Pour a 4 inch concrete slab", "3"),
    ("Asphalt paving for a parking lot", "32"),
    ("Install a hollow metal door", "8"),
    ("Replace asphalt shingle roofing", "7"),
    ("Install a fire sprinkler system", "21"),
    ("Demolish an existing interior wall", "2"),
    ("Lay a CMU block wall", "4"),
    ("Install a rooftop HVAC unit", "23"),
    ("Run Cat6 data cabling", "27"),
    ("Install fire alarm smoke detectors", "28"),
    ("Excavate and grade the site", "31"),
    ("Install a passenger elevator", "14"),
]


def main():
    confident_correct = 0   # routed straight to the right division
    top_correct = 0         # right division was the AI's #1 candidate (even if it paused)
    wrong = []

    for question, expected in CASES:
        code, name, meta = select_level(question, [])
        top = meta["candidates"][0]["code"] if meta["candidates"] else None

        is_confident = code == expected
        is_top = top == expected
        confident_correct += is_confident
        top_correct += is_top

        if is_confident:
            flag = "ROUTED"
        elif is_top:
            flag = "PAUSED"   # correct brain, asked a follow-up anyway
        else:
            flag = "WRONG"
            wrong.append((question, expected, top))

        print(f"[{flag:6}] {question!r} -> routed={code} top={top} "
              f"(expected {expected}) conf={meta['confidence']}")

    total = len(CASES)
    print("\n" + "=" * 60)
    print(f"ROUTED confidently & correct: {confident_correct}/{total} "
          f"({100 * confident_correct / total:.0f}%)")
    print(f"TOP candidate correct (brain): {top_correct}/{total} "
          f"({100 * top_correct / total:.0f}%)")
    if wrong:
        print("\nActually wrong (top candidate != expected):")
        for q, exp, got in wrong:
            print(f"  {q!r}: expected {exp}, top was {got}")
    else:
        print("\nNo truly wrong routes — every miss was just an over-cautious pause.")


if __name__ == "__main__":
    main()
