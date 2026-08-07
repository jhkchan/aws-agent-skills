#!/usr/bin/env python3
"""Impact evaluation harness for AWS CloudOps agent skills.

Measures the WITH-SKILL vs WITHOUT-SKILL performance delta — the core
methodology from Philipp Schmid (Google DeepMind) "Don't Ship Skills Without
Evals": a skill is only valuable if it measurably improves model performance
over baseline.

Pipeline per test case:
  1. Run target model WITHOUT skill loaded (raw prompt only) → baseline output
  2. Run target model WITH skill loaded → with-skill output
  3. Judge BOTH outputs with gpt-oss-120b on the same 8-dimension rubric
  4. Report per-dimension delta and overall impact score

If the delta ≤ 0 across multiple test cases, the skill provides no measurable
value and is a retirement candidate (per the retirement cadence).

Usage:
    python3 eval/impact_eval.py --skill s3-public-access-auditor [--profile default]
    python3 eval/impact_eval.py  # all skills with evals/ dirs

Satisfies: impact-eval methodology (skills-bench approach).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

# Reuse the invoke_bedrock + judge infrastructure from run_eval.py
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "eval"))

from run_eval import (
    invoke_bedrock,
    parse_judge_output,
    render_judge_prompt,
    SSOSessionExpiredError,
    GeoBlockError,
    MAX_SCORE,
)

GRADE_BANDS = [
    ("A", 108),
    ("B", 84),
    ("C", 60),
    ("D", 36),
    ("F", 0),
]


def grade_for(total: int) -> str:
    for label, floor in GRADE_BANDS:
        if total >= floor:
            return label
    return "F"


def extract_text(response: dict) -> str:
    """Extract text from Bedrock converse response (handles multi-block)."""
    content = response.get("output", {}).get("message", {}).get("content", [])
    parts = []
    for block in content:
        if "text" in block:
            parts.append(block["text"])
    return "\n".join(parts) if parts else ""


def judge_output(
    skill_definition: str,
    model_output: str,
    judge_model_id: str,
    profile: str,
    region: str,
) -> list[dict]:
    """Run the gpt-oss-120b judge on a single output and return dimensions."""
    judge_prompt = render_judge_prompt(skill_definition, model_output)
    try:
        response = invoke_bedrock(
            judge_model_id, judge_prompt, profile, region, temperature=0.0
        )
    except (SSOSessionExpiredError, GeoBlockError) as e:
        print(f"  ERROR: Judge invocation failed: {e}", file=sys.stderr)
        return []

    text = extract_text(response)
    return parse_judge_output(text)


def run_impact_for_skill(
    skill_dir: Path,
    profile: str = "default",
    region: str = "us-east-1",
    target_model: str = "amazon.nova-pro-v1:0",
    judge_model: str = "openai.gpt-oss-120b-1:0",
) -> dict:
    """Run impact eval for a single skill.

    Returns an impact report dict with per-case baseline and with-skill scores
    + the delta.
    """
    skill_name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {"skill": skill_name, "error": "SKILL.md not found"}

    skill_definition = skill_md.read_text()

    # Load eval prompts from evals/prompts/
    prompts_dir = skill_dir / "evals" / "prompts"
    if not prompts_dir.exists():
        # Fall back to eval/test-cases.yaml inputs
        spec_path = skill_dir / "eval" / "test-cases.yaml"
        if not spec_path.exists():
            return {"skill": skill_name, "error": "no eval prompts found"}
        spec = yaml.safe_load(spec_path.read_text())
        prompts = [(tc["id"], tc["input"]) for tc in spec.get("test_cases", [])]
    else:
        prompts = []
        for p in sorted(prompts_dir.glob("*.md")):
            prompts.append((p.stem, p.read_text()))

    if not prompts:
        return {"skill": skill_name, "error": "no test prompts found"}

    case_results = []

    for case_id, prompt_text in prompts:
        print(f"  [{skill_name}] case: {case_id} ...", end=" ", flush=True)

        # 1. Baseline: run WITHOUT skill (raw prompt only)
        try:
            baseline_response = invoke_bedrock(
                target_model, prompt_text, profile, region, temperature=0.0
            )
            baseline_output = extract_text(baseline_response)
        except SSOSessionExpiredError:
            print("SSO EXPIRED")
            print(
                f"\nERROR: AWS SSO session expired. Run: aws sso login --profile {profile}",
                file=sys.stderr,
            )
            sys.exit(1)
        except Exception as e:
            print(f"BASELINE ERROR: {e}")
            continue

        # 2. With skill: run WITH skill loaded
        with_skill_prompt = f"{skill_definition}\n\n{prompt_text}"
        try:
            with_skill_response = invoke_bedrock(
                target_model, with_skill_prompt, profile, region, temperature=0.0
            )
            with_skill_output = extract_text(with_skill_response)
        except SSOSessionExpiredError:
            print("SSO EXPIRED")
            sys.exit(1)
        except Exception as e:
            print(f"WITH-SKILL ERROR: {e}")
            continue

        # 3. Judge both outputs (median of 1 for impact — we want the delta, not absolute)
        baseline_dims = judge_output(
            skill_definition, baseline_output, judge_model, profile, region
        )
        with_skill_dims = judge_output(
            skill_definition, with_skill_output, judge_model, profile, region
        )

        baseline_total = sum(d.get("score", 0) for d in baseline_dims)
        with_skill_total = sum(d.get("score", 0) for d in with_skill_dims)
        delta = with_skill_total - baseline_total

        impact_label = "POSITIVE" if delta > 5 else ("NEUTRAL" if delta >= -5 else "NEGATIVE")

        case_results.append({
            "case_id": case_id,
            "baseline_score": baseline_total,
            "with_skill_score": with_skill_total,
            "delta": delta,
            "impact": impact_label,
            "baseline_dims": baseline_dims,
            "with_skill_dims": with_skill_dims,
        })

        print(f"baseline={baseline_total}/120 with_skill={with_skill_total}/120 delta={delta:+d} [{impact_label}]")

    # Aggregate
    if not case_results:
        return {"skill": skill_name, "error": "no cases completed successfully"}

    avg_delta = sum(c["delta"] for c in case_results) / len(case_results)
    positive_cases = sum(1 for c in case_results if c["delta"] > 5)
    neutral_cases = sum(1 for c in case_results if -5 <= c["delta"] <= 5)
    negative_cases = sum(1 for c in case_results if c["delta"] < -5)

    # Retirement recommendation
    if avg_delta <= 0:
        recommendation = "RETIRE_CANDIDATE"
    elif avg_delta < 5:
        recommendation = "LOW_IMPACT"
    elif avg_delta < 10:
        recommendation = "MODERATE_IMPACT"
    else:
        recommendation = "HIGH_IMPACT"

    report = {
        "skill": skill_name,
        "target_model": target_model,
        "judge_model": judge_model,
        "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "case_count": len(case_results),
        "avg_delta": round(avg_delta, 1),
        "positive_cases": positive_cases,
        "neutral_cases": neutral_cases,
        "negative_cases": negative_cases,
        "recommendation": recommendation,
        "cases": case_results,
    }

    # Write impact report
    impact_dir = REPO_ROOT / "eval" / "impact-reports"
    impact_dir.mkdir(parents=True, exist_ok=True)
    out_file = impact_dir / f"{skill_name}.json"
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Impact evaluation: measure with-skill vs without-skill performance delta"
    )
    parser.add_argument("--skill", help="Specific skill to evaluate")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--target-model", default="amazon.nova-pro-v1:0")
    parser.add_argument("--judge-model", default="openai.gpt-oss-120b-1:0")
    args = parser.parse_args()

    skills_dir = REPO_ROOT / "skills"

    if args.skill:
        skill_dirs = [skills_dir / args.skill]
        if not skill_dirs[0].exists():
            print(f"Error: skill '{args.skill}' not found", file=sys.stderr)
            sys.exit(1)
    else:
        skill_dirs = sorted(d for d in skills_dir.iterdir() if d.is_dir())

    reports = []
    for sd in skill_dirs:
        if sd.name == "aws-orchestrator":
            continue
        print(f"\n=== Impact eval: {sd.name} ===")
        report = run_impact_for_skill(
            sd,
            profile=args.profile,
            region=args.region,
            target_model=args.target_model,
            judge_model=args.judge_model,
        )
        reports.append(report)

    # Summary
    print("\n" + "=" * 80)
    print("IMPACT EVAL SUMMARY")
    print("=" * 80)
    print(f"{'Skill':<45} {'Avg Δ':>6} {'Rec':<20}")
    print("-" * 80)
    for r in reports:
        if "error" in r:
            print(f"{r['skill']:<45} {'ERR':>6} {r['error']}")
        else:
            print(f"{r['skill']:<45} {r['avg_delta']:>+6.1f} {r['recommendation']}")
    print("-" * 80)

    high = sum(1 for r in reports if r.get("recommendation") == "HIGH_IMPACT")
    moderate = sum(1 for r in reports if r.get("recommendation") == "MODERATE_IMPACT")
    low = sum(1 for r in reports if r.get("recommendation") == "LOW_IMPACT")
    retire = sum(1 for r in reports if r.get("recommendation") == "RETIRE_CANDIDATE")
    print(f"\nHIGH_IMPACT: {high}  MODERATE: {moderate}  LOW: {low}  RETIRE_CANDIDATE: {retire}")


if __name__ == "__main__":
    main()
