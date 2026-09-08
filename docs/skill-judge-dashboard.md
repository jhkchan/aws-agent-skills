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

D1 is weighted highest (max 20), D7 lowest (max 10), the rest max 15 — total 120. Names below are exactly as the judge emits them (`eval/judge_prompt.txt` / committed scorecards).

| ID | Dimension | Max | What it measures |
|---|---|---|---|
| D1 | Knowledge Delta | 20 | Expert content a capable model doesn't already know |
| D2 | Mindset + Appropriate Procedures | 15 | Encodes AWS-specific procedures and audit flows, not generic advice |
| D3 | Anti-Pattern Quality | 15 | Concrete NEVER-lists and pitfalls with precise triggers |
| D4 | Specification Compliance | 15 | Follows the skill's own declared output contract |
| D5 | Progressive Disclosure | 15 | Compact body, depth in references loaded on demand |
| D6 | Freedom Calibration | 15 | Right level of constraint — neither rigid nor laissez-faire |
| D7 | Pattern Recognition | 10 | Recognizable structure that aids comprehension |
| D8 | Practical Usability | 15 | Decision trees, exact CLI syntax, working examples |

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
