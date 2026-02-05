#!/usr/bin/env python3

from __future__ import annotations

import ast
import sys
from pathlib import Path

TARGET_METHODS = {
    # Structlog/EventClient style
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    "log_debug",
    "log_info",
    "log_warning",
    "log_error",
    "log_critical",
    # stdlib logging style
    "exception",
}


def _iter_py_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            files.extend([pp for pp in path.rglob("*.py") if pp.is_file()])
        elif path.is_file() and path.suffix == ".py":
            files.append(path)
    return files


def _is_target_call(node: ast.Call) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr not in TARGET_METHODS:
        return False
    return True


def _has_kw(node: ast.Call, name: str) -> bool:
    return any(isinstance(kw, ast.keyword) and kw.arg == name for kw in node.keywords)


def _has_fstring_arg(node: ast.Call) -> bool:
    for arg in node.args:
        if isinstance(arg, ast.JoinedStr):
            return True
    return False


def _is_stdlib_logger_call(node: ast.Call) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if not isinstance(func.value, ast.Name):
        return False

    # Heuristic: logging.getLogger(...).info(...) patterns become `logger.info(...)`
    # and often use `%s` formatting rather than structured kwargs.
    return func.value.id in {"logger", "log", "logging"}


def _requires_event_type(node: ast.Call) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False

    if func.attr not in {
        "info",
        "warning",
        "error",
        "critical",
        "log_info",
        "log_warning",
        "log_error",
        "log_critical",
    }:
        return False

    if _is_stdlib_logger_call(node):
        return False

    return True


def main(argv: list[str]) -> int:
    files = _iter_py_files(argv[1:])
    violations: list[str] = []

    for file_path in files:
        try:
            tree = ast.parse(
                file_path.read_text(encoding="utf-8"), filename=str(file_path)
            )
        except Exception as e:
            violations.append(f"{file_path}: failed to parse ({e})")
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not _is_target_call(node):
                continue

            if _has_fstring_arg(node):
                violations.append(
                    f"{file_path}:{node.lineno}:{node.col_offset + 1}: f-string used in log call"
                )

            if not _requires_event_type(node):
                continue

            if not _has_kw(node, "event_type"):
                violations.append(
                    f"{file_path}:{node.lineno}:{node.col_offset + 1}: missing event_type kwarg"
                )

    if violations:
        for v in violations:
            print(v)

        fstring_count = sum("f-string used in log call" in v for v in violations)
        missing_event_type_count = sum(
            "missing event_type kwarg" in v for v in violations
        )
        parse_fail_count = sum("failed to parse" in v for v in violations)

        print("\nSummary:")
        print(f"- files scanned: {len(set(p for p in files))}")
        print(f"- violations: {len(violations)}")
        print(f"- f-strings in log calls: {fstring_count}")
        print(f"- missing event_type: {missing_event_type_count}")
        if parse_fail_count:
            print(f"- parse failures: {parse_fail_count}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
