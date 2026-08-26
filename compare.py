"""
compare.py — Runs constrained classification against a test image set and
reports results. Previously compared both constrained and freeform strategies;
the freeform path has been removed in favour of the constrained-only pipeline.
"""

import os
import time
from inference import constrained_diagnose
from diagnostics_pb2 import IssueType

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

        results.append((filename, constrained))
        time.sleep(1)  # be polite to the API between calls

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    success = sum(1 for _, c in results if c is not None)
    print(f"Successful: {success}/{len(results)} images")
    for filename, c in results:
        marker = "✓" if c else "✗"
        c_name = IssueType.Name(c.issue_type) if c else "ERROR"
        print(f"  {marker} {filename}: {c_name}")


if __name__ == "__main__":
    run_comparison()