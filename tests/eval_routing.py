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
    passed = 0
    failures = []

    for question, expected in CASES:
        code, name, meta = select_level(question, [])
        ok = code == expected
        passed += ok
        flag = "PASS" if ok else "FAIL"
        print(f"[{flag}] {question!r} -> {code} (expected {expected}) "
              f"conf={meta['confidence']} fallback={meta['fallback']}")
        if not ok:
            failures.append((question, expected, code))

    total = len(CASES)
    print("\n" + "=" * 60)
    print(f"ACCURACY: {passed}/{total} ({100 * passed / total:.0f}%)")
    if failures:
        print("\nFailures:")
        for q, exp, got in failures:
            print(f"  {q!r}: expected {exp}, got {got}")


if __name__ == "__main__":
    main()
