"""Print test and failure counts for JUnit XML result folders (used by the Kotlin CI jobs)."""

import glob
import re
import sys


def count(attr: str, head: str) -> int:
    m = re.search(rf'{attr}="(\d+)"', head)
    return int(m.group(1)) if m else 0


def main() -> int:
    grand = grand_fail = 0
    for folder in sys.argv[1:]:
        total = fails = 0
        for f in glob.glob(f"{folder}/*.xml"):
            head = open(f).read(600)
            total += count("tests", head)
            fails += count("failures", head) + count("errors", head)
        print(f"{folder}: {total} tests, {fails} failed")
        grand += total
        grand_fail += fails
    print(f"Total: {grand} tests, {grand_fail} failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
