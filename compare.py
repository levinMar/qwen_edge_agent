"""
compare.py — Runs both classification strategies against the same image
set and reports where they agree/disagree. This comparison is the core
"constraint-solving" evidence for the portfolio writeup.
"""

import os
import time
from inference import constrained_diagnose, freeform_diagnose
from diagnostics_pb2 import IssueType, Severity

IMAGE_DIR = "./test_images"


def run_comparison():
    results = []

    for filename in sorted(os.listdir(IMAGE_DIR)):
        if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        path = os.path.join(IMAGE_DIR, filename)
        print(f"\n--- {filename} ---")

        try:
            constrained = constrained_diagnose(path)
            print(f"  [constrained] {IssueType.Name(constrained.issue_type)} "
                  f"({constrained.confidence:.2f}) — {constrained.raw_description}")
        except Exception as e:
            print(f"  [constrained] FAILED: {e}")
            constrained = None

        time.sleep(1)  # be polite to the API between calls

        try:
            freeform = freeform_diagnose(path)
            print(f"  [freeform]    {IssueType.Name(freeform.issue_type)} "
                  f"({freeform.confidence:.2f}) — {freeform.raw_description}")
        except Exception as e:
            print(f"  [freeform] FAILED: {e}")
            freeform = None

        agree = (
            constrained is not None
            and freeform is not None
            and constrained.issue_type == freeform.issue_type
        )
        results.append((filename, constrained, freeform, agree))
        time.sleep(1)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    agreements = sum(1 for r in results if r[3])
    print(f"Agreement: {agreements}/{len(results)} images")
    for filename, c, f, agree in results:
        marker = "✓" if agree else "✗"
        c_name = IssueType.Name(c.issue_type) if c else "ERROR"
        f_name = IssueType.Name(f.issue_type) if f else "ERROR"
        print(f"  {marker} {filename}: constrained={c_name} freeform={f_name}")


if __name__ == "__main__":
    run_comparison()