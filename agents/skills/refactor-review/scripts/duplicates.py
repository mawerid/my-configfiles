"""Copies across library files: function bodies identical up to the
function's own name and docstring, and module constants of one name and
value defined in several files. A hit is a lead to read, not a finding.

Usage: python3 duplicates.py [min_lines=4]   (from the repository root)
"""

import ast
import collections
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _py import functions, library_files, parse  # noqa: E402

min_lines = int(sys.argv[1]) if len(sys.argv) > 1 else 4

bodies = collections.defaultdict(list)
consts = collections.defaultdict(list)
for path, src in library_files():
    for name, first, last, dump in functions(src):
        if last - first + 1 < min_lines:
            continue
        bodies[hashlib.sha1(dump.encode()).hexdigest()].append(
            (last - first + 1, path, f"{path}:{first} {name}")
        )
    tree = parse(src)
    for node in tree.body if tree else []:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            name = node.targets[0].id
            if name.isupper():
                consts[f"{name} = {ast.unparse(node.value)}"].append(
                    f"{path}:{node.lineno}"
                )

print("== identical function bodies in more than one file")
for hits in sorted(bodies.values(), key=lambda h: -h[0][0]):
    if len({h[1] for h in hits}) > 1:
        print(f"{hits[0][0]:4} lines: " + ", ".join(h[2] for h in hits))

print("== constants of one name and value in more than one file")
for sig, where in sorted(consts.items(), key=lambda kv: -len(kv[1])):
    if len({w.rsplit(":", 1)[0] for w in where}) > 1:
        print(f"{sig}  <- " + ", ".join(where))
