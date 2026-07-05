#!/usr/bin/env python3
"""Aggregate recorded-audio needs across all realization files.

Phase D1 scaffolding per docs/SONNET_BUILD_PROMPT_UPGRADES.md, built by
Session 3 (INFRA). NOT a from-scratch text extractor: every realization
file already declares its own `media_assets:` block (content_key,
language, text, voice_hint, status) -- Codex has been populating this
consistently since before this script existed (confirmed across every
file in docs/content/realizations/). This script's job is purely to
aggregate those declarations project-wide, catch collisions, and
cross-reference against what's actually been recorded on disk -- it
does not invent its own key-derivation scheme.

Idempotent: rerunning after a content edit reflects only the new/changed
entries; nothing here mutates the realization YAML files.

Usage:
    python scripts/audio_manifest.py [--language fa,prs] [--status pending_generation]
                                      [--assets-dir backend/media_assets] [--format csv|json]

Exit code 1 if any duplicate content_key is found across files (a real
collision -- content_key is meant to be globally unique per the
compiler's own uniqueness invariant) or any entry has empty text.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REALIZATIONS_DIR = REPO_ROOT / "docs" / "content" / "realizations"
DEFAULT_ASSETS_DIR = REPO_ROOT / "backend" / "media_assets"


def load_media_assets(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    assets = data.get("media_assets", [])
    if not isinstance(assets, list):
        raise ValueError(f"{path}: media_assets must be a list")
    return assets


def recorded_asset_path(assets_dir: Path, content_key: str) -> Path:
    return assets_dir / f"{content_key}.mp3"


def build_manifest(
    languages: set[str] | None,
    statuses: set[str] | None,
    assets_dir: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_keys: dict[str, Path] = {}

    for path in sorted(REALIZATIONS_DIR.glob("*/*.yaml")):
        try:
            assets = load_media_assets(path)
        except (yaml.YAMLError, ValueError) as exc:
            errors.append(f"{path}: {exc}")
            continue

        for entry in assets:
            content_key = entry.get("content_key")
            text = entry.get("text")
            language = entry.get("language")

            if not content_key:
                errors.append(f"{path}: media_assets entry missing content_key: {entry}")
                continue
            if not text or not str(text).strip():
                errors.append(f"{path}: {content_key} has empty text")
                continue

            if content_key in seen_keys and seen_keys[content_key] != path:
                errors.append(
                    f"duplicate content_key '{content_key}' in {path} "
                    f"(already declared in {seen_keys[content_key]})"
                )
                continue
            seen_keys[content_key] = path

            if languages and language not in languages:
                continue
            status = entry.get("status", "pending_generation")
            if statuses and status not in statuses:
                continue

            recorded = recorded_asset_path(assets_dir, content_key).is_file()
            rows.append(
                {
                    "content_key": content_key,
                    "language": language,
                    "text": text,
                    "voice_hint": entry.get("voice_hint", ""),
                    "declared_status": status,
                    "recorded": recorded,
                    "realization_file": str(path.relative_to(REPO_ROOT)),
                }
            )

    return rows, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", help="Comma-separated language codes to include (default: all)")
    parser.add_argument("--status", help="Comma-separated declared statuses to include (default: all)")
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=DEFAULT_ASSETS_DIR,
        help=f"Directory checked for already-recorded {{content_key}}.mp3 files (default: {DEFAULT_ASSETS_DIR})",
    )
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    parser.add_argument("--missing-only", action="store_true", help="Only list entries not yet recorded")
    args = parser.parse_args()

    languages = set(args.language.split(",")) if args.language else None
    statuses = set(args.status.split(",")) if args.status else None

    rows, errors = build_manifest(languages, statuses, args.assets_dir)

    if args.missing_only:
        rows = [r for r in rows if not r["recorded"]]

    if args.format == "json":
        json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        writer = csv.DictWriter(
            sys.stdout,
            fieldnames=[
                "content_key",
                "language",
                "text",
                "voice_hint",
                "declared_status",
                "recorded",
                "realization_file",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    recorded_count = sum(1 for r in rows if r["recorded"])
    print(
        f"\n{total} entr{'y' if total == 1 else 'ies'} listed, "
        f"{recorded_count} recorded, {total - recorded_count} missing "
        f"(assets dir: {args.assets_dir})",
        file=sys.stderr,
    )

    if errors:
        print(f"\n{len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
