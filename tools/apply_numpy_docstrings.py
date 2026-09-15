#!/usr/bin/env python3
"""
Apply curated NumPy-style docstrings to the verified DORT_Input source modules.

This utility deliberately changes docstrings only. It uses Python's AST solely
to locate module/class/function docstring spans, then performs textual
replacement so the computational statements remain untouched.

Run from the repository root:

    python tools/apply_numpy_docstrings.py
    git diff

The script updates the six source modules verified in the documentation
snapshot. It does not invent an API for a missing quadrature source module.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPING_FILE = Path(__file__).with_name("numpy_docstrings.json")


def _node_key(stack: tuple[str, ...], node: ast.AST) -> str:
    name = getattr(node, "name", "")
    return ".".join((*stack, name)) if stack else name


def _collect_nodes(tree: ast.AST) -> dict[str, ast.AST]:
    """Collect module, class, and function nodes by qualified name."""
    found: dict[str, ast.AST] = {"__module__": tree}

    def visit_body(body, stack=()):
        for node in body:
            if isinstance(node, ast.ClassDef):
                key = _node_key(stack, node)
                found[key] = node
                visit_body(node.body, (*stack, node.name))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                key = _node_key(stack, node)
                found[key] = node
                # Nested functions are implementation details and intentionally
                # not traversed for curated public documentation.

    visit_body(tree.body)
    return found


def _doc_expr(node: ast.AST):
    body = getattr(node, "body", None)
    if not body:
        return None
    first = body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return first
    return None


def _indent_doc(text: str, indent: str) -> list[str]:
    clean = text.strip("\n")
    lines = clean.splitlines()
    out = [indent + '"""' + (lines[0] if lines else "")]
    if len(lines) == 1:
        out[-1] += '"""\n'
        return out
    out[0] += "\n"
    for line in lines[1:]:
        out.append(indent + line + "\n")
    out.append(indent + '"""\n')
    return out


def apply_file(path: Path, mapping: dict[str, str]) -> list[str]:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    nodes = _collect_nodes(tree)

    edits = []
    changed = []

    for key, doc in mapping.items():
        node = nodes.get(key)
        if node is None:
            print(f"WARNING: {path.name}: target not found: {key}")
            continue

        existing = _doc_expr(node)
        if existing is not None:
            start = existing.lineno - 1
            end = existing.end_lineno
            indent = " " * existing.col_offset
            replacement = _indent_doc(doc, indent)
            edits.append((start, end, replacement))
        else:
            body = getattr(node, "body", None)
            if not body:
                print(f"WARNING: {path.name}: cannot insert docstring: {key}")
                continue
            start = body[0].lineno - 1
            indent = " " * body[0].col_offset
            replacement = _indent_doc(doc, indent)
            edits.append((start, start, replacement))
        changed.append(key)

    # Apply bottom-up so original line numbers stay valid.
    for start, end, replacement in sorted(edits, reverse=True, key=lambda x: x[0]):
        lines[start:end] = replacement

    new_source = "".join(lines)
    # Verify that docstring replacement did not create invalid Python.
    ast.parse(new_source)

    path.write_text(new_source, encoding="utf-8")
    return changed


def main() -> None:
    mapping = json.loads(MAPPING_FILE.read_text(encoding="utf-8"))
    total = 0

    for filename, docs in mapping.items():
        path = ROOT / filename
        if not path.exists():
            print(f"SKIP: {filename} not found")
            continue
        changed = apply_file(path, docs)
        total += len(changed)
        print(f"UPDATED: {filename}: {len(changed)} docstrings")

    quadrature = ROOT / "quadrature.py"
    if quadrature.exists():
        print(
            "NOTICE: quadrature.py exists, but its exact public API was not "
            "present in the verified source snapshot. It has been left "
            "untouched rather than receiving invented semantic docstrings."
        )
    else:
        print(
            "NOTICE: no quadrature.py found in this repository snapshot. "
            "The Read-the-Docs user guide nevertheless documents quadrature "
            "as a processing stage and its DORT 81*/82*/83* mapping."
        )

    print(f"Completed. Curated docstrings applied: {total}")
    print("Review changes with: git diff")


if __name__ == "__main__":
    main()
