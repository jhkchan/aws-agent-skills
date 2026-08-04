"""Phase 3 scaffold tests — schema validation, orchestrator routing, command discovery.

Verifies the Phase 3 exit criteria:
  1. schemaValidation: all seed SKILL.md frontmatter validates against
     schema/SKILL.schema.json.
  2. orchestratorRouting: the CLI route command directs test prompts to the
     correct seed skill.
  3. commandDiscovery: the CLI list command discovers all 3 seed skills +
     the orchestrator.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "SKILL.schema.json"
SKILLS_DIR = REPO_ROOT / "skills"
CLI_PATH = REPO_ROOT / "cli" / "bin" / "cli.js"

SEED_SKILLS = [
    "s3-public-access-auditor",
    "iam-least-privilege-advisor",
    "ec2-security-group-auditor",
]

ALL_SKILLS = SEED_SKILLS + ["aws-orchestrator"]


# ---------------------------------------------------------------------------
# 1. Schema validation — all seed frontmatter passes schema/SKILL.schema.json
# ---------------------------------------------------------------------------


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def _parse_frontmatter(skill_md_path: Path) -> dict:
    text = skill_md_path.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---\s*", text, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


@pytest.mark.parametrize("skill_name", ALL_SKILLS)
def test_schema_validation(skill_name: str) -> None:
    """Each skill's frontmatter must validate against schema/SKILL.schema.json."""
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load_schema()
    skill_md = SKILLS_DIR / skill_name / "SKILL.md"
    assert skill_md.exists(), f"{skill_name}/SKILL.md missing"

    frontmatter = _parse_frontmatter(skill_md)
    jsonschema.validate(frontmatter, schema)


@pytest.mark.parametrize("skill_name", SEED_SKILLS)
def test_seed_frontmatter_has_metadata_fields(skill_name: str) -> None:
    """Seed skills must have the full structured-eval pattern metadata fields."""
    skill_md = SKILLS_DIR / skill_name / "SKILL.md"
    fm = _parse_frontmatter(skill_md)
    metadata = fm.get("metadata", {})

    assert fm.get("name") == skill_name
    assert fm.get("version"), f"{skill_name} missing version"
    assert fm.get("license"), f"{skill_name} missing license"
    assert "domain" in metadata, f"{skill_name} missing metadata.domain"
    assert "phase" in metadata, f"{skill_name} missing metadata.phase"
    assert "supports_pipeline" in metadata, f"{skill_name} missing metadata.supports_pipeline"
    assert "family" in metadata, f"{skill_name} missing metadata.family"
    assert "verdict_shape" in metadata, f"{skill_name} missing metadata.verdict_shape"


def test_schema_requires_name_and_description() -> None:
    """Schema must enforce name and description as required fields."""
    schema = _load_schema()
    assert "name" in schema["required"]
    assert "description" in schema["required"]


def test_schema_description_max_length() -> None:
    """Schema must enforce 1024-char max on description."""
    schema = _load_schema()
    assert schema["properties"]["description"]["maxLength"] == 1024


# ---------------------------------------------------------------------------
# 2. Orchestrator routing — CLI route directs prompts to correct seed skill
# ---------------------------------------------------------------------------


ROUTING_CASES = [
    (
        "audit my S3 buckets for public access",
        "s3-public-access-auditor",
    ),
    (
        "check this IAM role for wildcard permissions",
        "iam-least-privilege-advisor",
    ),
    (
        "are my security groups exposed on 0.0.0.0/0",
        "ec2-security-group-auditor",
    ),
]


