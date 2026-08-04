"""TDD tests for T-4: IAM least-privilege advisor + EC2 security-group auditor.

Validates spec scenarios:
  S-002 — each seed skill ships with SKILL.md (frontmatter),
          references/ (supplementary docs), eval/test-cases.yaml
          (5 test cases with expected verdicts).
  S-E04 — a skill directory missing eval/ is flagged as incomplete.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from eval.skill_validator import discover_skills, validate_skill_dir

SKILLS_DIR = pathlib.Path(__file__).resolve().parent.parent / "skills"

SEED_SKILLS = [
    "iam-least-privilege-advisor",
    "ec2-security-group-auditor",
    "s3-public-access-auditor",
]


# -- S-002: skill directory structure ----------------------------------------


@pytest.mark.parametrize("skill_name", SEED_SKILLS)
def test_skill_has_skill_md_with_frontmatter(skill_name: str) -> None:
    """SKILL.md exists and has name/description/version frontmatter (S-002)."""
    skill_md = SKILLS_DIR / skill_name / "SKILL.md"
    assert skill_md.exists(), f"{skill_name}/SKILL.md is missing"

    frontmatter = _parse_frontmatter(skill_md.read_text())
    assert frontmatter.get("name") == skill_name
    assert "description" in frontmatter
    assert "version" in frontmatter


@pytest.mark.parametrize("skill_name", SEED_SKILLS)
def test_skill_has_references_dir(skill_name: str) -> None:
    """references/ directory exists with at least one supplementary doc (S-002)."""
    refs_dir = SKILLS_DIR / skill_name / "references"
    assert refs_dir.is_dir(), f"{skill_name}/references/ is missing"
    ref_files = list(refs_dir.glob("*.md"))
    assert len(ref_files) >= 1, f"{skill_name}/references/ has no .md files"


@pytest.mark.parametrize("skill_name", SEED_SKILLS)
def test_skill_has_eval_test_cases(skill_name: str) -> None:
    """eval/test-cases.yaml exists with 5 test cases and expected verdicts (S-002)."""
    eval_yaml = SKILLS_DIR / skill_name / "eval" / "test-cases.yaml"
    assert eval_yaml.exists(), f"{skill_name}/eval/test-cases.yaml is missing"

    data = yaml.safe_load(eval_yaml.read_text())
    assert data["skill"] == skill_name
    assert data["model_id"] == "amazon.nova-pro-v1:0"

    cases = data["test_cases"]
    assert len(cases) == 5, f"expected 5 test cases, got {len(cases)}"

    for tc in cases:
        assert "id" in tc, "test case missing id"
        assert "input" in tc, f"test case {tc.get('id')} missing input"
        assert "expected_verdict" in tc, f"test case {tc.get('id')} missing expected_verdict"
        assert "assertions" in tc, f"test case {tc.get('id')} missing assertions"
        assert "must_contain" in tc["assertions"]
        assert "must_not_contain" in tc["assertions"]


# -- S-002: verdict diversity ------------------------------------------------


def test_iam_eval_has_verdict_diversity() -> None:
    """IAM eval covers OVERPERMISSIVE, LEAST_PRIVILEGE, and AMBIGUOUS verdicts."""
    eval_yaml = SKILLS_DIR / "iam-least-privilege-advisor" / "eval" / "test-cases.yaml"
    data = yaml.safe_load(eval_yaml.read_text())
    verdicts = {tc["expected_verdict"] for tc in data["test_cases"]}
    assert verdicts == {"OVERPERMISSIVE", "LEAST_PRIVILEGE", "AMBIGUOUS"}


def test_ec2_eval_has_verdict_diversity() -> None:
    """EC2 eval covers OPEN, PUBLIC_NONCRITICAL, and RESTRICTED verdicts."""
    eval_yaml = SKILLS_DIR / "ec2-security-group-auditor" / "eval" / "test-cases.yaml"
    data = yaml.safe_load(eval_yaml.read_text())
    verdicts = {tc["expected_verdict"] for tc in data["test_cases"]}
    assert verdicts == {"OPEN", "PUBLIC_NONCRITICAL", "RESTRICTED"}


def test_s3_eval_has_verdict_diversity() -> None:
    """S3 eval covers SAFE, PUBLIC, and AMBIGUOUS verdicts (S-003/S-004)."""
    eval_yaml = SKILLS_DIR / "s3-public-access-auditor" / "eval" / "test-cases.yaml"
    data = yaml.safe_load(eval_yaml.read_text())
    verdicts = {tc["expected_verdict"] for tc in data["test_cases"]}
    assert verdicts == {"SAFE", "PUBLIC", "AMBIGUOUS"}


# -- S-E04: skill without eval/ is flagged -----------------------------------


def test_skill_without_eval_is_flagged(tmp_path: str) -> None:
    """A skill directory missing eval/ is flagged as incomplete (S-E04)."""
    skills_root = pathlib.Path(tmp_path) / "skills"
    skill_dir = skills_root / "bare-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: bare-skill\n---\n# Bare\n")

    warnings = validate_skill_dir(skill_dir)
    assert len(warnings) == 1
    assert "eval" in warnings[0].lower()
    assert "bare-skill" in warnings[0]


def test_skill_with_eval_is_not_flagged(tmp_path: str) -> None:
    """A skill directory with eval/ passes validation (S-E04 negative case)."""
    skills_root = pathlib.Path(tmp_path) / "skills"
    skill_dir = skills_root / "good-skill"
    eval_dir = skill_dir / "eval"
    eval_dir.mkdir(parents=True)
    (eval_dir / "test-cases.yaml").write_text("skill: good-skill\ntest_cases: []\n")

    warnings = validate_skill_dir(skill_dir)
    assert len(warnings) == 0


def test_discover_skills_flags_missing_eval(tmp_path: str) -> None:
    """discover_skills emits a warning for a skill missing eval/ (S-E04)."""
    skills_root = pathlib.Path(tmp_path) / "skills"

    # Good skill with eval/
    good = skills_root / "good-skill"
    (good / "eval").mkdir(parents=True)
    (good / "eval" / "test-cases.yaml").write_text("skill: good-skill\ntest_cases: []\n")
    (good / "SKILL.md").write_text("---\nname: good-skill\n---\n# Good\n")

    # Bad skill without eval/
    bad = skills_root / "bad-skill"
    bad.mkdir(parents=True)
    (bad / "SKILL.md").write_text("---\nname: bad-skill\n---\n# Bad\n")

    warnings = discover_skills(skills_root)
    assert len(warnings) == 1
    assert "bad-skill" in warnings[0]


def test_real_seed_skills_have_no_warnings() -> None:
    """The actual seed skill directories pass discovery without warnings."""
    warnings = discover_skills(SKILLS_DIR)
    for skill_name in SEED_SKILLS:
        assert not any(skill_name in w for w in warnings), (
            f"unexpected warning for {skill_name}: {warnings}"
        )


# -- helpers -----------------------------------------------------------------


def _parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}
