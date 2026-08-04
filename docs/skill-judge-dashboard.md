# Skill Judge Dashboard — Eval Scorecards

Per-skill LLM-judge scorecards sourced from committed artifacts in
`eval/scorecards/`. Each skill is graded on an 8-dimension / 120-point rubric
by an independent judge model. Grade A = >=108/120 (Tier A, the eval-backed
wedge); Grade B = >=84/120 (Tier B, assertion-backed full pattern).

---

## Current scorecards

| Skill | Model | Total | Grade | Verdict | Assertions | Scorecard |
|---|---|---|---|---|---|---|
| s3-public-access-auditor | amazon.nova-pro-v1:0 | — | A | PUBLIC / SAFE / AMBIGUOUS | 5/5 | [JSON](../eval/scorecards/s3-public-access-auditor.json) |
| iam-least-privilege-advisor | amazon.nova-pro-v1:0 | — | A | OVERPERMISSIVE / LEAST_PRIVILEGE / AMBIGUOUS | 5/5 | [JSON](../eval/scorecards/iam-least-privilege-advisor.json) |
| ec2-security-group-auditor | amazon.nova-pro-v1:0 | — | A | OPEN / PUBLIC_NONCRITICAL / RESTRICTED | 5/5 | [JSON](../eval/scorecards/ec2-security-group-auditor.json) |

---

## 8-Dimension Rubric

Each dimension is scored 0-15 (total max: 120).

| Dimension | ID | What it measures |
|---|---|---|
| Clarity | D1 | Is the skill's logic clear and unambiguous? |
| Completeness | D2 | Does it cover the documented scope exhaustively? |
| Correctness | D3 | Are the classifications/verdicts technically correct? |
| Edge Case Handling | D4 | Does it handle multi-statement, malformed, and edge inputs? |
| Example Quality | D5 | Are the test cases representative and challenging? |
| Error Handling | D6 | Does it fail gracefully with clear messages? |
| Context Awareness | D7 | Does it account for AWS service interactions and dependencies? |
| Maintainability | D8 | Is the skill definition maintainable and extensible? |

---

## Grade bands

| Grade | Score range | Percentage | Tier | Meaning |
|---|---|---|---|---|
| A | >= 108 | >= 90% | Tier A | Eval-backed reference implementation |
| B | >= 84 | >= 70% | Tier B | Assertion-backed, full pattern |
| C | >= 60 | >= 50% | — | Needs improvement |
| D | >= 36 | >= 30% | — | Significant gaps |
| F | < 36 | < 30% | — | Failing |

---

## Running the eval

```bash
# Assertion-only (CI mode, no AWS credentials)
python3 eval/run_eval.py --assertion-only

# Full LLM-judge (local, requires AWS SSO)
python3 eval/run_eval.py --profile default

# Single skill
python3 eval/run_eval.py --skill s3-public-access-auditor
```

The judge model is `openai.gpt-oss-120b-1:0` (via Bedrock). The assertion
layer runs `must_contain` / `must_not_contain` keyword checks. Both layers
write to `eval/scorecards/<skill>.json`.
