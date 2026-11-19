"""The longest library functions, and how many run past 60 and 100 lines.

Usage: python3 fn_lengths.py [top=40]   (from the repository root)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _py import functions, library_files  # noqa: E402

top = int(sys.argv[1]) if len(sys.argv) > 1 else 40
rows = []
for path, src in library_files():
    for name, first, last, _ in functions(src):
        rows.append((last - first + 1, f"{path}:{first}", name))
rows.sort(reverse=True)
for length, at, name in rows[:top]:
    print(f"{length:5} {at} {name}")
print(
    f"functions: {len(rows)}, past 60 lines: {sum(r[0] > 60 for r in rows)},"
    f" past 100: {sum(r[0] > 100 for r in rows)}"
)
