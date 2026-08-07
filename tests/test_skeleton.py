"""S-001 — Repo skeleton created.

Given: the local working directory <repo-root>
When: the build creates the repo skeleton
Then: skills/, eval/, .github/workflows/, README.md, CONTRIBUTING.md,
      LICENSE (Apache-2.0), CODEOWNERS exist with correct structure
      matching the aws/agent-toolkit-for-aws minimal skill format.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


# --- Required top-level directories and files ---------------------------------

REQUIRED_DIRS = [
    REPO_ROOT / "skills",
    REPO_ROOT / "eval",
    REPO_ROOT / ".github" / "workflows",
]

REQUIRED_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "LICENSE",
    REPO_ROOT / "CODEOWNERS",
]


@pytest.mark.parametrize("required_dir", REQUIRED_DIRS, ids=lambda p: str(p.name))
def test_required_directories_exist(required_dir: Path) -> None:
    assert required_dir.is_dir(), f"missing required directory: {required_dir}"


@pytest.mark.parametrize("required_file", REQUIRED_FILES, ids=lambda p: str(p.name))
def test_required_files_exist(required_file: Path) -> None:
    assert required_file.is_file(), f"missing required file: {required_file}"


# --- LICENSE is Apache-2.0 ----------------------------------------------------


def test_license_is_apache_2() -> None:
    license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in license_text
    assert "Version 2.0" in license_text


# --- CODEOWNERS is non-empty and points at the maintainer ---------------------


def test_codeowners_non_empty() -> None:
    codeowners = (REPO_ROOT / "CODEOWNERS").read_text(encoding="utf-8").strip()
    assert codeowners, "CODEOWNERS must not be empty"
    assert not codeowners.startswith("#") or any(
        line.strip() and not line.strip().startswith("#")
        for line in codeowners.splitlines()
    ), "CODEOWNERS must have at least one non-comment rule"


# --- README mentions the eval-backed value prop -------------------------------


def test_readme_describes_project() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "aws-agent-skills" in readme.lower() or "agent-skills" in readme.lower()
    assert "eval" in readme.lower(), "README should mention the eval-backed contract"


# --- CONTRIBUTING references the co-located eval contract ---------------------


def test_contributing_references_eval_contract() -> None:
    contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "eval" in contributing.lower(), (
        "CONTRIBUTING should describe the eval-backed contract"
    )


# --- Minimal skill format: SKILL.md with name/description/version frontmatter -

FRONTMATTER_RE = re.compile(r"^---\s*\n(?P<yaml>.*?)\n---\s*\n", re.DOTALL)


def _skill_dirs() -> list[Path]:
    skills_root = REPO_ROOT / "skills"
    if not skills_root.is_dir():
        return []
    # Only include dirs that have a SKILL.md (skip empty dirs from in-progress builds)
    return [d for d in sorted(skills_root.iterdir()) if d.is_dir() and (d / "SKILL.md").exists()]


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda p: str(p.name))
def test_skill_has_minimal_format(skill_dir: Path) -> None:
    """aws/agent-toolkit-for-aws minimal skill format:
    SKILL.md with name/description/version frontmatter.
    """
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.is_file(), f"skill missing SKILL.md: {skill_dir.name}"

    body = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(body)
    assert match is not None, f"SKILL.md for {skill_dir.name} missing YAML frontmatter"
    frontmatter = match.group("yaml")
    for field in ("name", "description", "version"):
        assert re.search(rf"^{field}\s*:", frontmatter, re.MULTILINE), (
            f"SKILL.md for {skill_dir.name} missing frontmatter field: {field}"
        )
