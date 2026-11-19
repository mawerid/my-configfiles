"""Count candidate review patterns; interpret each in project context."""

import ast
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _py import blank_comments, library_files, parse  # noqa: E402

HEAVY = set(os.environ.get("REVIEW_HEAVY_IMPORTS", "").split(","))
TEXT = {
    "assert": r"^\s*assert\b",
    "print(": r"(?<![\w.])print\(",
    "except Exception / bare": r"except\s*(?:Exception\b[^:]*)?:",
    "hardcoded /home or ~": r"[\"'](?:/home/|~/)",
    "# type: ignore / noqa": r"#\s*(?:type:\s*ignore|noqa)",
}


def module_imports(tree):
    """Imports executed while loading a module, including class/control bodies.

    TYPE_CHECKING branches are reported separately; function bodies are lazy.
    """
    typing_names = {"typing"}
    guard_names = {"TYPE_CHECKING"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            typing_names.update(
                a.asname or a.name for a in node.names if a.name == "typing"
            )
        elif isinstance(node, ast.ImportFrom) and node.module == "typing":
            guard_names.update(
                a.asname or a.name for a in node.names if a.name == "TYPE_CHECKING"
            )

    def guard(node):
        if isinstance(node, ast.Name) and node.id in guard_names:
            return True
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "TYPE_CHECKING"
            and isinstance(node.value, ast.Name)
            and node.value.id in typing_names
        ):
            return True
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            result = guard(node.operand)
            return None if result is None else not result
        return None

    def walk(node, type_only=False):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            yield node, type_only
        elif isinstance(node, ast.If) and (condition := guard(node.test)) is not None:
            for child in node.body:
                yield from walk(child, type_only or condition)
            for child in node.orelse:
                yield from walk(child, type_only or not condition)
        else:
            for child in ast.iter_child_nodes(node):
                yield from walk(child, type_only)

    yield from walk(tree)


def scan(files):
    counts = collections.defaultdict(collections.Counter)
    imports = []
    for path, src in files:
        tree = parse(src)
        for node, type_only in module_imports(tree) if tree else []:
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif node.level == 0 and node.module:
                mods = [node.module]
            for module in mods:
                if module.split(".")[0] in HEAVY:
                    category = (
                        "type-only heavy import"
                        if type_only
                        else "top-level heavy import"
                    )
                    imports.append(f"{path}:{node.lineno} import {module} ({category})")
                    counts[category][path] += 1
        code = blank_comments(src)
        for key, pattern in TEXT.items():
            source = src if key.startswith("# ") else code
            count = len(re.findall(pattern, source, re.M))
            if count:
                counts[key][path] += count
    return counts, imports


def main():
    counts, imports = scan(library_files())
    print(
        "Text pattern counts are approximate: docstrings and inline comments may match."
    )
    print("Suppression comments (# type: ignore / noqa) are counted separately.")
    for key in ["top-level heavy import", "type-only heavy import", *TEXT]:
        by_file = counts[key]
        worst = ", ".join(f"{p} {n}" for p, n in by_file.most_common(4))
        label = (
            key if key not in TEXT or key.startswith("# ") else f"text matches: {key}"
        )
        print(f"{label:40} {sum(by_file.values()):4}   {worst}")
    print("== module-level heavy imports (runtime and type-only classified separately)")
    print("\n".join(imports))


if __name__ == "__main__":
    main()
