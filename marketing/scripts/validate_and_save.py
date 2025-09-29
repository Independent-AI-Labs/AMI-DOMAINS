#!/usr/bin/env python3
"""Validate Claude-collected records and persist the approved result.

Usage highlights
----------------
    cat <<'EOF' | python validate_and_save.py --type company --subdir drug_discovery \
        --requests-per-minute 20 --dry-run
    {
        "vendor_name": "Atomwise",
        "website_url": "https://atomwise.com",
        "primary_offering": "AI drug discovery platform",
        "employee_band": "50_199",
        "hq_region": "na"
    }
    EOF

Playbook for agents
-------------------
1. Gather vendor facts via browsing, then pipe structured JSON into this script.
2. Start with ``--dry-run`` to surface schema or duplicate issues without writing files.
3. Inspect ``logs/<subdir>/latest.log.json`` for machine-readable state updates.
4. Re-run with ``--force`` only when you intentionally override warnings.
5. Tune ``--max-retries`` / ``--timeout`` or ``--requests-per-minute`` for flaky hosts.
6. Successful runs emit ``*_result.json`` so downstream orchestration can branch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, cast

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

ModelData = MutableMapping[str, Any]


@dataclass(slots=True)
class ValidationOptions:
    data_type: str
    subdir: str
    force: bool
    dry_run: bool
    manifest_path: Path | None
    max_retries: int
    timeout: float
    backoff_factor: float
    requests_per_minute: float | None


@dataclass
class ValidationOutcome:
    data: ModelData
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    saved_file: Path | None = None
    manifest_path: Path | None = None
    duplicate_detected: bool = False


class Validator:
    """Apply declarative validation rules and persistence helpers."""

    def __init__(self, paths: ModulePaths, options: ValidationOptions, logger: StructuredLogger) -> None:
        self.paths = paths
        self.options = options
        self.logger = logger
        self.schema = load_schema_config(paths, options.data_type)

        url_cfg = self.schema.get("url_checks", {})
        allowed = url_cfg.get("allowed_status")
        self.allowed_status = set(int(code) for code in (allowed or DEFAULT_ALLOWED_STATUS))
        self.method = str(url_cfg.get("method", "HEAD")).upper()
        self.headers = dict(url_cfg.get("headers", {"User-Agent": "Mozilla/5.0"}))

        retry_cfg = self.schema.get("retry", {})
        status_forcelist: Iterable[int] | None = retry_cfg.get("status_forcelist") or url_cfg.get("retry_status")
        self.session = build_retry_session(
            max_retries=retry_cfg.get("max_retries", options.max_retries),
            backoff_factor=retry_cfg.get("backoff_factor", options.backoff_factor),
            timeout=options.timeout,
            allowed_methods=["GET", "HEAD"],
            status_forcelist=status_forcelist,
        )
        self.rate_limiter = RateLimiter(options.requests_per_minute)

    def validate(self, data: ModelData) -> ValidationOutcome:
        outcome = ValidationOutcome(data=data)
        required_fields = self.schema.get("required", [])
        field_rules = self.schema.get("fields", {})

        for required_field in required_fields:
            if not str(data.get(required_field, "")).strip():
                outcome.errors.append(f"Missing required field: {required_field}")

        for field_name, rules in field_rules.items():
            value = data.get(field_name)
            presence = rules.get("presence", "optional")
            if value is None:
                if presence == "recommended":
                    outcome.warnings.append(f"Recommended field missing: {field_name}")
                continue

            rule_type = rules.get("type", "string")
            if rule_type == "string":
                if not isinstance(value, str):
                    outcome.errors.append(f"{field_name}: expected string, got {type(value).__name__}")
                    continue
                min_length = rules.get("min_length")
                max_length = rules.get("max_length")
                if isinstance(min_length, int) and len(value) < min_length:
                    outcome.errors.append(f"{field_name}: too short (min {min_length})")
                if isinstance(max_length, int) and len(value) > max_length:
                    outcome.errors.append(f"{field_name}: too long (max {max_length})")
            elif rule_type == "enum":
                allowed_values = rules.get("values", [])
                if value not in allowed_values:
                    outcome.errors.append(f"{field_name}: '{value}' not in allowed values {allowed_values}")
            elif rule_type == "url":
                if not isinstance(value, str) or not value.startswith("http"):
                    outcome.errors.append(f"{field_name}: must be a valid HTTP(S) URL")

        website_url = data.get("website_url")
        if isinstance(website_url, str) and website_url.startswith("http"):
            self.logger.log("VERIFY", f"Checking {website_url}")
            if not self._verify_url(website_url):
                outcome.errors.append("website_url: URL does not exist or is not accessible")

        duplicate_keys = self.schema.get("duplicates", {}).get("keys", ["vendor_name", "website_url"])
        if self._is_duplicate(data, duplicate_keys):
            outcome.duplicate_detected = True
            outcome.errors.append("Duplicate entry - already exists")

        return outcome

    def _verify_url(self, url: str) -> bool:
        import requests  # type: ignore[import-untyped]

        self.rate_limiter.wait()
        try:
            response = self.session.request(self.method, url, headers=self.headers, allow_redirects=True)
            status_ok = response.status_code in self.allowed_status
            if not status_ok and self.method != "GET":
                response = self.session.request("GET", url, headers=self.headers, allow_redirects=True)
                status_ok = response.status_code in self.allowed_status
            self.logger.log(
                "VERIFY_RESULT",
                f"{url} -> HTTP {response.status_code}",
                details={"status": response.status_code, "final_url": getattr(response, "url", url)},
            )
            return status_ok
        except requests.RequestException as error:
            self.logger.log("VERIFY_ERROR", f"Request failed for {url}: {error}", level="ERROR")
            return False

    def _is_duplicate(self, data: Mapping[str, Any], keys: Iterable[str]) -> bool:
        models_dir = self.paths.base / "data-models" / "validated" / self.options.subdir / "data"
        if not models_dir.exists():
            return False
        for json_file in models_dir.glob("*.json"):
            with json_file.open("r", encoding="utf-8") as handle:
                existing = json.load(handle)
            for key in keys:
                if not existing.get(key) or not data.get(key):
                    continue
                if str(existing[key]).lower() == str(data[key]).lower():
                    self.logger.log("DUPLICATE", f"Existing record matches on {key}: {json_file.name}")
                    return True
        return False

    def save(self, data: ModelData) -> Path:
        vendor_name = str(data.get("vendor_name", "unknown"))
        slug = vendor_name.lower().replace(" ", "_").replace(".", "")
        slug = "".join(char for char in slug if char.isalnum() or char == "_")
        models_dir = self.paths.data_models(self.options.subdir)

        model_id_source = f"{vendor_name}{data.get('website_url', '')}".encode()
        data["model_id"] = hashlib.md5(model_id_source).hexdigest()[:8]
        data["date_saved"] = datetime.now().isoformat()
        data["validated"] = True

        model_file = models_dir / f"{slug}.json"
        if model_file.exists():
            counter = 1
            while (models_dir / f"{slug}_v{counter}.json").exists():
                counter += 1
            model_file = models_dir / f"{slug}_v{counter}.json"

        with model_file.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

        return model_file


def parse_input(raw: str) -> ModelData:
    if not raw:
        raise ValueError("No data provided via stdin")

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return cast(ModelData, parsed)
    except json.JSONDecodeError:
        pass

    data: ModelData = cast(ModelData, {})
    for line in iter_non_empty_lines(raw):
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()

    if not data:
        raise ValueError("Could not parse input data")
    return data


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate, dedupe, and persist marketing research records")
    parser.add_argument("--type", default="company", help="Schema type to validate against (company, link, ...)")
    parser.add_argument("--subdir", required=True, help="Research subdirectory to route output into")
    parser.add_argument("--force", action="store_true", help="Override warnings and duplicates")
    parser.add_argument("--dry-run", action="store_true", help="Run validation without writing to disk")
    parser.add_argument("--manifest", type=Path, help="Optional path for the result manifest JSON")
    parser.add_argument("--max-retries", type=int, default=3, help="HTTP retry attempts for URL verification")
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

    options = ValidationOptions(
        data_type=args.type,
        subdir=args.subdir,
        force=args.force,
        dry_run=args.dry_run,
        manifest_path=args.manifest,
        max_retries=args.max_retries,
        timeout=args.timeout,
        backoff_factor=args.backoff_factor,
        requests_per_minute=args.requests_per_minute,
    )

    paths = ModulePaths(Path(__file__))
    logger = StructuredLogger(paths, "validate_and_save", subdir=args.subdir)

    try:
        raw_input = sys.stdin.read().strip()
        data = parse_input(raw_input)
    except ValueError as error:
        logger.log("ERROR", str(error), level="ERROR")
        summary = {
            "status": "failed",
            "errors": [str(error)],
            "warnings": [],
            "dry_run": options.dry_run,
        }
        manifest = write_manifest(logger, summary, options.manifest_path)
        logger.log("RESULT", f"Validation aborted (manifest: {manifest})", level="ERROR")
        sys.exit(1)

    logger.log("START", f"Validating {data.get('vendor_name', 'unknown vendor')} ({options.data_type})")

    validator = Validator(paths, options, logger)
    outcome = validator.validate(data)

    if outcome.errors and not options.force:
        for error in outcome.errors:
            hint = hint_for_error(error)
            details = {"hint": hint} if hint else {}
            logger.log("ERROR", error, level="ERROR", details=details)
        summary = {
            "status": "failed",
            "errors": outcome.errors,
            "warnings": outcome.warnings,
            "dry_run": options.dry_run,
            "duplicate_detected": outcome.duplicate_detected,
        }
        manifest = write_manifest(logger, summary, options.manifest_path)
        logger.log("RESULT", f"Validation failed (manifest: {manifest})", level="ERROR")
        sys.exit(1)

    if outcome.warnings and not options.force:
        for warning in outcome.warnings:
            hint = hint_for_error(warning)
            details = {"hint": hint} if hint else {}
            logger.log("WARN", warning, level="WARN", details=details)
        summary = {
            "status": "needs_attention",
            "errors": outcome.errors,
            "warnings": outcome.warnings,
            "dry_run": options.dry_run,
            "duplicate_detected": outcome.duplicate_detected,
        }
        manifest = write_manifest(logger, summary, options.manifest_path)
        logger.log("RESULT", "Warnings present – rerun with --force when appropriate", level="WARN")
        sys.exit(1)

    if not options.dry_run:
        saved_path = validator.save(data)
        outcome.saved_file = saved_path
        logger.log("OK", f"Saved model to {saved_path}")
    else:
        logger.log("DRY_RUN", "Dry-run mode active; no files written")

    summary = {
        "status": "success",
        "warnings": outcome.warnings,
        "errors": outcome.errors,
        "dry_run": options.dry_run,
        "saved_file": str(outcome.saved_file) if outcome.saved_file else None,
        "duplicate_detected": outcome.duplicate_detected,
    }

    manifest = write_manifest(logger, summary, options.manifest_path)
    outcome.manifest_path = manifest
    logger.log("RESULT", f"Validation complete (manifest: {manifest})")


if __name__ == "__main__" and not os.environ.get("AMI_MARKETING_SKIP_MAIN"):  # pragma: no cover
    main()
