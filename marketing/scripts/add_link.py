#!/usr/bin/env python3
"""Validate, dedupe, and persist marketing research links with logging.

Quickstart
----------
    cat <<'EOF' | python add_link.py --subdir drug_discovery --requests-per-minute 30 --dry-run
    https://atomwise.com
    https://benevolent.ai
    EOF

Agent playbook
--------------
1. Pipe either plain URLs or CSV rows into stdin (set ``--format csv`` when needed).
2. Begin with ``--dry-run`` to review duplicates and HTTP status codes.
3. Tune ``--max-retries`` / ``--timeout`` / ``--requests-per-minute`` for unstable hosts.
4. Apply ``--force`` only when you intentionally keep duplicates or soft failures.
5. Inspect ``logs/<subdir>/latest.log.json`` plus ``*_result.json`` for machine cues.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence, cast

from utils import (
    DEFAULT_ALLOWED_STATUS,
    ModulePaths,
    RateLimiter,
    StructuredLogger,
    build_retry_session,
    ensure_runtime,
    hint_for_error,
    load_schema_config,
)

ensure_runtime(Path(__file__))

Row = MutableMapping[str, Any]


@dataclass(slots=True)
class LinkOptions:
    subdir: str
    format: str
    dry_run: bool
    force: bool
    manifest_path: Path | None
    max_retries: int
    timeout: float
    backoff_factor: float
    requests_per_minute: float | None


@dataclass
class LinkOutcome:
    verified: list[Row] = field(default_factory=list)
    rejected: list[Row] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class LinkProcessor:
    """Handle link verification, dedupe, and persistence."""

    def __init__(self, paths: ModulePaths, options: LinkOptions, logger: StructuredLogger) -> None:
        self.paths = paths
        self.options = options
        self.logger = logger
        self.config = load_schema_config(paths, "link")

        allowed = self.config.get("url_checks", {}).get("allowed_status")
        self.allowed_status = set(int(code) for code in (allowed or DEFAULT_ALLOWED_STATUS))

        retry_cfg = self.config.get("retry", {})
        status_forcelist = retry_cfg.get("status_forcelist")
        self.session = build_retry_session(
            max_retries=retry_cfg.get("max_retries", options.max_retries),
            backoff_factor=retry_cfg.get("backoff_factor", options.backoff_factor),
            timeout=options.timeout,
            allowed_methods=["GET", "HEAD"],
            status_forcelist=status_forcelist,
        )
        self.method = str(self.config.get("url_checks", {}).get("method", "HEAD")).upper()
        self.headers = dict(self.config.get("url_checks", {}).get("headers", {"User-Agent": "Mozilla/5.0"}))
        self.rate_limiter = RateLimiter(options.requests_per_minute)

        self.base_dir = self.paths.links(options.subdir)
        self.verified_file = self.base_dir / "verified_links.csv"
        self.rejected_file = self.base_dir / "rejected_links.csv"

    def process(self, rows: Sequence[Row]) -> LinkOutcome:
        outcome = LinkOutcome()
        existing_urls = self._load_existing_urls()

        for row in rows:
            url = str(row.get("url", "")).strip()
            if not url:
                self.logger.log("WARN", "Skipping row without URL", level="WARN", details={"row": dict(row)})
                continue

            if url in existing_urls:
                outcome.duplicates.append(url)
                self.logger.log("WARN", f"Duplicate URL detected: {url}")
                if not self.options.force:
                    continue

            result = self._verify_url(row)
            if result.get("success"):
                self.logger.log("OK", f"Verified {url}", details={"status": result.get("status_code")})
                outcome.verified.append(result)
                existing_urls.add(url)
            else:
                error_msg = result.get("error", "Verification failed")
                hint = hint_for_error(error_msg)
                details = {"status": result.get("status_code"), "hint": hint} if hint else {"status": result.get("status_code")}
                self.logger.log("ERROR", f"Failed to verify {url}: {error_msg}", level="ERROR", details=details)
                outcome.rejected.append(result)
                outcome.errors.append(error_msg)

        return outcome

    def persist(self, outcome: LinkOutcome) -> None:
        if self.options.dry_run:
            self.logger.log("DRY_RUN", "Dry-run mode active; no CSV files written")
            return

        if outcome.verified:
            file_exists = self.verified_file.exists()
            with self.verified_file.open("a", newline="", encoding="utf-8") as handle:
                fieldnames = [
                    "url",
                    "final_url",
                    "status_code",
                    "company_name",
                    "source",
                    "verified_at",
                    "url_hash",
                ]
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(outcome.verified)

        if outcome.rejected:
            file_exists = self.rejected_file.exists()
            with self.rejected_file.open("a", newline="", encoding="utf-8") as handle:
                fieldnames = ["url", "error", "status_code", "attempted_at"]
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(outcome.rejected)

    def _load_existing_urls(self) -> set[str]:
        urls: set[str] = set()
        if self.verified_file.exists():
            with self.verified_file.open("r", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                urls = {row["url"] for row in reader if row.get("url")}
        return urls

    def _verify_url(self, row: Row) -> Row:
        import requests  # type: ignore[import-untyped]

        url = str(row.get("url", "")).strip()
        self.rate_limiter.wait()
        result: Row = {
            "url": url,
            "company_name": row.get("company_name", ""),
            "source": row.get("source", ""),
            "final_url": url,
            "status_code": None,
            "verified_at": datetime.now().isoformat(),
            "url_hash": None,
            "error": None,
            "success": False,
        }
        try:
            response = self.session.request(self.method, url, headers=self.headers, allow_redirects=True)
            status_code = response.status_code
            result["status_code"] = status_code
            if status_code not in self.allowed_status and self.method != "GET":
                response = self.session.request("GET", url, headers=self.headers, allow_redirects=True)
                status_code = response.status_code
                result["status_code"] = status_code
            if status_code in self.allowed_status:
                result["success"] = True
                result["final_url"] = getattr(response, "url", url)
                result["url_hash"] = self._hash_url(url)
            else:
                result["error"] = f"HTTP {status_code}"
        except requests.RequestException as error:
            result["error"] = str(error)[:200]
        return result

    @staticmethod
    def _hash_url(url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()[:8]


def parse_rows(raw: str, fmt: str) -> list[Row]:
    if not raw.strip():
        raise ValueError("No links provided via stdin")

    rows: list[Row] = []
    if fmt == "csv":
        reader = csv.DictReader(io.StringIO(raw))
        for row in reader:
            if not row.get("url"):
                continue
            rows.append(cast(Row, row))
    else:
        for line in raw.splitlines():
            line = line.strip()
            if line and line.startswith("http"):
                rows.append(cast(Row, {"url": line}))
    if not rows:
        raise ValueError("No valid links found in input")
    return rows


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and persist marketing research links")
    parser.add_argument("--subdir", required=True, help="Research subdirectory for outputs")
    parser.add_argument("--format", choices=["plain", "csv"], default="plain", help="Input format")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without writing files")
    parser.add_argument("--force", action="store_true", help="Override duplicate warnings or soft failures")
    parser.add_argument("--manifest", type=Path, help="Optional path for the result manifest JSON")
    parser.add_argument("--max-retries", type=int, default=3, help="HTTP retry attempts for link verification")
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout for verification calls")
    parser.add_argument("--backoff-factor", type=float, default=0.5, help="Retry backoff factor for verification calls")
    parser.add_argument(
        "--requests-per-minute",
        type=float,
        help="Throttle outbound verification requests to this many per minute",
    )
    return parser


def write_manifest(
    logger: StructuredLogger,
    summary: Mapping[str, Any],
    override_path: Path | None,
) -> Path:
    manifest_path = logger.flush_summary(summary)
    if override_path:
        with override_path.open("w", encoding="utf-8") as handle:
            json.dump({**summary, "generated_at": datetime.now().isoformat()}, handle, indent=2)
        return override_path
    return manifest_path


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    options = LinkOptions(
        subdir=args.subdir,
        format=args.format,
        dry_run=args.dry_run,
        force=args.force,
        manifest_path=args.manifest,
        max_retries=args.max_retries,
        timeout=args.timeout,
        backoff_factor=args.backoff_factor,
        requests_per_minute=args.requests_per_minute,
    )

    paths = ModulePaths(Path(__file__))
    logger = StructuredLogger(paths, "add_link", subdir=args.subdir)

    raw_input = sys.stdin.read().strip()
    try:
        rows = parse_rows(raw_input, options.format)
    except ValueError as error:
        logger.log("ERROR", str(error), level="ERROR")
        summary = {
            "status": "failed",
            "errors": [str(error)],
            "warnings": [],
            "dry_run": options.dry_run,
        }
        manifest = write_manifest(logger, summary, options.manifest_path)
        logger.log("RESULT", f"Link ingestion aborted (manifest: {manifest})", level="ERROR")
        raise SystemExit(1)

    logger.log("START", f"Processing {len(rows)} link(s) for {options.subdir}")

    processor = LinkProcessor(paths, options, logger)
    outcome = processor.process(rows)
    processor.persist(outcome)

    summary = {
        "status": "success" if outcome.verified or options.force else "partial",
        "verified": len(outcome.verified),
        "rejected": len(outcome.rejected),
        "duplicates": outcome.duplicates,
        "dry_run": options.dry_run,
    }
    if outcome.rejected and not options.force:
        summary["status"] = "needs_attention"
    if outcome.errors:
        summary["errors"] = outcome.errors

    manifest = write_manifest(logger, summary, options.manifest_path)
    logger.log(
        "RESULT",
        f"Processed {len(rows)} link(s); verified {len(outcome.verified)}, rejected {len(outcome.rejected)}",
    )
    logger.log("MANIFEST", f"Result manifest: {manifest}")

    if not outcome.verified and not options.force:
        raise SystemExit(1)


if __name__ == "__main__" and not os.environ.get("AMI_MARKETING_SKIP_MAIN"):  # pragma: no cover
    main()
