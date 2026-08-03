"""Skill directory discovery and validation for the eval-backed contract.

Provides the convention-based discovery logic used by eval/run_eval.py and CI
to enforce the structural contract: every skill directory must contain an
eval/ subdirectory with co-located test cases (spec S-E04).
"""

from __future__ import annotations

import pathlib


def validate_skill_dir(skill_dir: pathlib.Path) -> list[str]:
    """Validate a single skill directory against the eval-backed contract.

    Returns a list of warning strings. An empty list means the skill passes
    all structural checks.
    """
    warnings: list[str] = []
    skill_name = skill_dir.name

    eval_dir = skill_dir / "eval"
    if not eval_dir.is_dir():
        warnings.append(
            f"Skill {skill_name} has no eval/ directory "
            "-- eval-backed contract requires co-located test cases"
        )
        return warnings

    test_cases = eval_dir / "test-cases.yaml"
    if not test_cases.exists():
        warnings.append(
            f"Skill {skill_name} has eval/ but no test-cases.yaml "
            "-- eval-backed contract requires co-located test cases"
        )

    return warnings


def discover_skills(skills_dir: pathlib.Path) -> list[str]:
    """Discover skill directories under *skills_dir* and validate each.

    Returns a list of warning strings for any skills that fail the
    eval-backed contract (missing eval/ or test-cases.yaml).
    """
    warnings: list[str] = []
    if not skills_dir.is_dir():
        return warnings

    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        if not (child / "SKILL.md").exists():
            continue
        warnings.extend(validate_skill_dir(child))

    return warnings
