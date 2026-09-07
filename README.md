# aws-agent-skills

<!-- badges — numbers are live from committed artifacts; see the linked docs for how each is derived -->
[![410 skills · 13 AWS service families · 6 task types](https://img.shields.io/badge/skills-410%20%C2%B7%2013%20families%20%C2%B7%206%20task%20types-232f3e)](SKILLS.md)
[![skill-judge eval: 407 scored, median-of-3 judge, 240 Grade A / 167 Grade B](https://img.shields.io/badge/eval-240%20A%20%C2%B7%20167%20B%20%C2%B7%20median--of--3%20judge-1f6feb)](SKILLS.md)
[![governance: @skills protocol source, verified end-to-end against the reference CLI](https://img.shields.io/badge/governance-%40skills%20protocol%20%C2%B7%20verified-6f42c1)](SKILL_GOVERNANCE.md)
[![security: AST10 sweep 0 findings · USF v1 signed 410/410 · did:web anchored](https://img.shields.io/badge/security-AST10%200%20findings%20%C2%B7%20USF%20signed%20410%2F410-b54708)](SKILL_GOVERNANCE.md)
[![format: agentskills.io open spec compliant, 410/410](https://img.shields.io/badge/format-agentskills.io%20compliant%20410%2F410-495057)](SPEC_COMPLIANCE_REPORT.md)
[![license: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-495057)](LICENSE)

**AWS CloudOps agent skills — measured, not asserted.** 410 skills across 13 AWS service
families and 6 task types (audit · deploy · troubleshoot · optimize · operate · automate).
Every task skill carries a committed eval scorecard produced by the shared harness; every
skill ships a signed security manifest; the whole repo is addressable through the
`@skills` protocol.

> **Not an AWS project.** This is an independent, community open-source repository by
> [Jacky Chan](https://github.com/jhkchan) (AWS Community Builder, ML & GenAI — a personal
> program membership, not an endorsement). It is not published by, affiliated with, or
> reviewed by Amazon Web Services. "AWS" and service names are used descriptively to
> identify the services these skills operate on; see [NOTICE](NOTICE) for trademark
> attribution. Where a skill and current AWS documentation disagree, **the AWS docs win**.

## Why this repo — four things nobody else ships together

| Pillar | What it is | Evidence |
|---|---|---|
| **1 · Comprehensive AWS coverage, including the newest services** | 410 skills spanning 13 families — from S3 and IAM fundamentals to S3 Tables, S3 Express One Zone directory buckets, EKS hybrid nodes, VPC Lattice, CloudWatch Application Signals, Amazon Verified Permissions, DataZone, EventBridge Scheduler, CloudTrail Lake, Neptune Analytics, MemoryDB, and MSK | [Coverage matrix](#coverage) below |
| **2 · skill-judge evaluation** | Every task skill is *scored*: Amazon Nova Pro executes it, gpt-oss-120b judges against the softaworks 8-dimension / 120-point rubric, and the **median of 3 judge runs** is committed as a JSON scorecard. No other AWS skill repo publishes eval artifacts | [SKILLS.md](SKILLS.md) · [docs/skill-judge-dashboard.md](docs/skill-judge-dashboard.md) |
| **3 · `@skills` governance** | The repo is a protocol-compliant skill source (atskills.one): every skill has a precise, resolvable address, verified end-to-end against the reference CLI — `get`, `save`, auto-trigger, and the 128-skill menu limit all tested live | [SKILL_GOVERNANCE.md](SKILL_GOVERNANCE.md) |
| **4 · AST10 security + USF v1 manifests** | Swept with the OWASP Agentic Skills Top 10 detector suite: **0 findings across 410 skills**. Each skill ships a signed `skill.usf.yaml` (declared permissions, risk tier, content hash, ed25519 signature anchored to `did:web:jhkchan.github.io`) | [SKILL_GOVERNANCE.md](SKILL_GOVERNANCE.md) |

The one-line pitch: **eval-backed grades, not vibes** — the quality claim is a committed
artifact you can re-derive, and the safety claim is a signed manifest you can verify.

---

## Install

### Method 1 — `@skills` protocol (precise, per-skill) · recommended for trying a few

```bash
git clone https://github.com/SylphAI-Inc/atskills && cd atskills && npm install --omit=dev --ignore-scripts
node bin/atskills.js get  gh:jhkchan/aws-agent-skills/skills/s3-public-access-auditor   # preview
node bin/atskills.js save gh:jhkchan/aws-agent-skills/skills/s3-public-access-auditor   # vendor into .atskills/
```

`save` copies the skill into your project's `.atskills/` with a `.source` revision pin and
resolves locally thereafter. Auto-trigger it by adding
`@gh:jhkchan/aws-agent-skills/skills/s3-public-access-auditor` to `.atskills/.autotrigger`.
(The reference CLI is not yet on npm; run it from a clone as above.)

### Method 2 — copy into your runtime's skills directory

`SKILL.md` in a named folder is the cross-agent format — these skills load in any runtime
that reads skill directories.

```bash
git clone https://github.com/jhkchan/aws-agent-skills.git

# A few skills, into Claude Code:
cp -r aws-agent-skills/skills/{s3-public-access-auditor,iam-least-privilege-advisor} ~/.claude/skills/

# The discovery index (one skill that routes to all others):
cp -r aws-agent-skills/skills/skill-catalog ~/.claude/skills/
```

| Runtime | Target directory |
|---|---|
| Claude Code | `~/.claude/skills/` |
| Cursor | `~/.agents/skills/`, `~/.cursor/skills/`, or `~/.claude/skills/` |
| Codex | `~/.codex/skills/` |
| VS Code / Copilot | `<your-project>/.github/skills/` |

Paths are from each runtime's own documentation. What is *exercised* here: the package
format is validated against the [agentskills.io](https://agentskills.io) open spec and the
`@skills` reference CLI (both 410/410) — per-runtime loading is format-level, not
behaviorally tested in every host.

> **Don't install all 410 at once.** Each skill's activation description costs ~220
> resident tokens; all 410 ≈ 90K tokens of context on every session. Install the handful
> you use, or install `skill-catalog` and let it route. This is also why the `@skills`
> protocol refuses to browse the whole repo as one menu (its limit is 128).

### Method 3 — Claude Code plugin marketplace

The repo ships a validated `.claude-plugin/marketplace.json` with **two plugins**:

```bash
claude plugin marketplace add jhkchan/aws-agent-skills

claude plugin install aws-cloudops@aws-agent-skills       # router: catalog + orchestrator (~300 tokens)
claude plugin install aws-cloudops-full@aws-agent-skills  # everything: 410 skills + 388 commands (~106K tokens)
```

`aws-cloudops` (the default choice) installs only the skill-catalog and the orchestrator —
about 300 always-on tokens — and routes you to any of the 410 skills on demand.
`aws-cloudops-full` installs the complete library; its ~106K always-on description cost is
measured (`claude plugin details aws-cloudops-full`), so reserve it for dedicated
AWS-working sessions or large-context plans.

### Discovery CLI (no install)

```bash
cd aws-agent-skills
node cli/bin/cli.js list                                  # all skills, grouped by task type
node cli/bin/cli.js list --task-type troubleshoot         # filter
node cli/bin/cli.js route "why is my Lambda timing out"   # natural-language routing
node cli/bin/cli.js route "audit my S3 buckets for public access"
node cli/bin/cli.js status                                # coverage + eval summary
```

---

## Quickstart

Install one skill (Method 1 or 2 above), then just describe the task in your agent:

```
Audit my S3 buckets for public access.
```

The skill activates, asks for the bucket configurations (or fetches them via `aws s3api`),
and returns structured verdicts:

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

The same shape works across all six task types:

| Task type | Prompt example | Skill that fires |
|---|---|---|
| **audit** | "Review this IAM policy for least-privilege violations." | `iam-least-privilege-advisor` |
| **deploy** | "Deploy a secure S3 bucket with encryption and lifecycle rules." | `s3-secure-bucket-deployer` |
| **troubleshoot** | "Why is my Lambda function timing out?" | `lambda-timeout-troubleshooter` |
| **optimize** | "Reduce my NAT Gateway spend." | `nat-gateway-cost-optimizer` |
| **operate** | "Set up automated RDS backups with cross-region copies." | `rds-backup-restore-operator` |
| **automate** | "Auto-remediate Security Hub findings on new resources." | `securityhub-remediation-automator` |

For a whole-account sweep, the orchestrator routes across auditors in a four-phase
pipeline — **Assess → Audit → Prioritize → Remediate**:

```
Run a full CloudOps security audit across my AWS account.
```

Deployer and operator skills end in a `READY_TO_DEPLOY` checklist with verification
commands — they prepare and verify changes rather than silently applying them.

### More output examples

**IAM policy review** — `Review this IAM policy for least-privilege violations.`

```text
POLICY: app-backend-role-policy
VERDICT: OVERPERMISSIVE
RISK: CRITICAL
REASON: Statement 1 grants iam:PassRole on Resource "*" — privilege escalation vector.
REMEDIATION: Scope iam:PassRole to specific service-linked roles. Remove wildcard Resource.
```

**Lambda runtime deprecation** — `Check if any of my Lambda functions use deprecated runtimes.`

```text
FUNCTION: data-processor
VERDICT: DEPRECATED_RUNTIME
RISK: HIGH
REASON: Runtime python3.9 reaches end-of-support 2025-10. AWS will block updates after 2026-01.
REMEDIATION: Upgrade to python3.13. Test with sam build && sam local invoke.
```

Full multi-finding walkthroughs live in each skill's `examples/` directory.

### Finding the right skill

- **Ask the catalog**: install `skills/skill-catalog` — 13 family tables mapping all 409
  task skills to exact paths, task types, and one-line descriptions.
- **Ask the CLI**: `node cli/bin/cli.js route "<your task>"`.
- **Slash commands**: 388 ready-made commands in `commands/aws/`, e.g.
  `/aws:audit-s3-public-access`, `/aws:deploy-s3-secure-bucket`.
- **Address it precisely**:
  `@skills:gh:jhkchan/aws-agent-skills/skills/<skill-name>` — single-skill references are
  always legal regardless of the 128-skill browsing limit. Details in
  [SKILL_GOVERNANCE.md](SKILL_GOVERNANCE.md).

---

## Coverage

**410 skills · 13 AWS service families · 6 task types.** 407 carry committed scorecards;
`aws-orchestrator` (routes rather than executes) and `skill-catalog` (a discovery index)
are unscored by design, and one deployer's judge run is pending. The family partition
follows the AWS service taxonomy; task types cover the full CloudOps lifecycle.

| Family | Skills | | Family | Skills |
|---|---|---|---|---|
| Security | 52 | | AppIntegration | 33 |
| Compute | 44 | | Databases | 31 |
| Management | 43 | | Governance | 30 |
| Analytics | 41 | | DevTools | 24 |
| Storage | 40 | | AI/ML | 16 |
| Networking | 39 | | FinOps | 12 |
| | | | Migration | 5 |

| Task type | Skills | | Task type | Skills |
|---|---|---|---|---|
| deploy | 157 | | optimize | 41 |
| troubleshoot | 59 | | automate | 31 |
| operate | 42 | | audit | 80 |

**Recent-service coverage** — the set deliberately includes services too new for any
training-data-dependent assistant to know well: S3 Tables (`s3-table-bucket-deployer`),
S3 Express One Zone (`s3-directory-bucket-deployer`), EKS hybrid nodes
(`eks-hybrid-node-deployer`), VPC Lattice (`vpclattice-service-deployer`,
`vpc-lattice-auth-auditor`), CloudWatch Application Signals
(`cloudwatch-application-signals-deployer`), Amazon Verified Permissions
(`verified-permissions-policy-auditor`), DataZone (`datazone-domain-deployer`),
EventBridge Scheduler (`eventbridge-scheduler-deployer`), CloudTrail Lake
(`cloudtrail-lake-operator`), Neptune Analytics (`neptune-graph-deployer`), MemoryDB
(`memorydb-cluster-deployer`), and MSK (`msk-cluster-auditor`, `kafka-msk-lag-troubleshooter`).

The complete scored index — every skill, score, grade, verdict rate, latency — is
[SKILLS.md](SKILLS.md).

---

## How the eval works (skill-judge)

```text
skills/*/eval/test-cases.yaml
   ->  eval/run_eval.py
   ->  Amazon Nova Pro executes the skill against its test cases
   ->  assertion layer  (must_contain / must_not_contain — deterministic, CI-runnable)
   ->  gpt-oss-120b judges against the softaworks 8-dimension / 120-point rubric
   ->  median of 3 judge runs  (kills the ±5 run-to-run judge variance)
   ->  JSON scorecard, committed at eval/scorecards/<skill>.json
```

| Dimension | Weight | | Dimension | Weight |
|---|---|---|---|---|
| D1 Knowledge delta | 20 | | D5 Progressive disclosure | 15 |
| D2 Completeness | 15 | | D6 Interoperability | 15 |
| D3 Accuracy | 15 | | D7 Efficiency | 10 |
| D4 Clarity | 15 | | D8 Practical usability | 15 |

**Grade A ≥ 108/120.** Current distribution: **240 A / 167 B** (407 scored). The shipped
Grade Bs sit at 96–107 — strong, but short of the floor on at least one dimension (the
scorecard names it); root-cause analysis of
the A/B boundary is published in [ROOT_CAUSE_REPORT.md](ROOT_CAUSE_REPORT.md), and the
keep-best re-eval policy means scores only improve on re-runs.

Each skill has two eval surfaces:

| Directory | Purpose |
|---|---|
| `eval/` | **Assertion layer** — deterministic verdict-token checks, runs in CI without AWS credentials |
| `evals/` | **Structured eval** — case metadata, prompts, and the *without-skill baselines* that make the with/without delta measurable |

The `evals/` structure follows the [OpenAI eval-skills guidance](https://developers.openai.com/blog/eval-skills)
and [Anthropic's "Demystifying evals for AI agents"](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

### Run it yourself

```bash
# Assertion layer only — no AWS credentials needed
python3 eval/run_eval.py --assertion-only

# Full eval (executor + judge) — requires Bedrock access
python3 eval/run_eval.py --skill s3-public-access-auditor
python3 eval/run_eval.py                        # all skills

# Impact eval — with-skill vs without-skill delta
python3 eval/impact_eval.py --skill s3-public-access-auditor

# Refresh the published index
python3 eval/generate_readme_table.py           # regenerates SKILLS.md from scorecards
```

### Highest-scored skills (full table: SKILLS.md)

| Skill | Model | Score | Grade | Verdicts |
|---|---|---|---|---|
| shield-advanced-coverage-auditor | Nova Pro | 116/120 | A | 6/6 |
| backup-plan-auditor | Nova Pro | 115/120 | A | 6/6 |
| stepfunctions-statemachine-deployer | Nova Pro | 115/120 | A | 3/5 |
| athena-workgroup-auditor | Nova Pro | 114/120 | A | 6/6 |
| billing-account-auditor | Nova Pro | 114/120 | A | 6/6 |
| sts-cross-account-role-auditor | Nova Pro | 114/120 | A | 6/6 |

---

## Governance & security

**`@skills` protocol (atskills.one).** The repo is a verified skill source. Single-skill
addresses always resolve; the root menu's 410 skills exceed the protocol's 128-skill
browsing limit by design, so discovery goes through `skill-catalog`. Verified live with
the reference CLI: `get`, `save` (+ `.source` pin), local-first resolution, and
`.autotrigger` residency. Full audit: [SKILL_GOVERNANCE.md](SKILL_GOVERNANCE.md).

**AST10 security sweep.** All 410 skills were audited with the independent
[jhkchan/owasp-ast10-agent-skills](https://github.com/jhkchan/owasp-ast10-agent-skills)
implementation of the OWASP Agentic Skills Top 10: **0 error-level findings, 0 warning
signals**. The decidability ledger (what a static sweep cannot decide — prose-level
intent, update drift, process governance) is recorded rather than implied.

**USF v1 manifests.** Every skill ships `skill.usf.yaml`: declared permissions
(read-only, identity-file deny floor, default-deny network), a risk tier by instructed
effect (81 L0 / 59 L1 / 266 L2 / 4 L3), a content hash over the runtime-loaded
instruction bytes, and an ed25519 signature over the RFC 8785 canonical manifest,
anchored to `did:web:jhkchan.github.io`:

```yaml
# skills/vpc-peering-deployer/skill.usf.yaml (excerpt — fields condensed)
permissions:
  files:
    read: [./SKILL.md, ./skill.usf.yaml, ./references/advanced-patterns.md, ...]
    write: []                                   # instructions only — writes nothing
    deny_write: [SOUL.md, MEMORY.md, AGENTS.md] # identity-file floor
  network: { allow: [], deny: "*" }             # default-deny: no package egress
  shell: false
risk_tier: L2          # deployer: creates/modifies infrastructure
signature: "ed25519:…" # verifies against https://jhkchan.github.io/.well-known/did.json
```

A verified signature answers *"who published this"*, never *"is this safe"* — read the
risk tier and the permissions.

**Format compliance.** 410/410 skills pass the [agentskills.io](https://agentskills.io)
open Agent Skills spec (frontmatter types, ≤1024-char descriptions, <500-line bodies,
progressive disclosure). Audit: [SPEC_COMPLIANCE_REPORT.md](SPEC_COMPLIANCE_REPORT.md).

---

## FAQ

### Why not contribute to `aws/agent-toolkit-for-aws`?

We investigated. The official AWS repo (140 skills) has a dual block on external
contributions: `CONTRIBUTING.md` states *"This project is not accepting external code
contributions at this time."*, and GitHub enforces `collaborators_only` PR creation —
public forks cannot even open PRs. Of its last 100 PRs, 97 were AWS staff. There is no
documented pathway in. The adjacent `awslabs/agent-plugins` does accept external PRs and
stays open as a future upstream path for the best Grade-A skills; the independent repo is
the faster route to shipping eval-backed work today.

### What models run the eval?

- **Executor** (runs the skill): Amazon Nova Pro (`amazon.nova-pro-v1:0`), plus
  `openai.gpt-oss-20b` on some skills.
- **Judge** (scores the run): `openai.gpt-oss-120b-1:0` via the softaworks skill-judge
  rubric, median of 3 runs.

### What does Grade A mean? Why do you ship Grade B skills?

Grade A ≥ 108/120 (90%) on the 8-dimension rubric. Grade B (the shipped ones sit at
96–107) is a working skill that dropped points on at least one dimension; the scorecard
shows exactly which and why.
We publish both rather than hiding the Bs: the grade is the contract, and a B you can
inspect beats an A you have to trust. Hardening continues against the published
[root-cause analysis](ROOT_CAUSE_REPORT.md), and the keep-best policy means a re-eval can
only raise a committed score.

### How was the coverage chosen?

The skill universe was derived bottom-up from the 421-service botocore enumeration:
287 CloudOps-relevant services × the task types each genuinely supports, then built to
saturation. Coverage is now complete across all 13 families and 6 task types; new skills
track new AWS services as they reach GA.

### How do I contribute a skill?

1. Create `skills/<your-skill>/SKILL.md` (validate against `schema/SKILL.schema.json`).
2. Add `eval/test-cases.yaml` with 5–6 deterministic cases.
3. Run `python3 eval/run_eval.py --skill <your-skill>` and confirm Grade A.
4. Run `python3 scripts/generate_usf_manifests.py --force` for the manifest, and refresh
   the index with `python3 eval/generate_readme_table.py`.
5. Open a PR — CI runs the assertion layer; the maintainer reviews and commits the judge
   scorecard.

Full guide: [CONTRIBUTING.md](CONTRIBUTING.md). Skill lifecycle (capability vs.
preference classification, retirement cadence): [MAINTENANCE.md](MAINTENANCE.md).

### How is this different from other AWS skill repos?

`aws/agent-toolkit-for-aws` (140 skills, closed to external PRs) and
`itsmostafa/aws-agent-skills` (18 skills) publish SKILL.md + references with **zero
public eval artifacts**. This repo makes the quality claim structural: committed
median-of-3 scorecards, signed USF manifests, a protocol-verified addressing scheme, and
a zero-findings security sweep. Measured, not asserted.

---

## Repository layout

```
skills/<name>/           SKILL.md + references/ + eval/ + evals/ + examples/ + skill.usf.yaml
commands/aws/            388 slash commands (one per task skill)
eval/                    shared harness: run_eval.py, impact_eval.py, scorecards/, generate_readme_table.py
scripts/                 USF manifest generator (+ vendored content-hash algorithm)
cli/                     discovery/routing CLI (Node, zero deps)
schema/                  SKILL.schema.json (frontmatter contract)
docs/                    architecture, skill-judge dashboard
```

## License

[Apache License 2.0](LICENSE) — see [NOTICE](NOTICE) for AWS trademark attribution.

## Author

**Jacky Chan** — AWS Community Builder (ML & GenAI). Personal, community project; not
affiliated with or endorsed by any employer.
