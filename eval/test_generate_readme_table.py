"""Tests for README scorecard table generation (S-007).

Verifies that the README score table is auto-generated from committed
scorecard JSON artifacts — not hand-typed — showing per-skill: model,
total score, grade, verdicts correct, latency, and tokens.
"""

from __future__ import annotations

import json
from pathlib import Path

from generate_readme_table import (
    BEGIN_MARKER,
    END_MARKER,
    generate_table,
    update_readme,
)


def _make_scorecard(skill: str, **overrides: object) -> dict:
    """Build a minimal valid scorecard dict matching the spec S-005 schema."""
    card: dict = {
        "skill": skill,
        "model_id": "amazon.nova-pro-v1:0",
        "total_score": 99,
        "max_score": 120,
        "grade": "A",
        "verdicts_correct": 5,
        "verdicts_total": 5,
        "token_count": 1234,
        "latency_ms": 5678,
        "dimensions": [],
    }
    card.update(overrides)
    return card


def _write_scorecards(tmp_path: Path, cards: list[dict]) -> Path:
    """Write scorecard JSON files into a temp scorecards dir and return it."""
    d = tmp_path / "scorecards"
    d.mkdir()
    for c in cards:
        (d / f"{c['skill']}.json").write_text(json.dumps(c))
    return d


# --------------------------------------------------------------------------- #
# S-007: table contains all required columns
# --------------------------------------------------------------------------- #
def test_table_contains_all_required_columns(tmp_path: Path) -> None:
    """Score, Grade, Verdicts, Latency, Tokens, Model columns must all appear."""
    d = _write_scorecards(tmp_path, [_make_scorecard("s3-public-access-auditor")])
    table = generate_table(d)
    for header in ("Skill", "Model", "Score", "Grade", "Verdicts", "Latency", "Tokens"):
        assert header in table, f"Missing required column header: {header}"


# --------------------------------------------------------------------------- #
# S-007: values sourced from JSON artifacts, not hardcoded
# --------------------------------------------------------------------------- #
def test_table_values_come_from_json_artifacts(tmp_path: Path) -> None:
    """Changing JSON values must change the table output."""
    card = _make_scorecard(
        "iam-least-privilege-advisor",
        total_score=85,
        grade="B",
        model_id="openai.gpt-oss-20b-1:0",
        verdicts_correct=4,
        verdicts_total=5,
        token_count=999,
        latency_ms=3200,
    )
    d = _write_scorecards(tmp_path, [card])
    table = generate_table(d)
    assert "85/120" in table
    assert "openai.gpt-oss-20b-1:0" in table
    assert "4/5" in table
    assert "3.2s" in table
    assert "999" in table
    # Must NOT contain values from a different skill
    assert "99/120" not in table


# --------------------------------------------------------------------------- #
# S-007: multiple skills produce one row each, sorted by name
# --------------------------------------------------------------------------- #
def test_table_multiple_skills_sorted(tmp_path: Path) -> None:
    cards = [
        _make_scorecard("ec2-security-group-auditor", total_score=72, grade="B"),
        _make_scorecard("s3-public-access-auditor", total_score=99, grade="A"),
        _make_scorecard("iam-least-privilege-advisor", total_score=85, grade="B"),
    ]
    d = _write_scorecards(tmp_path, cards)
    table = generate_table(d)
    lines = table.strip().split("\n")
    # header + separator + 3 data rows
    assert len(lines) == 5
    assert "ec2-security-group-auditor" in lines[2]
    assert "iam-least-privilege-advisor" in lines[3]
    assert "s3-public-access-auditor" in lines[4]


# --------------------------------------------------------------------------- #
# S-007: graceful when no scorecards committed yet
# --------------------------------------------------------------------------- #
def test_table_empty_dir_produces_header_only(tmp_path: Path) -> None:
    d = tmp_path / "empty"
    d.mkdir()
    table = generate_table(d)
    lines = table.strip().split("\n")
    assert len(lines) == 2  # header + separator only


def test_table_missing_dir_produces_header_only(tmp_path: Path) -> None:
    d = tmp_path / "does_not_exist"
    table = generate_table(d)
    lines = table.strip().split("\n")
    assert len(lines) == 2


# --------------------------------------------------------------------------- #
# S-007: README updated in-place between markers
# --------------------------------------------------------------------------- #
def test_update_readme_replaces_between_markers(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Title\n\nIntro text.\n\n"
        f"{BEGIN_MARKER}\nOld stale table.\n{END_MARKER}\n\nFooter.\n"
    )
    d = _write_scorecards(tmp_path, [_make_scorecard("s3-public-access-auditor")])
    update_readme(readme, d)
    content = readme.read_text()
    assert "Old stale table." not in content
    assert "s3-public-access-auditor" in content
    assert "Intro text." in content
    assert "Footer." in content


def test_update_readme_appends_when_no_markers(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Title\n\nIntro.\n")
    d = _write_scorecards(tmp_path, [_make_scorecard("s3-public-access-auditor")])
    update_readme(readme, d)
    content = readme.read_text()
    assert BEGIN_MARKER in content
    assert "s3-public-access-auditor" in content
    assert "Intro." in content
