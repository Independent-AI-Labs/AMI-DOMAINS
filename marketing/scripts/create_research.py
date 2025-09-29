#!/usr/bin/env python3
"""Scaffold a new marketing research workspace with immutable requirements.

Usage
-----
    cat <<'EOF' | python create_research.py ai-safety --title "AI Safety Landscape"
    ## Objective
    Map major AI safety tooling vendors.
    EOF

The script bootstraps the canonical directory layout, writes the initial
requirements (immutable), and prepares supporting notebooks/log folders so
agents can begin validated research immediately.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from utils import ModulePaths, StructuredLogger, ensure_runtime

ensure_runtime(Path(__file__))

MODULE_ROOT = Path(__file__).resolve().parent.parent
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
BROWSER_REMINDER = "Browser MCP tool (the only trusted source of content)"
DEFAULT_AUDIT_TEMPLATE = """# Audit Trail\n\nAll updates after the immutable initial requirements live here.\nAppend via scripts (e.g. add_audit_note.py) for traceability.\n"""


@dataclass(slots=True)
class ScaffoldOptions:
    slug: str
    title: str
    requirements_body: str
    dry_run: bool = False
    force: bool = False
    manifest_path: Path | None = None
    include_audit: bool = True


@dataclass(slots=True)
class ScaffoldOutcome:
    research_root: Path
    created_directories: List[Path]
    created_files: Dict[str, Path]
    dry_run: bool
    existed: bool


class ResearchScaffold:
    def __init__(self, options: ScaffoldOptions, *, module_root: Path = MODULE_ROOT, script_path: Path | None = None) -> None:
        self.options = options
        self.module_root = module_root
        self.script_path = script_path or Path(__file__)
        self.research_root = self.module_root / "research" / options.slug

    def _validate(self) -> None:
        if not SLUG_PATTERN.match(self.options.slug):
            raise ValueError(f"Slug '{self.options.slug}' must match {SLUG_PATTERN.pattern}")
        if not self.options.requirements_body.strip():
            raise ValueError("Initial requirements body cannot be empty")

        requirements_path = self._requirements_path()
        if requirements_path.exists():
            raise FileExistsError(
                "initial-requirements.md already exists; requirements are immutable"
            )
        if self.research_root.exists() and not self.options.force:
            raise FileExistsError(
                f"Research directory {self.research_root} already exists; pass --force to extend it"
            )

    def _requirements_path(self) -> Path:
        return self.research_root / "requirements-and-schemas" / "requirements" / "initial-requirements.md"

    def _audit_path(self) -> Path:
        return self.research_root / "requirements-and-schemas" / "requirements" / "audit-trail.md"

    def _compose_requirements(self) -> str:
        body = self.options.requirements_body.strip()
        lines: List[str] = []

        if not body.lstrip().startswith("#"):
            lines.append(f"# {self.options.title}")
            lines.append("")
            lines.append(body)
        else:
            lines.append(body)

        normalized = "\n".join(lines).lower()
        if "browser mcp" not in normalized:
            lines.append("")
            lines.append(f"> Reminder: The {BROWSER_REMINDER}.")

        if not lines[-1].endswith("\n"):
            lines[-1] = lines[-1] + "\n"

        return "\n".join(lines).rstrip() + "\n"

    def run(self) -> ScaffoldOutcome:
        existed = self.research_root.exists()
        if not self.options.force and existed:
            # _validate will raise appropriately, but we guard early to avoid incidental writes
            raise FileExistsError(
                f"Research directory {self.research_root} already exists; pass --force to extend it"
            )

        self._validate()

        requirements_path = self._requirements_path()
        audit_path = self._audit_path()

        directories = [
            self.research_root,
            self.research_root / "data-models",
            self.research_root / "data-models" / "validated",
            self.research_root / "downloads",
            self.research_root / "logs",
            self.research_root / "links-and-sources",
            self.research_root / "links-and-sources" / "validated",
            self.research_root / "requirements-and-schemas",
            requirements_path.parent,
            self.research_root / "requirements-and-schemas" / "schemas",
        ]

        created_dirs: List[Path] = []
        created_files: Dict[str, Path] = {}

        if self.options.dry_run:
            return ScaffoldOutcome(self.research_root, directories, created_files, True, existed)

        for directory in directories:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                created_dirs.append(directory)

        requirements_content = self._compose_requirements()
        requirements_path.write_text(requirements_content, encoding="utf-8")
        created_files["initial_requirements"] = requirements_path

        if self.options.include_audit and not audit_path.exists():
            audit_path.write_text(DEFAULT_AUDIT_TEMPLATE, encoding="utf-8")
            created_files["audit_trail"] = audit_path

        paths = ModulePaths(self.script_path, research_root=self.research_root)
        logger = StructuredLogger(paths, "create_research", subdir=self.options.slug)
        logger.log("OK", f"Scaffold ready at {self.research_root}")
        summary = {
            "status": "success",
            "dry_run": False,
            "research_root": str(self.research_root),
            "created_directories": [str(p) for p in created_dirs],
            "created_files": {key: str(value) for key, value in created_files.items()},
        }
        manifest = logger.flush_summary(summary)

        if self.options.manifest_path is not None:
            self.options.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            self.options.manifest_path.write_text(
                manifest.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

        logger.log("RESULT", f"Scaffold complete (manifest: {manifest})")
        return ScaffoldOutcome(self.research_root, created_dirs, created_files, False, existed)


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create marketing research scaffolding")
    parser.add_argument("slug", help="Directory name under research/ e.g. ai-enablers")
    parser.add_argument("--title", help="Human readable title", default=None)
    parser.add_argument(
        "--requirements-file",
        type=Path,
        help="Path to Markdown containing the initial requirements (defaults to stdin)",
    )
    parser.add_argument("--force", action="store_true", help="Allow scaffolding when directory already exists")
    parser.add_argument("--dry-run", action="store_true", help="Report planned actions without writing to disk")
    parser.add_argument("--manifest", type=Path, help="Optional path to write the JSON manifest")
    parser.add_argument("--skip-audit", action="store_true", help="Do not create audit-trail.md placeholder")
    return parser.parse_args(argv)


def load_requirements_text(requirements_file: Path | None) -> str:
    if requirements_file is not None:
        return requirements_file.read_text(encoding="utf-8").strip()
    data = sys.stdin.read().strip()
    if not data:
        raise ValueError("Provide initial requirements via stdin or --requirements-file")
    return data


def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv)
    slug = args.slug.strip().lower()
    title = args.title or slug.replace("-", " ").replace("_", " ").title()

    try:
        body = load_requirements_text(args.requirements_file)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    options = ScaffoldOptions(
        slug=slug,
        title=title,
        requirements_body=body,
        dry_run=args.dry_run,
        force=args.force,
        manifest_path=args.manifest,
        include_audit=not args.skip_audit,
    )

    scaffold = ResearchScaffold(options)

    try:
        outcome = scaffold.run()
    except FileExistsError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    if outcome.dry_run:
        print("DRY-RUN: would create the following directories:")
        for directory in outcome.created_directories:
            print(f"  - {directory}")
        print("No files were created.")


if __name__ == "__main__" and not os.environ.get("AMI_MARKETING_SKIP_MAIN"):
    main()
