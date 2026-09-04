#!/usr/bin/env python3
"""Generate the README scorecard table from committed eval scorecard JSON.

Discovers ``eval/scorecards/*.json``, parses each scorecard artifact, and
emits a markdown table into ``SKILLS.md`` between sentinel markers so the
table is always sourced from committed artifacts — never hand-typed.

Usage::

    python eval/generate_readme_table.py           # update README in-place
    python eval/generate_readme_table.py --stdout  # print table to stdout
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCORECARDS_DIR = REPO_ROOT / "eval" / "scorecards"
DEFAULT_README = REPO_ROOT / "SKILLS.md"

BEGIN_MARKER = "<!-- BEGIN EVAL SCORECARD TABLE -->"
END_MARKER = "<!-- END EVAL SCORECARD TABLE -->"

TABLE_HEADERS = ("Skill", "Model", "Score", "Grade", "Verdicts", "Latency", "Tokens")


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_scorecards(scorecards_dir: Path) -> list[dict]:
    """Load all ``*.json`` scorecard files, sorted by skill name.

    Returns an empty list if the directory does not exist or contains no
    JSON files.
    """
    if not scorecards_dir.is_dir():
        return []
    cards: list[dict] = []
    for f in sorted(scorecards_dir.glob("*.json")):
        cards.append(json.loads(f.read_text()))
    cards.sort(key=lambda c: c.get("skill", ""))
    return cards


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def _format_latency(ms: object) -> str:
    if ms is None:
        return "---"
    return f"{float(ms) / 1000:.1f}s"


def _format_score(card: dict) -> str:
    total = card.get("total_score", 0)
    maximum = card.get("max_score", 120)
    return f"{total}/{maximum}"


def _format_verdicts(card: dict) -> str:
    correct = card.get("assertions_passed_count", 0)
    total = correct + card.get("assertions_failed_count", 0)
    return f"{correct}/{total}"


# --------------------------------------------------------------------------- #
# Table generation
# --------------------------------------------------------------------------- #
def generate_table(scorecards_dir: Path) -> str:
    """Produce the markdown scorecard table from committed JSON artifacts."""
    cards = load_scorecards(scorecards_dir)
    lines = [
        "| " + " | ".join(TABLE_HEADERS) + " |",
        "|" + "|".join("---" for _ in TABLE_HEADERS) + "|",
    ]
    for c in cards:
        row = (
            str(c.get("skill", "---")),
            str(c.get("model_id", "---")),
            _format_score(c),
            str(c.get("grade", "---")),
            _format_verdicts(c),
            _format_latency(c.get("latency_ms")),
            str(c.get("token_count", "---")),
        )
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# README update
# --------------------------------------------------------------------------- #
def update_readme(readme_path: Path, scorecards_dir: Path) -> None:
    """Replace (or append) the scorecard table block in *readme_path*."""
    table = generate_table(scorecards_dir)
    block = f"{BEGIN_MARKER}\n{table}\n{END_MARKER}"
    content = readme_path.read_text()

    if BEGIN_MARKER in content and END_MARKER in content:
        before = content[: content.index(BEGIN_MARKER)]
        after = content[content.index(END_MARKER) + len(END_MARKER) :]
        readme_path.write_text(before + block + after)
    else:
        readme_path.write_text(content.rstrip() + "\n\n" + block + "\n")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scorecards-dir",
        type=Path,
        default=DEFAULT_SCORECARDS_DIR,
        help="Directory containing committed scorecard JSON (default: eval/scorecards)",
    )
    parser.add_argument(
        "--readme",
        type=Path,
        default=DEFAULT_README,
        help="Path to README.md (default: repo root README.md)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the table to stdout instead of updating README.md",
    )
    args = parser.parse_args(argv)

    if args.stdout:
        print(generate_table(args.scorecards_dir))
    else:
        update_readme(args.readme, args.scorecards_dir)
        print(f"Updated {args.readme}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
