# Contributing to aws-agent-skills

Thank you for your interest in contributing. This repo ships **eval-backed**
AWS CloudOps agent skills — every skill carries a co-located eval specification
that produces a per-dimension scorecard when run through the shared Python
harness. A skill without an eval is considered incomplete.

## Repository layout

```text
skills/<name>/
  SKILL.md            # minimal skill format: name/description/version frontmatter + body
  references/         # optional supplementary docs
  eval/
    test-cases.yaml   # co-located eval spec (the eval-backed contract)
eval/
  run_eval.py         # shared runner: globs skills/*/eval/*.yaml
.github/workflows/    # CI: assertion-only on every PR (no AWS credentials)
```

## How to add a skill

1. Create `skills/<your-skill-name>/SKILL.md` with the minimal frontmatter
   (`name`, `description`, `version`) — the same format used by
   [aws/agent-toolkit-for-aws](https://github.com/aws/agent-toolkit-for-aws).
2. Add `skills/<your-skill-name>/eval/test-cases.yaml` with deterministic test
   cases and `must_contain` / `must_not_contain` assertions (see existing
   skills for the schema).
3. Run the assertion layer locally:
   ```bash
   python3 eval/run_eval.py --assertion-only
   ```
4. Open a PR. CI runs the assertion layer on every PR (no AWS credentials
   needed). The LLM-judge layer is run locally by the maintainer and the
   resulting scorecard JSON is committed as an artifact.

## Eval-backed floor

A skill is listed as **eval-backed** in the README only if it ships a
per-dimension scorecard AND scores **>=70/120 (Grade B)**. Below the floor,
the skill is returned for improvement rather than shipped as eval-backed.

## License

By contributing, you agree that your contributions are licensed under the
[Apache License 2.0](./LICENSE).

## Author

Jacky Chan — AWS Community Builder. This repo is de-branded: it carries no
employer, company, or product branding. Personal attribution only.
