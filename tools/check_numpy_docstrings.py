#!/usr/bin/env python3
"""Report public callables whose docstrings lack basic NumPy-style sections."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "mesh.py",
    "materials.py",
    "regions.py",
    "model.py",
    "plotting.py",
    "writer.py",
    "quadrature.py",
]


def public(name: str) -> bool:
    return not name.startswith("_")


def main() -> None:
    failures = 0
    for filename in FILES:
        path = ROOT / filename
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if not public(node.name):
                continue
            doc = ast.get_docstring(node) or ""
            if not doc.strip():
                print(f"{filename}:{node.lineno}: missing docstring: {node.name}")
                failures += 1
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                meaningful_args = [
                    a.arg for a in (*node.args.args, *node.args.kwonlyargs)
                    if a.arg not in {"self", "cls"}
                ]
                if meaningful_args and "Parameters\n----------" not in doc:
                    print(f"{filename}:{node.lineno}: no Parameters section: {node.name}")
                    failures += 1
        print(f"checked {filename}")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
