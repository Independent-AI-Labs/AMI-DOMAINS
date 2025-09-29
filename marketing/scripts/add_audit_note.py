#!/usr/bin/env python3
"""Append free-form markdown notes to the marketing audit trail.

Quickstart
----------
    cat <<'EOF' | python add_audit_note.py --title "March 2025 direction"
    Reprioritised agent research to focus on APAC growth accounts.
    EOF

Agent playbook
--------------
1. Capture narrative updates or clarifications as Markdown via stdin.
2. Use ``--title`` to hint at the purpose; defaults to first line of the note.
3. Dry-run to preview logging without mutating the audit trail.
4. Appenditions land in ``requirements-and-schemas/requirements/audit-trail.md``.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Mapping

from utils import ModulePaths, StructuredLogger, ensure_runtime

ensure_runtime(Path(__file__))

AUDIT_FILENAME = "audit-trail.md"
SEPARATOR = "\n---\n\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append Markdown notes to the marketing audit trail")
    parser.add_argument("--title", help="Optional heading for the entry")
    parser.add_argument("--manifest", type=Path, help="Optional path for manifest output")
    parser.add_argument("--dry-run", action="store_true", help="Record intent without writing to disk")
    return parser


def resolve_audit_path(paths: ModulePaths) -> Path:
    requirements_dir = paths.base / "requirements-and-schemas" / "requirements"
    requirements_dir.mkdir(parents=True, exist_ok=True)
    return requirements_dir / AUDIT_FILENAME


def wrap_entry(body: str, title: str | None) -> str:
    timestamp = datetime.now().isoformat(timespec="seconds")
    heading = title or body.strip().splitlines()[0]
    heading_line = heading.strip()
    entry_lines = [f"## {heading_line} ({timestamp})", "", body.strip(), SEPARATOR]
    return "\n".join(entry_lines)


def write_manifest(logger: StructuredLogger, summary: Mapping[str, object], manifest_path: Path | None) -> Path:
    manifest = logger.flush_summary(summary)
    if manifest_path is not None:
        with manifest_path.open("w", encoding="utf-8") as handle:
            import json
            from datetime import datetime as _dt

            json.dump({**summary, "generated_at": _dt.now().isoformat()}, handle, indent=2)
        return manifest_path
    return manifest


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    paths = ModulePaths(Path(__file__))
    logger = StructuredLogger(paths, "add_audit_note", subdir=None)

    body = sys.stdin.read().strip()
    if not body:
        logger.log("ERROR", "No Markdown provided via stdin", level="ERROR")
        summary = {"status": "failed", "errors": ["stdin empty"], "dry_run": args.dry_run}
        manifest = write_manifest(logger, summary, args.manifest)
        logger.log("RESULT", f"Audit note aborted (manifest: {manifest})", level="ERROR")
        raise SystemExit(1)

    if "initial-requirements.md" in body.lower():
        logger.log("WARN", "Initial requirements are immutable; note recorded separately", level="WARN")

    entry = wrap_entry(body, args.title)
    audit_path = resolve_audit_path(paths)

    if args.dry_run:
        logger.log("DRY_RUN", "Dry-run enabled; audit trail not modified")
    else:
        with audit_path.open("a", encoding="utf-8") as handle:
            handle.write(entry)
        logger.log("OK", f"Appended audit note to {audit_path}")

    summary = {
        "status": "success",
        "dry_run": args.dry_run,
        "audit_path": str(audit_path),
        "title": args.title or entry.splitlines()[0],
    }
    manifest = write_manifest(logger, summary, args.manifest)
    logger.log("RESULT", f"Audit entry recorded (manifest: {manifest})")


if __name__ == "__main__" and not os.environ.get("AMI_MARKETING_SKIP_MAIN"):  # pragma: no cover
    main()
