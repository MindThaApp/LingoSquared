#!/usr/bin/env python3

import argparse
import json
import os
import sys
from pathlib import Path

import httpx


API_URL = "https://api.openai.com/v1/audio/speech"
MODEL = "gpt-4o-mini-tts"
VOICE = "marin"

TEST_SENTENCES = (
    ("en", "Good morning."),
    ("en", "Nice to meet you."),
    ("fa", "سلام"),
    ("fa", "روز خوبی داشته باشید"),
    ("prs", "سلام علیکم"),
    ("prs", "صبح بخیر"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate sample MP3 files using OpenAI text-to-speech."
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("/tmp/openai-tts-test"),
        help="Output directory (default: /tmp/openai-tts-test)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        print(
            "Error: OPENAI_API_KEY is not set in the environment.",
            file=sys.stderr,
        )
        return 2

    try:
        args.out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(
            f"Error: could not create output directory {args.out_dir}: {exc}",
            file=sys.stderr,
        )
        return 2

    written_files: list[Path] = []
    failures = 0
    language_indexes: dict[str, int] = {}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "audio/mpeg",
        "Content-Type": "application/json; charset=utf-8",
    }

    with httpx.Client(timeout=60.0) as client:
        for language_code, text in TEST_SENTENCES:
            language_indexes[language_code] = (
                language_indexes.get(language_code, 0) + 1
            )
            index = language_indexes[language_code]
            output_path = args.out_dir / f"{language_code}_{index:02d}.mp3"

            payload = {
                "model": MODEL,
                "voice": VOICE,
                "input": text,
                "response_format": "mp3",
            }
            request_body = json.dumps(
                payload,
                ensure_ascii=False,
            ).encode("utf-8")

            print(f"Generating {output_path.name}: {text}")

            try:
                response = client.post(
                    API_URL,
                    headers=headers,
                    content=request_body,
                )
            except httpx.HTTPError as exc:
                failures += 1
                print(
                    f"Error requesting {output_path.name}: {exc}",
                    file=sys.stderr,
                )
                continue

            if response.status_code != 200:
                failures += 1
                print(
                    (
                        f"Error generating {output_path.name}: "
                        f"HTTP {response.status_code}"
                    ),
                    file=sys.stderr,
                )
                print(response.text, file=sys.stderr)
                continue

            try:
                output_path.write_bytes(response.content)
            except OSError as exc:
                failures += 1
                print(
                    f"Error writing {output_path}: {exc}",
                    file=sys.stderr,
                )
                continue

            written_files.append(output_path)

    print("\nFiles written:")
    if written_files:
        for path in written_files:
            print(f"- {path}")
    else:
        print("- none")

    if failures:
        print(f"\nCompleted with {failures} failure(s).", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
