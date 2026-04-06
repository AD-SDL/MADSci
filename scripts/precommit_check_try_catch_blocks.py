#!/usr/bin/env python3

from __future__ import annotations

import ast
import sys
from pathlib import Path
from tokenize import COMMENT, tokenize


def _iter_py_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            files.extend([pp for pp in path.rglob("*.py") if pp.is_file()])
        elif path.is_file() and path.suffix == ".py":
            files.append(path)
    return files


def find_no_qa_lines(file_path: Path) -> set(int):
    test = tokenize(Path.open(file_path, "rb").readline)
    tokens = list(test)
    no_qa_lines = set()
    for token in tokens:
        if token.type == COMMENT and "noqa" in token.string:
            no_qa_lines.add(token.start[0])
    return no_qa_lines


def sub_walk(
    node: ast.AST, violations: list[str], no_qa_lines: set[int], file_path: Path
) -> list[str]:
    for subnode in ast.walk(node):
        if isinstance(subnode, ast.ExceptHandler):
            raise_or_return = False
            for subsubnode in ast.walk(subnode):
                if isinstance(subsubnode, ast.Raise):
                    raise_or_return = True
                    break
                if isinstance(subsubnode, ast.Return):
                    if (
                        isinstance(subsubnode.value, ast.Call)
                        and subsubnode.value.func.id == "ActionResult"
                    ):
                        raise_or_return = True
                        break
                    if subsubnode.lineno in no_qa_lines:
                        raise_or_return = True
                        break

            if not raise_or_return:
                violations.append(
                    f"{file_path}:{subnode.lineno}:{subnode.col_offset + 1}: try/catch block without raise or ActionResult return"
                )
    return violations


def main(argv: list[str]) -> int:
    files = _iter_py_files(argv[1:])
    violations: list[str] = []

    for file_path in files:
        no_qa_lines = find_no_qa_lines(file_path)
        try:
            tree = ast.parse(
                file_path.read_text(encoding="utf-8"), filename=str(file_path)
            )
        except Exception as e:
            violations.append(f"{file_path}: failed to parse ({e})")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                print(f"Found try block in {file_path}:{node.lineno}")
                violations = sub_walk(node, violations, no_qa_lines, file_path)

    if violations:
        for v in violations:
            print(v)

        try_catch_count = sum(
            "try/catch block without raise or ActionResult return" in v
            for v in violations
        )

        print("\nSummary:")
        print(
            f"- try/catch blocks without raise or ActionResult return: {try_catch_count}"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
