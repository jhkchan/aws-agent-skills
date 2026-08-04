# Architecture — AWS CloudOps Agent Skills

This document describes the repo's layered architecture, derived from the
softaworks skill-suite pattern and adapted for AWS CloudOps auditing.

---

## Layer overview

```
┌─────────────────────────────────────────────────────────────────┐
│  USER ENTRY POINTS                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ /aws:*      │  │ NL prompt    │  │ cli/bin/cli.js route   │ │
│  │ slash cmds  │  │ (natural)    │  │ (programmatic routing) │ │
│  └──────┬──────┘  └──────┬───────┘  └───────────┬────────────┘ │
│         │                │                       │              │
├─────────┴────────────────┴───────────────────────┴──────────────┤
│  ORCHESTRATOR LAYER                                             │
│  skills/aws-orchestrator/SKILL.md                               │
│    └── references/pipeline-phases.md  (4-phase routing)         │
│    └── references/routing-logic.md    (NL -> skill matching)     │
├─────────────────────────────────────────────────────────────────┤
│  SPECIALIST SKILLS LAYER                                        │
│  ┌──────────────────┐ ┌────────────────────┐ ┌───────────────┐ │
│  │ s3-public-       │ │ iam-least-         │ │ ec2-security- │ │
│  │ access-auditor   │ │ privilege-advisor  │ │ group-auditor │ │
│  │ SKILL.md         │ │ SKILL.md           │ │ SKILL.md      │ │
│  │ references/      │ │ references/        │ │ references/   │ │
│  │ eval/test-cases  │ │ eval/test-cases    │ │ eval/test-cases│ │
│  └──────────────────┘ └────────────────────┘ └───────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  SHARED INFRASTRUCTURE                                          │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐ ┌────────────────┐ │
│  │ schema/  │ │ _aws_     │ │ eval/      │ │ commands/aws/  │ │
│  │ SKILL.   │ │ shared/   │ │ run_eval.py│ │ pipeline.md    │ │
│  │ schema   │ │ taxonomy  │ │ judge      │ │ status.md      │ │
│  │ .json    │ │ iam-ref   │ │ scorecards │ │ help.md        │ │
│  │          │ │ cli-ref   │ │            │ │                │ │
│  └──────────┘ └───────────┘ └────────────┘ └────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  MARKETPLACE MANIFESTS                                          │
│  skills.sh.json  |  .claude-plugin/marketplace.json  |  package.json │
└─────────────────────────────────────────────────────────────────┘
```

---

## Pattern provenance

This repo's architecture is derived from studying these source repos:

| Source repo | What we adopted | What we adapted |
|---|---|---|
| `the internal reference repo/sales-agent-skills` | Top-level layout (commands/, cli/, schema/, skills.sh.json, .claude-plugin/, USAGE.md), orchestrator-with-references pattern, evals/ structure, slash-command frontmatter (description + nl_triggers + routes_to) | Domain (sales -> AWS CloudOps); pipeline stages (RAIN 6-stage -> CloudOps 4-phase); verdict shape (advisory -> deterministic) |
| `the internal reference repo/programming-agent-skills` | `_programming_shared/` cross-cutting reference pattern -> `_aws_shared/` | Content (Pragmatic Programmer concepts -> AWS service taxonomy, IAM patterns, CLI reference) |
| `softaworks/agent-toolkit` | agents/ routing concept, commands/ as slash-command entry points | agents/ directory folded into skills/aws-orchestrator/ (single orchestrator vs multiple agents) |

---

## Key design decisions

### 1. Co-located evals (not centralized)

Each skill ships `eval/test-cases.yaml` inside its own directory
(`skills/<name>/eval/test-cases.yaml`). This follows the repo's original
Phase 2 contract and differs from the reference repo's `evals/` directory
(`evals/evals.json` + `evals/eval_config.yaml`). The AWS repo preserves the
existing eval convention for backwards compatibility — the eval runner globs
`skills/*/eval/*.yaml`. Phase 3 adds the `evals/` structured layer as a
future canonical surface (retrofit in subsequent work).

