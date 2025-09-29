#!/usr/bin/env python3
"""Validate and persist proposed JSON Schemas for marketing data models.

Quickstart
----------
    cat <<'EOF' | python propose_schema.py --name vendor_profile --dry-run
    {
      "title": "Vendor Profile",
      "type": "object",
      "required": ["vendor_name", "website_url"],
      "properties": {
        "vendor_name": {"type": "string", "minLength": 1},
        "website_url": {"type": "string", "format": "uri"}
      },
      "additionalProperties": false
    }
    EOF

Agent playbook
--------------
1. Collect schema draft text (JSON) from your reasoning environment.
2. Pipe it into this script with ``--dry-run`` to surface modelling issues.
3. Use ``--force`` to overwrite an existing schema intentionally.
4. Review ``schemas/<name>.schema.json`` and manifest output when satisfied.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

from utils import ModulePaths, StructuredLogger, ensure_runtime

ensure_runtime(Path(__file__))

SchemaDict = MutableMapping[str, Any]


ALLOWED_PRIMITIVE_TYPES = {"string", "number", "integer", "boolean", "array", "object"}
FORMAT_ALLOWED_FOR_TYPE = {
    "uri": {"string"},
    "date": {"string"},
    "date-time": {"string"},
    "email": {"string"},
}


@dataclass(slots=True)
class SchemaOptions:
    name: str
    dry_run: bool
    force: bool
    manifest_path: Path | None


@dataclass
class SchemaValidationResult:
    schema: SchemaDict
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class SchemaValidator:
    """Apply marketing data modelling rules to a proposed JSON schema."""

    def __init__(self, options: SchemaOptions, paths: ModulePaths, logger: StructuredLogger) -> None:
        self.options = options
        self.paths = paths
        self.logger = logger

    def validate(self, schema: SchemaDict) -> SchemaValidationResult:
        result = SchemaValidationResult(schema=schema)

        if not isinstance(schema, dict):
            result.errors.append("Schema must be a JSON object")
            return result

        self._require(schema, "title", str, result)
        self._require(schema, "type", str, result)
        if schema.get("type") != "object":
            result.errors.append("Schema root type must be 'object'")

        properties = schema.get("properties")
        if not isinstance(properties, dict) or not properties:
            result.errors.append("Schema must define non-empty 'properties' object")
        else:
            self._validate_properties(properties, result)

        required = schema.get("required")
        if not isinstance(required, list) or not required:
            result.errors.append("Schema must declare a non-empty 'required' array")
        else:
            self._validate_required(required, properties, result)

        if "additionalProperties" not in schema:
            result.warnings.append("'additionalProperties' missing; defaults to true")

        return result

    def _require(self, schema: Mapping[str, Any], key: str, expected_type: type, result: SchemaValidationResult) -> None:
        value = schema.get(key)
        if value is None:
            result.errors.append(f"Missing required property: {key}")
            return
        if not isinstance(value, expected_type):
            result.errors.append(f"Property '{key}' must be of type {expected_type.__name__}")

    def _validate_properties(self, properties: Mapping[str, Any], result: SchemaValidationResult) -> None:
        for field_name, definition in properties.items():
            if not re.match(r"^[a-z][a-z0-9_]*$", field_name):
                result.errors.append(f"Field '{field_name}' must be snake_case")
            if not isinstance(definition, dict):
                result.errors.append(f"Definition for '{field_name}' must be an object")
                continue
            field_type = definition.get("type")
            if field_type not in ALLOWED_PRIMITIVE_TYPES:
                result.errors.append(f"Field '{field_name}' has unsupported type '{field_type}'")
            if field_type == "array" and "items" not in definition:
                result.errors.append(f"Array field '{field_name}' must declare 'items'")
            fmt = definition.get("format")
            if fmt is not None:
                allowed = FORMAT_ALLOWED_FOR_TYPE.get(fmt)
                if allowed is None:
                    result.warnings.append(f"Field '{field_name}' uses non-standard format '{fmt}'")
                elif field_type not in allowed:
                    result.errors.append(f"Format '{fmt}' is incompatible with type '{field_type}' on '{field_name}'")
            enum_values = definition.get("enum")
            if enum_values is not None:
                if not isinstance(enum_values, Sequence) or isinstance(enum_values, (str, bytes)):
                    result.errors.append(f"Field '{field_name}' enum must be an array of distinct values")
                else:
                    if len(set(enum_values)) != len(list(enum_values)):
                        result.errors.append(f"Field '{field_name}' enum contains duplicate values")
            description = definition.get("description")
            if description and len(str(description)) > 512:
                result.warnings.append(f"Field '{field_name}' description is unusually long (>512 chars)")

    def _validate_required(
        self,
        required: Sequence[Any],
        properties: Mapping[str, Any] | None,
        result: SchemaValidationResult,
    ) -> None:
        seen = set()
        for item in required:
            if not isinstance(item, str):
                result.errors.append("All entries in 'required' must be strings")
                continue
            if item in seen:
                result.errors.append(f"Duplicate entry '{item}' in 'required'")
                continue
            seen.add(item)
            if properties is not None and item not in properties:
                result.errors.append(f"Required field '{item}' missing from properties")


def write_manifest(logger: StructuredLogger, summary: Mapping[str, Any], manifest_path: Path | None) -> Path:
    manifest = logger.flush_summary(summary)
    if manifest_path is not None:
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump({**summary, "generated_at": datetime.now().isoformat()}, handle, indent=2)
        return manifest_path
    return manifest


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate proposed JSON schemas for marketing research data models")
    parser.add_argument("--name", required=True, help="Schema name (used for output filename)")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing schema to disk")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing schema")
    parser.add_argument("--manifest", type=Path, help="Optional manifest output path")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    options = SchemaOptions(name=args.name, dry_run=args.dry_run, force=args.force, manifest_path=args.manifest)
    paths = ModulePaths(Path(__file__))
    logger = StructuredLogger(paths, "propose_schema", subdir=None)

    raw = sys.stdin.read().strip()
    if not raw:
        logger.log("ERROR", "No schema proposal provided via stdin", level="ERROR")
        manifest = write_manifest(logger, {"status": "failed", "errors": ["stdin empty"], "dry_run": options.dry_run}, options.manifest_path)
        logger.log("RESULT", f"Schema proposal aborted (manifest: {manifest})", level="ERROR")
        raise SystemExit(1)

    try:
        proposed = json.loads(raw)
    except json.JSONDecodeError as error:
        logger.log("ERROR", f"Invalid JSON: {error}", level="ERROR")
        manifest = write_manifest(
            logger,
            {"status": "failed", "errors": [f"json_error: {error}"], "dry_run": options.dry_run},
            options.manifest_path,
        )
        logger.log("RESULT", f"Schema proposal aborted (manifest: {manifest})", level="ERROR")
        raise SystemExit(1)

    validator = SchemaValidator(options, paths, logger)
    result = validator.validate(proposed)

    if result.errors:
        for error in result.errors:
            logger.log("ERROR", error, level="ERROR")
        summary = {"status": "failed", "errors": result.errors, "warnings": result.warnings, "dry_run": options.dry_run}
        manifest = write_manifest(logger, summary, options.manifest_path)
        logger.log("RESULT", f"Schema rejected (manifest: {manifest})", level="ERROR")
        raise SystemExit(1)

    if result.warnings and not options.force:
        for warning in result.warnings:
            logger.log("WARN", warning, level="WARN")
        summary = {
            "status": "needs_attention",
            "errors": result.errors,
            "warnings": result.warnings,
            "dry_run": options.dry_run,
        }
        manifest = write_manifest(logger, summary, options.manifest_path)
        logger.log("RESULT", "Warnings present – rerun with --force to proceed", level="WARN")
        raise SystemExit(1)

    output_path = paths.schemas() / f"{options.name}.schema.json"
    if output_path.exists() and not options.force:
        logger.log("ERROR", f"Schema {output_path.name} already exists; use --force to overwrite", level="ERROR")
        summary = {
            "status": "failed",
            "errors": ["schema_exists"],
            "warnings": result.warnings,
            "dry_run": options.dry_run,
        }
        manifest = write_manifest(logger, summary, options.manifest_path)
        logger.log("RESULT", f"Schema not written (manifest: {manifest})", level="ERROR")
        raise SystemExit(1)

    if options.dry_run:
        logger.log("DRY_RUN", "Dry-run enabled; schema not written")
    else:
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(result.schema, handle, indent=2)
            handle.write("\n")
        logger.log("OK", f"Schema saved to {output_path}")

    summary = {
        "status": "success",
        "warnings": result.warnings,
        "errors": result.errors,
        "dry_run": options.dry_run,
        "output_path": str(output_path) if not options.dry_run else None,
    }
    manifest = write_manifest(logger, summary, options.manifest_path)
    logger.log("RESULT", f"Schema ready (manifest: {manifest})")


if __name__ == "__main__" and not os.environ.get("AMI_MARKETING_SKIP_MAIN"):  # pragma: no cover
    main()
