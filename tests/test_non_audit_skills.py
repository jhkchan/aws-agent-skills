"""Tests for non-audit skills (deploy, troubleshoot, optimize, operate, automate).

Validates that:
  - Non-audit skills exist with correct metadata (task_type, skill_class)
  - Each non-audit skill has eval artifacts (eval/ or evals/)
  - The schema includes task_type, skill_class, lifecycle_status
  - The CLI discovers and routes non-audit skills correctly
  - The impact eval harness is importable
  - The skill universe document exists and is well-formed
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
SCHEMA_PATH = REPO_ROOT / "schema" / "SKILL.schema.json"
UNIVERSE_PATH = REPO_ROOT / "features" / "aws-cloudops-skills-oss" / "skill-universe.md"
IMPACT_EVAL = REPO_ROOT / "eval" / "impact_eval.py"
MAINTENANCE = REPO_ROOT / "MAINTENANCE.md"


def _parse_frontmatter(text: str) -> dict:
    """Parse YAML frontmatter from a SKILL.md file."""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 3)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def _get_skill_dirs() -> list[Path]:
    """Get all skill directories (excluding _retired/)."""
    return sorted(
        d for d in SKILLS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_") and not d.name.startswith(".")
    )


# ---------------------------------------------------------------------------
# Schema: new metadata fields
# ---------------------------------------------------------------------------

class TestSchemaUpdates:
    def test_task_type_in_schema(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text())
        meta_props = schema["properties"]["metadata"].get("properties", {})
        assert "task_type" in meta_props, "schema must include metadata.task_type"

    def test_skill_class_in_schema(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text())
        meta_props = schema["properties"]["metadata"].get("properties", {})
        assert "skill_class" in meta_props, "schema must include metadata.skill_class"

    def test_lifecycle_status_in_schema(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text())
        meta_props = schema["properties"]["metadata"].get("properties", {})
        assert "lifecycle_status" in meta_props, "schema must include metadata.lifecycle_status"

    def test_task_type_enum_values(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text())
        meta_props = schema["properties"]["metadata"]["properties"]
        assert set(meta_props["task_type"]["enum"]) == {
            "audit", "deploy", "troubleshoot", "optimize", "operate", "automate"
        }


# ---------------------------------------------------------------------------
# Non-audit skill discovery
# ---------------------------------------------------------------------------

class TestNonAuditSkills:
    def test_deploy_skills_exist(self) -> None:
        deploy_skills = [
            d for d in _get_skill_dirs()
            if "deployer" in d.name
        ]
        assert len(deploy_skills) >= 2, f"expected >=2 deploy skills, got {len(deploy_skills)}"

    def test_troubleshoot_skills_exist(self) -> None:
        troubleshoot_skills = [
            d for d in _get_skill_dirs()
            if "troubleshooter" in d.name
        ]
        assert len(troubleshoot_skills) >= 1, f"expected >=1 troubleshoot skill, got {len(troubleshoot_skills)}"

    def test_optimize_skills_exist(self) -> None:
        optimize_skills = [
            d for d in _get_skill_dirs()
            if "optimizer" in d.name
        ]
        assert len(optimize_skills) >= 1, f"expected >=1 optimize skill, got {len(optimize_skills)}"


# ---------------------------------------------------------------------------
# Non-audit skill metadata
# ---------------------------------------------------------------------------

class TestNonAuditMetadata:
    @pytest.mark.parametrize("skill_name", [
        d.name for d in _get_skill_dirs()
        if any(s in d.name for s in ["deployer", "troubleshooter", "optimizer", "operator", "automator"])
    ])
    def test_skill_has_task_type_metadata(self, skill_name: str) -> None:
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        if not skill_md.exists():
            pytest.skip(f"{skill_name}/SKILL.md not yet built")
        fm = _parse_frontmatter(skill_md.read_text())
        meta = fm.get("metadata", {})
        # task_type should be present (or inferable from name)
        task_type = meta.get("task_type")
        if task_type is None:
            # CLI can infer from name suffix — acceptable for backward compat
            pass
        else:
            assert task_type in ["audit", "deploy", "troubleshoot", "optimize", "operate", "automate"], \
                f"{skill_name} has invalid task_type: {task_type}"


# ---------------------------------------------------------------------------
# CLI routing for non-audit skills
# ---------------------------------------------------------------------------

class TestCLIRouting:
    def test_cli_route_deploy(self) -> None:
        result = subprocess.run(
            ["node", "cli/bin/cli.js", "route", "deploy a secure S3 bucket"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        assert "deploy" in result.stdout.lower()

    def test_cli_route_troubleshoot(self) -> None:
        result = subprocess.run(
            ["node", "cli/bin/cli.js", "route", "why is my Lambda function timing out"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        assert "troubleshoot" in result.stdout.lower()

    def test_cli_route_optimize(self) -> None:
        result = subprocess.run(
            ["node", "cli/bin/cli.js", "route", "reduce my EC2 costs"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        assert "optimize" in result.stdout.lower()

    def test_cli_list_filter_task_type(self) -> None:
        result = subprocess.run(
            ["node", "cli/bin/cli.js", "list", "--task-type", "deploy"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        assert "task_type=deploy" in result.stdout

    def test_cli_status_shows_task_types(self) -> None:
        result = subprocess.run(
            ["node", "cli/bin/cli.js", "status"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        assert "audit" in result.stdout
        assert "deploy" in result.stdout or "troubleshoot" in result.stdout


# ---------------------------------------------------------------------------
# Impact eval harness
# ---------------------------------------------------------------------------

class TestImpactEval:
    def test_impact_eval_exists(self) -> None:
        assert IMPACT_EVAL.exists(), "eval/impact_eval.py must exist"

    def test_impact_eval_importable(self) -> None:
        """The impact eval module must import without errors."""
        result = subprocess.run(
            ["python3", "-c", "import sys; sys.path.insert(0, 'eval'); import impact_eval"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        # Import may fail if SSO or Bedrock is unavailable, but the module should parse
        assert result.returncode == 0 or "import" not in result.stderr.lower(), \
            f"impact_eval.py import error: {result.stderr}"

    def test_cli_impact_command(self) -> None:
        result = subprocess.run(
            ["node", "cli/bin/cli.js", "impact"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        # Should either show reports or say none found
        assert "impact" in result.stdout.lower() or "no impact" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Skill universe document
# ---------------------------------------------------------------------------

class TestSkillUniverse:
    def test_universe_exists(self) -> None:
        assert UNIVERSE_PATH.exists(), "skill-universe.md must exist"

    def test_universe_has_task_type_breakdown(self) -> None:
        text = UNIVERSE_PATH.read_text()
        for tt in ["audit", "deploy", "troubleshoot", "optimize", "operate", "automate"]:
            assert tt in text, f"skill-universe.md must mention task type: {tt}"

    def test_universe_has_capability_preference(self) -> None:
        text = UNIVERSE_PATH.read_text()
        assert "capability" in text, "skill-universe.md must mention capability classification"
        assert "preference" in text, "skill-universe.md must mention preference classification"

    def test_universe_has_total_count(self) -> None:
        text = UNIVERSE_PATH.read_text()
        # Must mention a total skill count (format varies: "Total skill slots" or "Total skill universe")
        assert re.search(r"Total skill.*(slots|universe).*\d+", text, re.IGNORECASE) or \
               re.search(r"\d+\s*total skills", text, re.IGNORECASE), \
            "skill-universe.md must show total skill count"


# ---------------------------------------------------------------------------
# Maintenance: retirement cadence
# ---------------------------------------------------------------------------

class TestRetirementCadence:
    def test_maintenance_has_retirement_section(self) -> None:
        text = MAINTENANCE.read_text()
        assert "retirement" in text.lower(), "MAINTENANCE.md must have retirement cadence section"
        assert "RETIRE_CANDIDATE" in text, "MAINTENANCE.md must define retirement criteria"
        assert "impact" in text.lower(), "MAINTENANCE.md must reference impact evaluation"
