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

# This hook is intended to ratchet a small, curated set of production modules
# over time. It is still executed by pre-commit for any staged Python file, but
# we only report violations for files under this allowlist.
#
# Rationale: avoids overwhelming contributors while we incrementally migrate the
# codebase to structured logging patterns.
AUDITED_PATH_PREFIXES = {
    "src/madsci_common/madsci/common/",
    "src/madsci_event_manager/madsci/event_manager/",
    "src/madsci_resource_manager/madsci/resource_manager/",
    "src/madsci_location_manager/madsci/location_manager/",
    "src/madsci_data_manager/madsci/data_manager/",
    "src/madsci_experiment_manager/madsci/experiment_manager/",
    "src/madsci_workcell_manager/madsci/workcell_manager/",
    "src/madsci_node_module/madsci/node_module/",
    "src/madsci_squid/madsci/squid/",
    "src/madsci_client/madsci/client/",
    "src/madsci_common/tests/",
    "src/madsci_client/tests/",
}


def _is_audited(file_path: Path) -> bool:
    normalized = file_path.as_posix()
    return any(normalized.startswith(prefix) for prefix in AUDITED_PATH_PREFIXES)


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

    # Heuristic: stdlib logging calls can't accept arbitrary kwargs.
    value = func.value
    if isinstance(value, ast.Name):
        return value.id in {"logger", "log", "logging"}

    if isinstance(value, ast.Attribute):
        return value.attr == "logger"

    return False


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

    # Only enforce for known EventClient logger variables.
    # This avoids false positives on stdlib loggers (self.logger, logger, logging).
    target_obj = func.value
    if isinstance(target_obj, ast.Name):
        target_root = target_obj.id
    elif isinstance(target_obj, ast.Attribute):
        target_root = target_obj.attr
    else:
        target_root = None

    # Enforce only at EventClient boundary; raw structlog logger calls may
    # legitimately omit event_type.
    if target_root not in {"event_client"}:
        return False

    # Only enforce on EventClient/structlog-style calls.
    # stdlib logging calls can't accept arbitrary kwargs like event_type.
    if _is_stdlib_logger_call(node):
        return False

    return True


def main(argv: list[str]) -> int:
    files = _iter_py_files(argv[1:])
    violations: list[str] = []

    for file_path in files:
        if not _is_audited(file_path):
            continue
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
