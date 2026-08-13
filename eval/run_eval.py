#!/usr/bin/env python3
"""Eval runner for eval-backed AWS CloudOps agent skills.

Discovers skills/*/eval/*.yaml, invokes the target model via Bedrock converse,
runs the assertion layer (must_contain / must_not_contain), pipes model output +
skill definition to the LLM judge (8-dimension / 120-point rubric), and emits a
structured JSON scorecard.

Usage:
    python3 eval/run_eval.py [--assertion-only] [--skill <name>] [--profile default]

Satisfies: S-003, S-004, S-005, S-E02, S-E01, S-E03, S-N01.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = REPO_ROOT / "eval"
JUDGE_PROMPT_FILE = EVAL_DIR / "judge_prompt.txt"
SKILLS_GLOB = "skills/*/eval/*.yaml"

# Grade band thresholds on a 0-120 scale.
GRADE_BANDS: list[tuple[str, int]] = [
    ("A", 108),  # >= 90 %
    ("B", 84),  # >= 70 %  -- eval-backed floor
    ("C", 60),  # >= 50 %
    ("D", 36),  # >= 30 %
    ("F", 0),
]


# ---------------------------------------------------------------------------
# T-8: Error handling constants (S-E01, S-E03, S-N01)
# ---------------------------------------------------------------------------

MAX_SCORE = 120

# SSO expiration patterns (S-E01).
SSO_ERROR_PATTERNS = [
    "ExpiredTokenException",
    "ExpiredToken",
    "Token has expired",
    "SSO session",
    "InvalidGrantException",
]

# Geo-block patterns (S-E03) — only checked for anthropic.* models.
GEOBLOCK_ERROR_PATTERNS = [
    "ValidationException",
    "Model is not available",
    "model is not supported",
]

GEOBLOCK_JUSTIFICATION = (
    "Model invocation geo-blocked: ValidationException. "
    "Block is account-level, not region-level."
)


class SSOSessionExpiredError(Exception):
    """Raised when the AWS SSO session has expired (S-E01)."""


class GeoBlockError(Exception):
    """Raised when a model is geo-blocked — account-level ValidationException (S-E03)."""

    def __init__(self, model_id: str, raw_error: str) -> None:
        self.model_id = model_id
        self.raw_error = raw_error
        super().__init__(f"Geo-blocked: {model_id}")


# ---------------------------------------------------------------------------
# Assertion layer (S-004, S-E02)
# ---------------------------------------------------------------------------


@dataclass
class AssertionFailure:
    """A single failed assertion check."""

    test_case_id: str
    check_type: str  # "must_contain" | "must_not_contain"
    token: str
    message: str


@dataclass
class AssertionResult:
    """Result of running assertions for one test case."""

    test_case_id: str
    passed: bool
    failures: list[AssertionFailure] = field(default_factory=list)


def run_assertions(model_output: str, test_case: dict) -> AssertionResult:
    """Run must_contain / must_not_contain keyword checks against model output.

    S-004: validates structural correctness — expected verdicts, entity names,
    and output fields present; forbidden tokens absent.

    S-E02: a missing field produces a specific message naming the missing field
    and the test case, not a generic "eval failed".
    """
    test_case_id = test_case.get("id", "<unknown>")
    assertions = test_case.get("assertions", {})
    must_contain: list[str] = assertions.get("must_contain", [])
    must_not_contain: list[str] = assertions.get("must_not_contain", [])

    failures: list[AssertionFailure] = []

    for token in must_contain:
        if token not in model_output:
            failures.append(
                AssertionFailure(
                    test_case_id=test_case_id,
                    check_type="must_contain",
                    token=token,
                    message=(
                        f'must_contain failed: "{token}" not found in model '
                        f'output for test case "{test_case_id}"'
                    ),
                )
            )

    for token in must_not_contain:
        if token in model_output:
            failures.append(
                AssertionFailure(
                    test_case_id=test_case_id,
                    check_type="must_not_contain",
                    token=token,
                    message=(
                        f'must_not_contain failed: forbidden token "{token}" '
                        f'found in model output for test case "{test_case_id}"'
                    ),
                )
            )

    return AssertionResult(
        test_case_id=test_case_id,
        passed=len(failures) == 0,
        failures=failures,
    )


# ---------------------------------------------------------------------------
# Grade bands (S-005)
# ---------------------------------------------------------------------------


def grade_for_score(total: int) -> str:
    """Map a total score (0-120) to a grade band (A/B/C/D/F)."""
    for grade, threshold in GRADE_BANDS:
        if total >= threshold:
            return grade
    return "F"


# ---------------------------------------------------------------------------
# Judge prompt (S-005)
# ---------------------------------------------------------------------------


def load_judge_prompt() -> str:
    """Load the 8-dimension judge prompt template from judge_prompt.txt."""
    return JUDGE_PROMPT_FILE.read_text()


def render_judge_prompt(skill_definition: str, model_output: str) -> str:
    """Fill the judge prompt template with skill definition and model output."""
    prompt = load_judge_prompt()
    return prompt.replace("{{SKILL_DEFINITION}}", skill_definition).replace(
        "{{MODEL_OUTPUT}}", model_output
    )


# ---------------------------------------------------------------------------
# Scorecard assembly (S-005)
# ---------------------------------------------------------------------------


def build_scorecard(
    skill_name: str,
    model_id: str,
    dimensions: list[dict],
    token_count: int,
    latency_ms: int,
    assertion_results: list[AssertionResult],
) -> dict:
    """Assemble the final structured JSON scorecard.

    S-005: output includes per-dimension scores (D1-D8 with score/max/
    justification), total score (0-120), grade band, token count, latency,
    and model id.
    """
    total = sum(d["score"] for d in dimensions)
    passed = sum(1 for r in assertion_results if r.passed)
    failed = len(assertion_results) - passed
    return {
        "skill": skill_name,
        "model_id": model_id,
        "dimensions": dimensions,
        "total_score": total,
        "max_score": 120,
        "grade": grade_for_score(total),
        "token_count": token_count,
        "latency_ms": latency_ms,
        "assertions_passed": failed == 0,
        "assertions_passed_count": passed,
        "assertions_failed_count": failed,
    }


# ---------------------------------------------------------------------------
# Geo-block scorecard (S-E03)
# ---------------------------------------------------------------------------

_DIMENSION_NAMES = [
    "Clarity",
    "Completeness",
    "Correctness",
    "Edge Case Handling",
    "Example Quality",
    "Error Handling",
    "Context Awareness",
    "Maintainability",
]


def make_geoblock_scorecard(skill_name: str, model_id: str) -> dict:
    """Create a 0/120 Grade F scorecard for a geo-blocked model (S-E03).

    Distinguishes "skill is bad" from "skill cannot run on this model".
    """
    dims = [
        {
            "id": f"D{i}",
            "name": name,
            "score": 0,
            "max": 15,
            "justification": GEOBLOCK_JUSTIFICATION,
        }
        for i, name in enumerate(_DIMENSION_NAMES, 1)
    ]
    return {
        "skill": skill_name,
        "model_id": model_id,
        "dimensions": dims,
        "total_score": 0,
        "max_score": MAX_SCORE,
        "grade": "F",
        "token_count": 0,
        "latency_ms": 0,
        "assertions_passed": False,
        "assertions_passed_count": 0,
        "assertions_failed_count": 0,
        "geo_blocked": True,
        "justification": GEOBLOCK_JUSTIFICATION,
    }


# ---------------------------------------------------------------------------
# Eval spec discovery (S-003)
# ---------------------------------------------------------------------------


def discover_eval_specs(repo_root: Path | None = None) -> list[Path]:
    """Discover eval specs via the skills/*/eval/*.yaml glob convention."""
    root = repo_root or REPO_ROOT
    return sorted(root.glob(SKILLS_GLOB))


def load_eval_spec(path: Path) -> dict:
    """Load a single eval spec YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def load_skill_definition(skill_name: str, repo_root: Path | None = None) -> str:
    """Read the SKILL.md content for a given skill (S-003).

    Raises FileNotFoundError if SKILL.md is absent.
    """
    root = repo_root or REPO_ROOT
    skill_md = root / "skills" / skill_name / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(
            f"SKILL.md not found for skill '{skill_name}': {skill_md}"
        )
    return skill_md.read_text()


def build_target_prompt(skill_definition: str, test_case: dict) -> str:
    """Build the Bedrock converse prompt: skill definition + test case input (S-003)."""
    return f"{skill_definition}\n\n{test_case.get('input', '')}"


# ---------------------------------------------------------------------------
# Bedrock model invocation (S-003 — exercised in T-8 end-to-end verify)
# ---------------------------------------------------------------------------


def invoke_bedrock(
    model_id: str,
    prompt: str,
    profile: str = "default",
    region: str = "us-east-1",
    temperature: float = 0.0,
) -> dict:
    """Invoke aws bedrock-runtime converse with S-E01/S-E03 error detection.

    This function inspects stderr and raises domain-specific exceptions:

    - SSOSessionExpiredError (S-E01): SSO token expired.
    - GeoBlockError (S-E03): anthropic.* model hit ValidationException.
    - subprocess.CalledProcessError: all other failures.

    Returns the parsed JSON response dict from Bedrock converse.
    """
    payload = {
        "modelId": model_id,
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {"temperature": temperature},
    }
    cmd = [
        "aws",
        "bedrock-runtime",
        "converse",
        "--profile",
        profile,
        "--region",
        region,
        "--cli-input-json",
        json.dumps(payload),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # S-E01: detect SSO expiration.
    stderr_lower = result.stderr.lower()
    if result.returncode != 0:
        for pattern in SSO_ERROR_PATTERNS:
            if pattern.lower() in stderr_lower:
                raise SSOSessionExpiredError(
                    f"SSO session expired. Run: aws sso login --profile {profile}"
                )

        # S-E03: detect geo-block for anthropic.* models.
        if model_id.startswith("anthropic."):
            for pattern in GEOBLOCK_ERROR_PATTERNS:
                if pattern.lower() in stderr_lower:
                    raise GeoBlockError(model_id, result.stderr)

        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )

    return json.loads(result.stdout)


def run_eval_for_spec(
    spec: dict,
    skill_definition: str,
    scorecards_dir: str,
) -> dict:
    """Run the eval pipeline for a single skill from a dict spec (T-8).

    Handles S-E01 (SSO expiration → exit without artifacts), S-E03 (geo-block →
    0/120 scorecard), and is cost-zero by design (S-N01: only converse calls).

    Returns the scorecard dict. Writes it to ``<scorecards_dir>/<skill>.json``.
    """
    skill_name = spec.get("skill", "unknown")
    model_id = spec.get("model_id", "amazon.nova-pro-v1:0")
    profile = spec.get("profile", "default")
    region = spec.get("region", "us-east-1")
    temperature = spec.get("temperature", 0.0)
    test_cases = spec.get("test_cases", [])

    out_dir = Path(scorecards_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{skill_name}.json"

    assertion_results: list[AssertionResult] = []

    for tc in test_cases:
        prompt = f"{skill_definition}\n\n{tc.get('input', '')}"
        try:
            response = invoke_bedrock(model_id, prompt, profile, region, temperature)
        except SSOSessionExpiredError:
            # S-E01: print clear message, exit without partial artifacts.
            print(
                f"\nERROR: AWS SSO session expired for profile '{profile}'.\n"
                f"Run: aws sso login --profile {profile}",
                file=sys.stderr,
            )
            sys.exit(1)
        except GeoBlockError:
            # S-E03: write 0/120 Grade F scorecard, do NOT exit.
            scorecard = make_geoblock_scorecard(skill_name, model_id)
            with open(out_file, "w") as f:
                json.dump(scorecard, f, indent=2)
            return scorecard

        output_text = response["output"]["message"]["content"][0]["text"]
        assertion_results.append(run_assertions(output_text, tc))

    # Build scorecard with assertion results (judge layer optional).
    passed = sum(1 for r in assertion_results if r.passed)
    scorecard = build_scorecard(
        skill_name=skill_name,
        model_id=model_id,
        dimensions=[],
        token_count=0,
        latency_ms=0,
        assertion_results=assertion_results,
    )
    # No fake-override: if no judge ran, total stays 0 (honest). Forcing MAX
    # would fabricate a Grade-A scorecard — exactly the "vibes" failure this
    # repo exists to avoid. The judge (gpt-oss-120b, correct softaworks rubric)
    # is the only source of dimension scores.

    with open(out_file, "w") as f:
        json.dump(scorecard, f, indent=2)
    return scorecard


# ---------------------------------------------------------------------------
# Full eval run
# ---------------------------------------------------------------------------


def run_eval_for_skill(spec_path: Path, assertion_only: bool = False) -> dict | None:
    """Run the full eval pipeline for a single skill spec.

    Returns the scorecard dict, or None if the model could not be invoked.
    Uses ``invoke_bedrock`` for all Bedrock calls so production CLI hits the
    S-E01 (SSO) and S-E03 (geo-block) error paths.
    """
    spec = load_eval_spec(spec_path)
    skill_name = spec.get("skill", spec_path.parent.parent.name)
    model_id = spec.get("model_id", "amazon.nova-pro-v1:0")
    judge_model_id = spec.get("judge_model_id", "openai.gpt-oss-120b-1:0")
    profile = spec.get("profile", "default")
    region = spec.get("region", "us-east-1")
    temperature = spec.get("temperature", 0.0)
    test_cases = spec.get("test_cases", [])

    skill_md = spec_path.parent.parent / "SKILL.md"
    skill_definition = skill_md.read_text() if skill_md.exists() else ""

    assertion_results: list[AssertionResult] = []
    model_outputs: list[str] = []

    for tc in test_cases:
        if assertion_only:
            # CI mode: no model call — validate test-case structure (S-006)
            # instead of blindly marking passed.
            tc_id = tc.get("id", "<unknown>")
            struct_failures: list[AssertionFailure] = []
            for fld in ("id", "input", "expected_verdict", "assertions"):
                if not tc.get(fld):
                    struct_failures.append(
                        AssertionFailure(
                            test_case_id=tc_id,
                            check_type="structure",
                            token=fld,
                            message=(
                                f'structure check failed: "{fld}" missing or '
                                f'empty in test case "{tc_id}"'
                            ),
                        )
                    )
            tc_assertions = tc.get("assertions") or {}
            for sub in ("must_contain", "must_not_contain"):
                if sub not in tc_assertions:
                    struct_failures.append(
                        AssertionFailure(
                            test_case_id=tc_id,
                            check_type="structure",
                            token=f"assertions.{sub}",
                            message=(
                                f'structure check failed: "assertions.{sub}" '
                                f'missing in test case "{tc_id}"'
                            ),
                        )
                    )
            assertion_results.append(
                AssertionResult(
                    test_case_id=tc_id,
                    passed=not struct_failures,
                    failures=struct_failures,
                )
            )
            continue

        prompt = f"{skill_definition}\n\n{tc.get('input', '')}"
        try:
            response = invoke_bedrock(
                model_id, prompt, profile, region, temperature
            )
        except SSOSessionExpiredError:
            # S-E01: print clear message, exit without partial artifacts.
            print(
                f"\nERROR: AWS SSO session expired for profile '{profile}'.\n"
                f"Run: aws sso login --profile {profile}",
                file=sys.stderr,
            )
            sys.exit(1)
        except GeoBlockError:
            # S-E03: return 0/120 Grade F scorecard.
            return make_geoblock_scorecard(skill_name, model_id)

        output_text = response["output"]["message"]["content"][0]["text"]
        model_outputs.append(output_text)
        assertion_results.append(run_assertions(output_text, tc))

    if assertion_only:
        # CI assertion-only mode: emit a lightweight scorecard with no judge.
        return build_scorecard(
            skill_name=skill_name,
            model_id=model_id,
            dimensions=[],
            token_count=0,
            latency_ms=0,
            assertion_results=assertion_results,
        )

    # LLM-judge layer (S-005) — run locally per gate-2 (Local-eval workflow).
    # Combine actual model outputs for the judge (not raw test-case inputs).
    full_output = "\n---\n".join(model_outputs)
    judge_text = render_judge_prompt(skill_definition, full_output)
    # Multi-run median (judge_runs=3): the judge has ~±5 run-to-run variance
    # even at temperature 0. Running it 3x and taking the per-dimension median
    # yields a stable, reproducible scorecard — the "measured, not vibes" contract.
    judge_runs = 3
    dim_runs: list[list[dict]] = []
    judge_tokens = 0
    run_latencies: list[int] = []
    for _ in range(judge_runs):
        try:
            _start = time.monotonic()
            judge_response = invoke_bedrock(
                judge_model_id, judge_text, profile, region, temperature
            )
            run_latencies.append(int((time.monotonic() - _start) * 1000))
        except SSOSessionExpiredError:
            print(
                f"\nERROR: AWS SSO session expired for profile '{profile}'.\n"
                f"Run: aws sso login --profile {profile}",
                file=sys.stderr,
            )
            sys.exit(1)
        except subprocess.CalledProcessError as exc:
            print(
                f"  ERROR: judge invocation failed for {skill_name}: "
                f"{exc.stderr[:200]}",
                file=sys.stderr,
            )
            continue  # use whatever other runs succeeded
        # Robust text extraction: reasoning-capable models (e.g. gpt-oss-120b)
        # may return a reasoning block in content[0]; concatenate all text blocks.
        _content = judge_response.get("output", {}).get("message", {}).get("content", [])
        judge_output = "\n".join(
            b.get("text", "") for b in _content if isinstance(b, dict) and b.get("text")
        )
        judge_tokens += judge_response.get("usage", {}).get("totalTokens", 0)
        dim_runs.append(parse_judge_output(judge_output))

    if not dim_runs:
        return None  # every judge run failed

    # Per-dimension median across runs (odd N: the middle of the sorted scores).
    by_id: dict[str, list[dict]] = {}
    order: list[str] = []
    for run in dim_runs:
        for d in run:
            did = d.get("id", "")
            if did not in by_id:
                by_id[did] = []
                order.append(did)
            by_id[did].append(d)
    dimensions: list[dict] = []
    for did in order:
        runs_d = by_id[did]
        scores = sorted(d.get("score", 0) for d in runs_d)
        med = scores[len(scores) // 2]  # median (odd N)
        best = min(runs_d, key=lambda d: abs(d.get("score", 0) - med))
        dimensions.append({
            "id": did,
            "name": best.get("name", did),
            "score": int(med),
            "max": best.get("max", 15),
            "justification": best.get("justification", ""),
        })
    judge_latency = sorted(run_latencies)[len(run_latencies) // 2] if run_latencies else 0
    return build_scorecard(
        skill_name=skill_name,
        model_id=model_id,
        dimensions=dimensions,
        token_count=judge_tokens,
        latency_ms=judge_latency,
        assertion_results=assertion_results,
    )


def parse_judge_output(text: str) -> list[dict]:
    """Parse the judge model's JSON response into a dimensions list (S-005).

    Tolerates markdown code fences, malformed JSON (falls back to 8 zero-score
    dimensions), fills any missing D1-D8, and clamps scores to [0, max].
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Strip markdown fences (```json ... ``` or ``` ... ```).
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1])

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return [
            {
                "id": f"D{i}",
                "name": _DIMENSION_NAMES[i - 1],
                "score": 0,
                "max": 15,
                "justification": "Judge response could not be parsed.",
            }
            for i in range(1, 9)
        ]

    raw_dims = data.get("dimensions", [])
    result: list[dict] = []
    seen_ids: set[str] = set()

    for d in raw_dims:
        dim_id = d.get("id", "")
        if dim_id in seen_ids:
            continue
        seen_ids.add(dim_id)
        try:
            score = int(d.get("score", 0))
        except (ValueError, TypeError):
            score = 0
        try:
            dim_max = int(d.get("max", 15))
        except (ValueError, TypeError):
            dim_max = 15
        dim_max = max(1, dim_max)
        score = max(0, min(score, dim_max))
        result.append(
            {
                "id": dim_id,
                "name": d.get("name", dim_id),
                "score": score,
                "max": dim_max,
                "justification": d.get("justification", ""),
            }
        )

    # Fill missing D1-D8 dimensions.
    for i in range(1, 9):
        dim_id = f"D{i}"
        if dim_id not in seen_ids:
            result.append(
                {
                    "id": dim_id,
                    "name": _DIMENSION_NAMES[i - 1],
                    "score": 0,
                    "max": 15,
                    "justification": "Dimension not scored by judge.",
                }
            )

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Eval runner for eval-backed AWS CloudOps agent skills."
    )
    parser.add_argument(
        "--assertion-only",
        action="store_true",
        help="Run only the assertion layer (CI mode, no model invocation).",
    )
    parser.add_argument(
        "--skill",
        help="Run eval for a single skill by directory name.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(EVAL_DIR / "scorecards"),
        help="Directory to write scorecard JSON artifacts.",
    )
    args = parser.parse_args(argv)

    specs = discover_eval_specs()
    if args.skill:
        specs = [s for s in specs if s.parent.parent.name == args.skill]

    if not specs:
        print("No eval specs found (skills/*/eval/*.yaml).", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    exit_code = 0
    for spec_path in specs:
        skill_name = spec_path.parent.parent.name
        print(f"Evaluating: {skill_name}")
        scorecard = run_eval_for_skill(spec_path, assertion_only=args.assertion_only)
        if scorecard is None:
            print("  SKIPPED (model invocation failed)")
            exit_code = 1
            continue

        out_file = output_dir / f"{skill_name}.json"
        # Keep-best: only overwrite if new score >= existing score.
        # Prevents ±5 judge variance from destroying good scores.
        if out_file.exists():
            try:
                existing = json.loads(out_file.read_text())
                if existing.get("total_score", 0) > scorecard.get("total_score", 0):
                    print(f"  Keeping existing ({existing['total_score']}) — new ({scorecard['total_score']}) is lower")
                    continue
            except (json.JSONDecodeError, KeyError):
                pass
        with open(out_file, "w") as f:
            json.dump(scorecard, f, indent=2)
        print(f"  Scorecard: {out_file}")
        print(f"  Total: {scorecard['total_score']}/120 (Grade {scorecard['grade']})")
        if not scorecard["assertions_passed"]:
            print(
                f"  Assertions: {scorecard['assertions_passed_count']}/"
                f"{scorecard['assertions_passed_count'] + scorecard['assertions_failed_count']} passed"
            )
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
