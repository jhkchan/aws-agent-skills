# Show HN: 405 eval-backed AWS CloudOps agent skills (open source)

**TL;DR:** I built a repo of 405 AWS CloudOps agent skills — covering 13 service families and 6 task types (audit, deploy, troubleshoot, optimize, operate, automate). Every skill ships with a committed eval scorecard scored by a median-of-3 LLM judge on an 8-dimension rubric. No other AWS agent-skills repo publishes eval artifacts. Apache-2.0.

## The problem

Every AWS agent-skills repo I found — `aws/agent-toolkit-for-aws` (140 skills), community repos — ships `SKILL.md` files and **claims** "thorough evals" with zero published artifacts. You have to take the author's word that the skill works.

That's not good enough. If we're handing cloud infrastructure decisions to AI agents, the skills guiding those decisions need to be measured, not asserted.

## What I built

**[jhkchan/aws-agent-skills](https://github.com/jhkchan/aws-agent-skills)** — 405 eval-backed AWS CloudOps agent skills.

### Eval-backed by design

Every skill has:
- Co-located `eval/test-cases.yaml` with 5 test cases (must_contain / must_not_contain assertions)
- `evals/` directory with 5 prompts + 5 baselines (with-skill vs without-skill delta)
- A committed `eval/scorecards/<skill>.json` with per-dimension scores

The eval harness runs each skill's SKILL.md through a model (Nova Pro), sends the output to a judge (gpt-oss-120b), and scores it on the [softaworks 8-dimension rubric](https://github.com/softaworks/agent-toolkit/tree/main/skills/skill-judge):

| Dimension | Max | What it measures |
|---|---|---|
| D1 Knowledge Delta | 20 | Expert content not in the base model |
| D2 Mindset | 15 | Analytical framework quality |
| D3 Anti-Pattern | 15 | Catches common mistakes |
| D4 Spec Compliance | 15 | Follows the output contract |
| D5 Progressive Disclosure | 15 | Right depth at right time |
| D6 Freedom Calibration | 15 | Appropriate autonomy |
| D7 Pattern Recognition | 10 | Recognizes the scenario |
| D8 Practical Usability | 15 | Decision trees, working examples |

Each skill is run 3× and the per-dimension **median** is taken (±5 point judge variance makes single runs unreliable).

**Grade A = 108+ / 120 (90%). Grade B = 84-107.** Currently: 193A / 395 scored (48.9% A rate).

### Coverage

**13 AWS service families:**

| Family | Skills | | Family | Skills |
|---|---|---|---|---|
| Security | 51 | | AppIntegration | 34 |
| Compute | 43 | | Databases | 31 |
| Management | 42 | | Governance | 30 |
| Analytics | 41 | | DevTools | 24 |
| Storage | 40 | | AI/ML | 16 |
| Networking | 38 | | FinOps | 13 |
| | | | Migration | 5 |

**6 task types:**

| Type | Count | Example |
|---|---|---|
| deploy | 155 | `vpc-peering-deployer`, `rds-bluegreen-deployer` |
| audit | 80 | `s3-public-access-auditor`, `iam-least-privilege-advisor` |
| troubleshoot | 58 | `lambda-invocation-troubleshooter`, `s3-access-denied-troubleshooter` |
| optimize | 41 | `s3-storage-class-optimizer`, `lambda-cold-start-optimizer` |
| operate | 40 | `secrets-rotation-operator`, `rds-snapshot-operator` |
| automate | 31 | `securityhub-remediation-automator`, `drift-detection-automator` |

### Example: S3 Public Access Auditor

**Prompt:** `Audit my S3 buckets for public access.`

```text
BUCKET: app-data-prod
VERDICT: SAFE
REASON: S3 Block Public Access is fully enabled (all 4 settings).
REMEDIATION: None required.

BUCKET: public-assets-cdn
VERDICT: PUBLIC
REASON: BPA is OFF. Bucket policy grants s3:GetObject to Principal "*" with no condition.
REMEDIATION: Enable BPA (all 4 settings). Use CloudFront + OAC if public CDN is intended.
```

Every skill follows a STRICT output contract — required output structure, FORBIDDEN patterns, and a perfect example. This is what differentiates Grade A from Grade B skills: D8 (Practical Usability) rewards decision trees, working examples, and error handling that produces immediately actionable output.

## How to use

### Claude Code / Cursor / Windsurf

```bash
git clone https://github.com/jhkchan/aws-agent-skills.git
cp -r aws-agent-skills/skills/s3-public-access-auditor ~/.claude/skills/

# Then just describe the task:
# "Audit my S3 buckets for public access"
```

### CLI discovery and routing

```bash
node cli/bin/cli.js list --task-type deploy
node cli/bin/cli.js route "deploy a secure VPC"
node cli/bin/cli.js status
```

The CLI routes by keyword with task-type-aware matching — deploy skills win for deploy prompts, troubleshoot skills for diagnostic prompts.

## Why I built this

As an AWS Community Builder (ML & GenAI), I see a gap: the community has agent skills, but no one publishes eval proof. The skills are claimed to work, but there's no scorecard, no rubric, no reproducible methodology.

This repo makes the eval-backed contract **structural** — you can run `python3 eval/run_eval.py --skill <name>` and reproduce the score yourself. The judge prompt is open. The rubric is open. The scorecard is committed.

## What's next

- **More variance re-evals** — the gpt-oss-120b judge has ±5 run-to-run variance. Mass re-evals promote ~20-30% of near-threshold B skills to A per round.
- **Community contributions** — the eval harness makes PR review objective: a new skill must score Grade B (84+) to merge.
- **Upstream contribution** — if organic reach falls short, canonical skills can be contributed to `awslabs/agent-plugins`.

## Tech details

- **Eval model:** amazon.nova-pro-v1:0 (execution)
- **Judge model:** gpt-oss-120b (scoring)
- **Rubric:** softaworks 8-dimension / 120pt
- **Methodology:** median-of-3 per dimension
- **Tests:** 824 passing (YAML/JSON parse, schema validation, CLI routing)
- **License:** Apache-2.0

---

*Jacky Chan — AWS Community Builder (ML & GenAI). This is a personal/community project, not affiliated with or endorsed by AWS.*
