"""Read tracked Python files under the selected project source directory."""

import ast
import os
import re
import subprocess
from pathlib import Path


def library_files():
    root = os.environ.get("REVIEW_ROOT", ".")
    paths = subprocess.check_output(["git", "ls-files", "-z", "--", root])
    for name in os.fsdecode(paths).split("\0"):
        path = Path(name)
        if path.suffix == ".py" and path.is_file() and not path.is_symlink():
            yield name, path.read_text(encoding="utf-8")


def parse(src):
    try:
        return ast.parse(src)
    except SyntaxError:
        return None


def functions(src):
    """(qualified name, first line, last line, normalised body dump) of every
    def, methods included. The dump ignores the function's own name,
    docstring and positions, so renamed copies hash alike."""
    tree = parse(src)
    if tree is None:
        return

    def walk(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = child.body
                if (
                    body
                    and isinstance(body[0], ast.Expr)
                    and isinstance(getattr(body[0], "value", None), ast.Constant)
                ):
                    body = body[1:]
                dump = ast.dump(
                    ast.Module(body=body, type_ignores=[]), include_attributes=False
                )
                yield (prefix + child.name, child.lineno, child.end_lineno, dump)
                yield from walk(child, prefix + child.name + ".")
            elif isinstance(child, ast.ClassDef):
                yield from walk(child, prefix + child.name + ".")
            else:
                yield from walk(child, prefix)

    yield from walk(tree, "")


def blank_comments(src):
    """Source with `#` comments blanked (strings kept), lines preserved."""
    return re.sub(r"(?m)^(\s*)#.*$", lambda m: m.group(1), src)
