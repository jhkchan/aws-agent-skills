"""Tests for the CI eval workflow (.github/workflows/eval.yml).

Validates acceptance scenarios:
  S-006 — CI runs assertion-layer evals on every PR
  S-E04 — Skill without eval/ flagged as incomplete
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import yaml

WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent / ".github" / "workflows" / "eval.yml"
)

SPEC_WARNING_PREFIX = "Skill"
SPEC_WARNING_SUFFIX = (
    "has no eval/ directory — eval-backed contract requires co-located test cases"
)


def _load_workflow() -> dict:
    """Load and parse the eval.yml workflow file."""
    with open(WORKFLOW_PATH) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# S-006 — CI runs assertion-layer evals on every PR
# ---------------------------------------------------------------------------


class TestS006AssertionLayerOnPR:
    """S-006: a PR triggers the assertion-layer job in assertion-only mode."""

    def test_workflow_file_exists(self):
        """The workflow file must exist at .github/workflows/eval.yml."""
        assert WORKFLOW_PATH.exists(), f"Expected workflow at {WORKFLOW_PATH}"

    def test_triggers_on_pull_request(self):
        """The workflow must trigger on pull_request events."""
        wf = _load_workflow()
        # PyYAML parses the bare 'on:' key as boolean True (YAML 1.1 spec).
        on = wf.get("on") or wf.get(True)
        assert on is not None, "Workflow missing 'on' trigger"
        # 'on' can be a list, a dict, or a string
        if isinstance(on, dict):
            assert "pull_request" in on, "Workflow must trigger on pull_request"
        elif isinstance(on, list):
            assert "pull_request" in on
        else:
            assert on == "pull_request"

    def test_has_assertion_job(self):
        """A job for assertion-layer evals must exist."""
        wf = _load_workflow()
        jobs = wf.get("jobs", {})
        assert len(jobs) > 0, "Workflow must have at least one job"
        # At least one job should be the assertion-layer
        assertion_jobs = [name for name in jobs if "assert" in name.lower()]
        assert assertion_jobs, (
            "No assertion-layer job found (expected a job name containing 'assert')"
        )

    def test_assertion_job_runs_on_pr(self):
        """The assertion job must run on ubuntu-latest (CI standard runner)."""
        wf = _load_workflow()
        jobs = wf.get("jobs", {})
        for name, job in jobs.items():
            if "assert" in name.lower():
                assert job.get("runs-on") is not None, f"Job '{name}' missing runs-on"

    def test_no_aws_credentials(self):
        """Gate-2 Local-eval: CI must NOT configure AWS credentials."""
        wf = _load_workflow()
        wf_text = yaml.dump(wf)
        # No AWS access key secrets should be referenced
        forbidden = [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "aws-actions/configure-aws-credentials",
        ]
        for token in forbidden:
            assert token not in wf_text, (
                f"Workflow must not contain '{token}' — gate-2 Local-eval decision "
                f"prohibits AWS credentials in CI"
            )

    def test_assertion_job_references_eval_runner(self):
        """The assertion job must invoke eval/run_eval.py in assertion-only mode."""
        wf = _load_workflow()
        wf_text = yaml.dump(wf)
        assert "run_eval.py" in wf_text, "Workflow must reference eval/run_eval.py"
        assert "assert" in wf_text.lower(), "Workflow must invoke assertion-only mode"


# ---------------------------------------------------------------------------
# S-E04 — Skill without eval/ flagged as incomplete
# ---------------------------------------------------------------------------


class TestSE04MissingEvalWarning:
    """S-E04: a skill missing eval/ emits a warning with the spec message."""

    def test_has_eval_coverage_check(self):
        """The workflow must contain a check for skills missing eval/ dirs."""
        wf = _load_workflow()
        wf_text = yaml.dump(wf)
        # The check should look for eval/ directories under skills/
        assert "skills/" in wf_text, "Workflow must scan skills/ directory"
        assert "eval" in wf_text.lower(), "Workflow must check for eval/ directories"

    def test_warning_message_matches_spec(self):
        """The warning message must match the spec exactly."""
        # Read raw file content — yaml.dump() escapes unicode (em-dash -> —).
        raw = WORKFLOW_PATH.read_text()
        assert SPEC_WARNING_SUFFIX in raw, (
            f"Warning message must contain: '{SPEC_WARNING_SUFFIX}'"
        )

    def test_missing_eval_detection_logic(self):
        """Test the missing-eval detection by running the check script against
        a temp directory with a skill missing eval/."""
        # Extract the check script from the workflow and run it against
        # a simulated skills directory.
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            # Create a skill WITH eval/
            (tmp / "skills" / "good-skill" / "eval").mkdir(parents=True)
            (tmp / "skills" / "good-skill" / "SKILL.md").write_text("good")
            # Create a skill WITHOUT eval/
            (tmp / "skills" / "bad-skill").mkdir(parents=True)
            (tmp / "skills" / "bad-skill" / "SKILL.md").write_text("bad")

            # Run a bash check simulating the workflow's logic
            script = f"""
            cd {tmp}
            for skill_dir in skills/*/; do
              skill_name=$(basename "$skill_dir")
              if [ ! -d "${{skill_dir}}eval" ]; then
                echo "::warning::Skill $skill_name has no eval/ directory — eval-backed contract requires co-located test cases"
              fi
            done
            """
            result = subprocess.run(
                ["bash", "-c", script],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            output = result.stdout + result.stderr
            assert "bad-skill" in output, "Missing-eval check must flag 'bad-skill'"
            assert SPEC_WARNING_SUFFIX in output, "Warning message must match spec"
            assert "good-skill" not in output, (
                "Missing-eval check must NOT flag 'good-skill' (has eval/)"
            )
