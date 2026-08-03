"""OSS governance tests for T-9 ship gate.

Asserts the three ship artifacts (LICENSE, CONTRIBUTING.md, README.md) satisfy
the spec's eval-backed contract, de-brand, and repo-posture requirements.

Derived from:
  - S-001 (LICENSE Apache-2.0, CONTRIBUTING.md exist with correct structure)
  - S-007 (README publishes eval scorecard table)
  - Spec glossary "De-brand" (zero employer/company/product branding;
    author attributes as "Jacky Chan, AWS Community Builder")
  - Spec line 20 repo posture (jhkchan/aws-agent-skills, Apache-2.0,
    de-branded, solo-maintainer)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LICENSE = REPO_ROOT / "LICENSE"
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"
README = REPO_ROOT / "README.md"

# De-brand blocklist — these tokens MUST NOT appear in shipped content.
# (The internal reference repo / The other internal reference repo are Jacky's employers; de-brand per spec glossary.)
FORBIDDEN_BRAND_TOKENS = ("the internal reference repo", "the other internal reference repo")


def _read(path: Path) -> str:
    if not path.exists():
        pytest.fail(f"required governance file missing: {path}")
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# LICENSE
# ---------------------------------------------------------------------------


class TestLicense:
    def test_file_exists(self) -> None:
        assert LICENSE.exists(), f"{LICENSE} must exist (S-001)"

    def test_is_apache_2(self) -> None:
        text = _read(LICENSE)
        assert "Apache License" in text
        assert "Version 2.0" in text
        assert "SPDX-License-Identifier: Apache-2.0" in text

    def test_copyright_personal_not_company(self) -> None:
        text = _read(LICENSE)
        assert "Jacky Chan" in text
        for token in FORBIDDEN_BRAND_TOKENS:
            assert token.lower() not in text.lower(), (
                f"de-brand violation: LICENSE mentions '{token}'"
            )


# ---------------------------------------------------------------------------
# CONTRIBUTING.md
# ---------------------------------------------------------------------------


class TestContributing:
    def test_file_exists(self) -> None:
        assert CONTRIBUTING.exists(), f"{CONTRIBUTING} must exist (S-001)"

    def test_documents_eval_backed_contract(self) -> None:
        text = _read(CONTRIBUTING).lower()
        # Eval-backed contract is structural (spec ADR Consequences).
        assert "eval" in text
        assert "co-located" in text or "colocated" in text
        assert "assertion" in text
        assert "scorecard" in text

    def test_documents_skill_format(self) -> None:
        text = _read(CONTRIBUTING).lower()
        # Minimal skill format (aws/agent-toolkit alignment).
        assert "skill.md" in text
        for field in ("name", "description", "version"):
            assert field in text, f"CONTRIBUTING must document frontmatter: {field}"

    def test_documents_license(self) -> None:
        text = _read(CONTRIBUTING).lower()
        assert "apache-2.0" in text or "apache 2.0" in text

    def test_debrand(self) -> None:
        text = _read(CONTRIBUTING).lower()
        for token in FORBIDDEN_BRAND_TOKENS:
            assert token.lower() not in text, (
                f"de-brand violation: CONTRIBUTING mentions '{token}'"
            )


# ---------------------------------------------------------------------------
# README.md
# ---------------------------------------------------------------------------


class TestReadme:
    def test_file_exists(self) -> None:
        assert README.exists(), f"{README} must exist (S-001)"

    def test_has_scorecard_table(self) -> None:
        """S-007: README publishes eval scorecard table sourced from committed artifacts."""
        text = _read(README)
        # A GFM table row: | ... | ... |
        assert re.search(r"^\s*\|.*\|\s*$", text, re.MULTILINE), (
            "README must contain a markdown table for scorecards"
        )
        # S-007 required columns per-skill.
        lowered = text.lower()
        for col in ("skill", "model", "grade", "verdict"):
            assert col in lowered, f"README scorecard table must include column: {col}"

    def test_repo_posture(self) -> None:
        text = _read(README)
        assert "jhkchan/aws-agent-skills" in text, (
            "README must reference the repo path jhkchan/aws-agent-skills"
        )
        lowered = text.lower()
        assert "apache-2.0" in lowered or "apache 2.0" in lowered

    def test_attribution(self) -> None:
        """De-brand glossary: author = 'Jacky Chan, AWS Community Builder'."""
        text = _read(README)
        assert "Jacky Chan" in text
        assert "AWS Community Builder" in text

    def test_debrand_no_company(self) -> None:
        text = _read(README).lower()
        for token in FORBIDDEN_BRAND_TOKENS:
            assert token.lower() not in text, (
                f"de-brand violation: README mentions '{token}'"
            )
