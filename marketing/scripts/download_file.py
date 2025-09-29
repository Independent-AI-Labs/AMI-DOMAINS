#!/usr/bin/env python3
"""Download marketing research artefacts with stealth defaults and manifest output.

Quickstart
----------
    python download_file.py --url https://example.com/data.csv --subdir reports --dry-run
    echo "https://example.com/file.pdf" | python download_file.py --subdir insights

Agent playbook
--------------
1. Provide one or more URLs via ``--url`` or stdin (one per line).
2. Run with ``--dry-run`` to confirm status codes and destination paths.
3. Adjust ``--max-retries`` / ``--timeout`` / ``--requests-per-minute`` for noisy hosts.
4. Use ``--force`` to ignore non-200 responses you intentionally accept.
5. Inspect ``logs/<subdir>/latest.log.json`` and ``*_result.json`` for structured outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, MutableMapping, cast

from utils import (
    DEFAULT_ALLOWED_STATUS,
    ModulePaths,
    RateLimiter,
    StructuredLogger,
    build_retry_session,
    ensure_runtime,
    hint_for_error,
    iter_non_empty_lines,
    load_schema_config,
)

ensure_runtime(Path(__file__))

DownloadResult = MutableMapping[str, Any]


@dataclass(slots=True)
class DownloadOptions:
    urls: list[str]
    output: Path | None
    subdir: str | None
    dry_run: bool
    force: bool
    manifest_path: Path | None
    max_retries: int
    timeout: float
    backoff_factor: float
    requests_per_minute: float | None


@dataclass
class DownloadOutcome:
    results: list[DownloadResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def successful(self) -> int:
        return sum(1 for result in self.results if result.get("success"))

    @property
    def failed(self) -> int:
        return sum(1 for result in self.results if not result.get("success"))


class DownloadManager:
    """Handle network fetches with retry, stealth headers, and logging."""

    def __init__(self, paths: ModulePaths, options: DownloadOptions, logger: StructuredLogger) -> None:
        self.paths = paths
        self.options = options
        self.logger = logger
        self.config = load_schema_config(paths, "download")

        url_cfg = self.config.get("url_checks", {})
        allowed = url_cfg.get("allowed_status")
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
        self.rate_limiter = RateLimiter(options.requests_per_minute)
        self.headers = dict(self.config.get("headers", {})) or self._default_headers()
        self.scraper = self._create_scraper()

    def _default_headers(self) -> Mapping[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        }

    def _create_scraper(self) -> Any | None:
        try:
            module = importlib.import_module("cloudscraper")
            create_scraper = getattr(module, "create_scraper")
            return create_scraper(browser={"browser": "chrome", "platform": "windows", "desktop": True})
        except Exception as error:  # noqa: BLE001 - surface but continue
            self.logger.log("WARN", f"Cloudscraper unavailable: {error}; falling back to requests")
            return None

    def download_all(self) -> DownloadOutcome:
        outcome = DownloadOutcome()
        for url in self.options.urls:
            url = url.strip()
            if not url:
                continue
            self.logger.log("DOWNLOAD", f"Fetching {url}")
            result = self._download_single(url)
            outcome.results.append(result)
            if not result.get("success"):
                outcome.errors.append(result.get("error", "Unknown error"))
        return outcome

    def _download_single(self, url: str) -> DownloadResult:
        import requests  # type: ignore[import-untyped]

        self.rate_limiter.wait()
        result: DownloadResult = {
            "url": url,
            "success": False,
            "status_code": None,
            "output_path": None,
            "size_bytes": None,
            "error": None,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            response = self._make_request(url)
            status_code = response.status_code
            result["status_code"] = status_code
            if status_code not in self.allowed_status and not self.options.force:
                result["error"] = f"HTTP {status_code}"
                self.logger.log("ERROR", f"{url} responded with HTTP {status_code}", level="ERROR")
                return result

            output_path = self._resolve_output_path(url, response)
            result["output_path"] = str(output_path)
            if self.options.dry_run:
                self.logger.log("DRY_RUN", f"Dry-run; skipping download to {output_path}")
                result["success"] = True
                return result

            total_bytes = 0
            with output_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    total_bytes += len(chunk)
            result["success"] = True
            result["size_bytes"] = total_bytes
            self.logger.log("OK", f"Saved {output_path} ({total_bytes:,} bytes)")
            return result
        except requests.RequestException as error:
            message = str(error)[:200]
            result["error"] = message
            hint = hint_for_error(message)
            details = {"hint": hint} if hint else {}
            self.logger.log("ERROR", f"Failed to download {url}: {message}", level="ERROR", details=details)
            if self.options.force:
                self.logger.log("WARN", "--force enabled; keeping failure for manifest only", level="WARN")
            return result

    def _make_request(self, url: str):  # type: ignore[no-untyped-def]
        if self.scraper is not None:
            return cast(Any, self.scraper.get(url, headers=self.headers, timeout=self.options.timeout, stream=True))
        return self.session.get(url, headers=self.headers, stream=True)

    def _resolve_output_path(self, url: str, response: Any) -> Path:
        if self.options.output:
            self.options.output.parent.mkdir(parents=True, exist_ok=True)
            return self.options.output
        downloads_dir = self.paths.downloads(self.options.subdir or "general")
        filename = self._filename_from_response(url, response)
        return downloads_dir / filename

    def _filename_from_response(self, url: str, response: Any) -> str:
        disposition = response.headers.get("content-disposition") if hasattr(response, "headers") else None
        if disposition:
            import re

            match = re.search(r'filename="?([^";]+)"?', disposition)
            if match:
                return match.group(1)
        from urllib.parse import unquote, urlparse

        parsed = urlparse(url)
        candidate = unquote(Path(parsed.path).name)
        if candidate:
            return candidate
        return f"download_{hashlib.md5(url.encode()).hexdigest()[:8]}"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download marketing research artefacts with structured logs")
    parser.add_argument("--url", help="Single URL to download (stdin also accepted)")
    parser.add_argument("--output", type=Path, help="Exact file path to write" )
    parser.add_argument("--subdir", help="Research subdirectory for downloads")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing downloaded files")
    parser.add_argument("--force", action="store_true", help="Keep manifest success even on HTTP errors")
    parser.add_argument("--manifest", type=Path, help="Optional path for the result manifest JSON")
    parser.add_argument("--max-retries", type=int, default=3, help="HTTP retry attempts for downloads")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout for downloads")
    parser.add_argument("--backoff-factor", type=float, default=0.5, help="Retry backoff factor for downloads")
    parser.add_argument(
        "--requests-per-minute",
        type=float,
        help="Throttle outbound download requests to this many per minute",
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


def gather_urls(args: argparse.Namespace) -> list[str]:
    urls: list[str] = []
    if args.url:
        urls.append(args.url.strip())
    stdin_payload = sys.stdin.read().strip()
    if stdin_payload:
        urls.extend(list(iter_non_empty_lines(stdin_payload)))
    urls = [url for url in urls if url.startswith("http")]
    if not urls:
        raise ValueError("No URLs provided")
    return urls


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    paths = ModulePaths(Path(__file__))
    logger = StructuredLogger(paths, "download_file", subdir=args.subdir or "general")

    try:
        urls = gather_urls(args)
    except ValueError as error:
        logger.log("ERROR", str(error), level="ERROR")
        summary = {"status": "failed", "errors": [str(error)], "warnings": [], "dry_run": args.dry_run}
        manifest = write_manifest(logger, summary, args.manifest)
        logger.log("RESULT", f"Download aborted (manifest: {manifest})", level="ERROR")
        raise SystemExit(1)

    logger.log("START", f"Downloading {len(urls)} file(s)")

    options = DownloadOptions(
        urls=urls,
        output=args.output,
        subdir=args.subdir,
        dry_run=args.dry_run,
        force=args.force,
        manifest_path=args.manifest,
        max_retries=args.max_retries,
        timeout=args.timeout,
        backoff_factor=args.backoff_factor,
        requests_per_minute=args.requests_per_minute,
    )

    manager = DownloadManager(paths, options, logger)
    outcome = manager.download_all()

    if not options.dry_run:
        for result in outcome.results:
            if result.get("success") and result.get("output_path"):
                logger.log("SAVED", f"Stored at {result['output_path']}")

    summary = {
        "status": "success" if outcome.successful or options.force else "failed",
        "downloads": len(outcome.results),
        "successful": outcome.successful,
        "failed": outcome.failed,
        "dry_run": options.dry_run,
        "force": options.force,
        "errors": outcome.errors,
        "outputs": [result.get("output_path") for result in outcome.results if result.get("output_path")],
    }
    manifest = write_manifest(logger, summary, options.manifest_path)
    logger.log("RESULT", f"Downloads complete ({outcome.successful} succeeded, {outcome.failed} failed)")
    logger.log("MANIFEST", f"Result manifest: {manifest}")

    if outcome.failed and not options.force:
        raise SystemExit(1)


if __name__ == "__main__" and not os.environ.get("AMI_MARKETING_SKIP_MAIN"):  # pragma: no cover
    main()