def _run_cli(*args: str) -> str:
    """Run the CLI and return stdout."""
    result = subprocess.run(
        ["node", str(CLI_PATH), *args],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    return result.stdout


@pytest.mark.parametrize("prompt,expected_skill", ROUTING_CASES)
def test_orchestrator_routing(prompt: str, expected_skill: str) -> None:
    """CLI route must direct the test prompt to the expected seed skill."""
    output = _run_cli("route", prompt)
    # The "Primary route:" line contains the top-scoring skill name.
    match = re.search(r"Primary route:\s*(\S+)", output)
    assert match, f"Could not parse primary route from output:\n{output}"
    routed_skill = match.group(1)
    assert routed_skill == expected_skill, (
        f"Expected '{expected_skill}' for prompt '{prompt}', got '{routed_skill}'"
    )


def test_route_emits_phase_indicator() -> None:
    """The route command must emit a [Phase: ...] indicator."""
    output = _run_cli("route", "audit my S3 buckets")
    assert re.search(r"\[Phase:\s*\w+", output), (
        f"Phase indicator missing from route output:\n{output}"
    )


# ---------------------------------------------------------------------------
# 3. Command discovery — CLI lists all skills
# ---------------------------------------------------------------------------


def test_cli_list_discovers_all_seeds() -> None:
    """CLI list must discover all 3 seed skills + the orchestrator."""
    output = _run_cli("list")
    for skill in ALL_SKILLS:
        assert skill in output, f"CLI list did not discover skill: {skill}"


def test_cli_list_shows_eval_status() -> None:
    """CLI list must show eval-backed status for seed skills."""
    output = _run_cli("list")
    for skill in SEED_SKILLS:
        # Each seed should have [eval-backed] badge.
        assert "eval-backed" in output, (
            f"Expected eval-backed badge for seed skills in list output"
        )


def test_cli_validate_passes() -> None:
    """CLI validate must exit 0 (no errors) for all current skills."""
    output = _run_cli("validate")
    assert "0 errors" in output, f"Validation errors:\n{output}"


def test_cli_status_shows_orchestrator() -> None:
    """CLI status must report the orchestrator as present."""
    output = _run_cli("status")
    assert "orchestrator" in output.lower()
    assert "present" in output.lower()


# ---------------------------------------------------------------------------
# 4. Phase 3 infrastructure presence
# ---------------------------------------------------------------------------


def test_commands_dir_has_seed_commands() -> None:
    """commands/aws/ must have a slash command for each seed skill."""
    commands_dir = REPO_ROOT / "commands" / "aws"
    assert commands_dir.is_dir(), "commands/aws/ directory missing"

    for skill in SEED_SKILLS:
        # Convention: audit-<service>.md pattern
        cmd_files = list(commands_dir.glob("*.md"))
        assert cmd_files, f"No command files in commands/aws/"

    # Verify the three per-seed command files exist
    expected_commands = [
        "audit-s3-public-access.md",
        "audit-iam-least-privilege.md",
        "audit-ec2-security-groups.md",
    ]
    for cmd in expected_commands:
        assert (commands_dir / cmd).exists(), f"Missing command file: {cmd}"


def test_pipeline_command_exists() -> None:
    """commands/aws/pipeline.md must exist."""
    assert (REPO_ROOT / "commands" / "aws" / "pipeline.md").exists()


def test_orchestrator_skill_exists() -> None:
    """skills/aws-orchestrator/SKILL.md must exist."""
    orch = SKILLS_DIR / "aws-orchestrator" / "SKILL.md"
    assert orch.exists(), "aws-orchestrator/SKILL.md missing"


def test_orchestrator_has_references() -> None:
    """aws-orchestrator must have references/ with pipeline-phases and routing-logic."""
    refs = SKILLS_DIR / "aws-orchestrator" / "references"
    assert (refs / "pipeline-phases.md").exists()
    assert (refs / "routing-logic.md").exists()


def test_shared_infra_exists() -> None:
    """_aws_shared/ must exist with shared reference docs."""
    shared = REPO_ROOT / "_aws_shared"
    assert shared.is_dir(), "_aws_shared/ directory missing"
    md_files = list(shared.glob("*.md"))
    assert len(md_files) >= 2, f"Expected >=2 shared refs, got {len(md_files)}"


def test_usage_md_exists() -> None:
    """USAGE.md must exist at repo root."""
    assert (REPO_ROOT / "USAGE.md").exists()


def test_schema_file_exists() -> None:
    """schema/SKILL.schema.json must exist."""
    assert SCHEMA_PATH.exists()


def test_cli_entry_point_exists() -> None:
    """cli/bin/cli.js must exist."""
    assert CLI_PATH.exists()


def test_package_json_exists() -> None:
    """package.json must exist."""
    assert (REPO_ROOT / "package.json").exists()