### 2. Orchestrator as a skill (not a separate agent)

The structured-eval pattern uses `skills/<domain>-orchestrator/SKILL.md` as a skill
that an LLM reads and follows. softaworks uses `agents/*.md` as separate
agent definitions. We follow the structured-eval pattern: the orchestrator is a skill
with `metadata.entry_point: true`, making it discoverable by the same
frontmatter-based routing as specialist skills.

### 3. Functional CLI (not a stub)

the reference repo's `cli/bin/cli.js` is a stub (`console.log("full CLI coming")`). We
make it functional: it discovers skills, routes prompts by keyword matching,
validates against the schema, and reports status. This enables
`node cli/bin/cli.js route "check my S3"` to return the matched skill(s)
without an LLM — useful for CI, scripting, and debugging.

### 4. _aws_shared/ at repo root (not under skills/)

the internal reference repo places `_programming_shared/` at the repo root (not inside `skills/`).
We follow the same convention: `_aws_shared/` is a peer of `skills/`, not a
child. This avoids the skill-directory validation contract (which requires
every `skills/*` directory to have `SKILL.md`) while making shared references
importable by any skill via relative path.

### 5. JSON Schema for frontmatter validation

`schema/SKILL.schema.json` (draft-07) validates the SKILL.md YAML frontmatter.
This is adopted directly from the reference repo's `schema/SKILL.schema.json` pattern.
The schema enforces: name pattern (lowercase-hyphens), description length
(10-1024 chars for agent activation triggers), version, keywords, tags,
dependencies, and metadata (CloudOps-specific extensions: family, phase,
verdict_shape, supports_pipeline, entry_point).

---

## File inventory

### Shared infrastructure (Phase 3 deliverables)

| Path | Purpose |
|---|---|
| `schema/SKILL.schema.json` | JSON Schema validating SKILL.md frontmatter |
| `cli/bin/cli.js` | Functional CLI: list, route, validate, status |
| `package.json` | npm manifest: name, bin, files[], keywords |
| `skills.sh.json` | skills.sh marketplace manifest with groupings[] |
| `.claude-plugin/marketplace.json` | Claude Code plugin marketplace manifest |
| `commands/aws/pipeline.md` | Slash command: enter full pipeline |
| `commands/aws/status.md` | Slash command: phase + routing summary |
| `commands/aws/help.md` | Slash command: list all commands + skills |
| `skills/aws-orchestrator/SKILL.md` | Orchestrator skill (entry point) |
| `skills/aws-orchestrator/references/pipeline-phases.md` | 4-phase routing reference |
| `skills/aws-orchestrator/references/routing-logic.md` | NL-to-skill routing logic |
| `_aws_shared/aws-service-taxonomy.md` | 12 CloudOps families, 287 services |
| `_aws_shared/common-iam-patterns.md` | Shared IAM patterns (wildcards, escalation, conditions) |
| `_aws_shared/aws-cli-reference.md` | Shared AWS CLI enumeration + remediation commands |
| `USAGE.md` | Per-skill invocation guide + pipeline walkthrough |
| `docs/architecture.md` | This document |
| `docs/skill-judge-dashboard.md` | Per-skill eval scorecard dashboard |

### Pre-existing (Phase 2 deliverables — preserved)

| Path | Purpose |
|---|---|
| `eval/run_eval.py` | Eval runner: globs skills/*/eval/*.yaml, assertions + judge |
| `eval/skill_validator.py` | Skill directory discovery + validation |
| `eval/judge_prompt.txt` | 8-dimension LLM-judge prompt template |
| `eval/scorecards/*.json` | Committed LLM-judge scorecard artifacts |
| `skills/*/SKILL.md` | Specialist skill definitions |
| `skills/*/references/*.md` | Per-skill domain reference docs |
| `skills/*/eval/test-cases.yaml` | Co-located eval test cases |
| `.github/workflows/eval.yml` | CI: assertion-only on every PR |
