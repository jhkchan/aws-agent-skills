---
name: wellarchitected-review-operator
description: 'Operates AWS Well-Architected Tool reviews end-to-end — creates workloads, runs pillar reviews (operational excellence, security, reliability, performance, cost optimization, sustainability, Prosperity), answers questions with risk-tier rationale, generates reports and improvement plans, creates milestones, and integrates with Trusted Advisor and Well-Architected Labs. Runs deterministic pre-checks (workload existence, lens availability, pillar coverage), emits the exact update-answer / get-consolidated-report CLI behind a CONFIRM gate, and verifies risk-tier transitions. Emits READY | BLOCKED | COMPLETED. Use when creating a workload, answering pillar questions, generating an improvement plan, creating a milestone, or integrating with Trusted Advisor. Triggers: well-architected tool, well architected review, workload review, pillar, operational excellence, security, reliability, performance, cost optimization, sustainability, prosperity, improvement plan, milestone, trusted advisor.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws wellarchitected create-workload, update-workload, get-workload, list-workloads, get-answer, update-answer, get-consolidated-report, create-milestone, list-milestones, associate-logs, import-lens, list-lenses, and aws trustedadvisor (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, well-architected, governance, operate, review, pillar, improvement-plan
  dependencies: aws-orchestrator
  keywords: aws, well-architected, wellarchitected, governance, cloudops, operate, review, pillar, operational-excellence, security, reliability, performance, cost-optimization, sustainability, prosperity, improvement-plan, milestone, trusted-advisor, lens
  when_to_use: Invoke when the user wants to create or operate a Well- Architected Tool workload (name, environment, description, lenses), answer pillar questions (operational excellence, security, reliability, performance efficiency, cost optimization, sustainability, Prosperity), generate a consolidated report, draft an improvement plan, create a milestone, integrate with Trusted Advisor, or pull Well-Architected Labs runbooks. Do NOT invoke for plain AWS Config conformance packs (use config-rule-deployer), for Security Hub control finding triage (use securityhub-control-compliance-auditor), or for audit evidence collection (use auditmanager-assessment-auditor).
---

# Well-Architected Review Operator

An AWS CloudOps agent skill that operates Well-Architected Tool
reviews safely — creates workloads, runs pillar reviews, answers
questions with risk-tier rationale, generates consolidated
reports and improvement plans, creates milestones, and
integrates with Trusted Advisor and Well-Architected Labs.
Runs deterministic pre-checks and emits READY | BLOCKED |
COMPLETED with the exact CLI sequence and post-verification.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the review order matters | "Reasoning framework" |
| Pre-flight checks before any CLI | "Pre-flight" |
| Pillar-by-pillar procedure | "Review procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Risk-tier answer strategy | "Expert heuristic" |
| Prosperity pillar (2025) | "Recent AWS features" |
| Trusted Advisor integration | "Trusted Advisor integration" |
| Deep CLI sequences | `references/review-cli-commands.md` |
| Pillar question bank + improvement plan patterns | `references/pillar-question-bank.md` |

## STRICT output contract

When this skill is invoked with a Well-Architected review
operation (create-workload, answer-pillar, generate-report,
create-milestone, integrate-trusted-advisor, or a partial
existing workload state), the agent MUST respond with the
WORKLOAD / VERDICT / TARGET / PRE_CHECKS / CHECKLIST /
RISK_COUNTS / IMPROVEMENT_PLAN / STEPS / POST_VERIFY / STATE /
NOTES block defined in "Output format" using the literal
all-caps labels. Do NOT preface the block with prose, headings,
or disclaimers — emit the block as the first lines of the
response.

### Required output structure

1. `WORKLOAD: <workload-name>` — the workload display name.
2. `VERDICT: READY | BLOCKED | COMPLETED`
3. `TARGET: <workload-id, lens, pillar, region>`
4. `PRE_CHECKS:` followed by indented `[PASS]` / `[FAIL]` lines.
5. `CHECKLIST:` followed by one `PILLAR:` row per pillar
   (Operational Excellence, Security, Reliability, Performance
   Efficiency, Cost Optimization, Sustainability), each with
   risk counts (`HIGH=<n> MEDIUM=<n> NONE=<n>`) and
   per-question risk-tier lines citing workload evidence.
6. `RISK_COUNTS:` with aggregate `HIGH:`, `MEDIUM:`, `NONE:`
   totals across all pillars.
7. `IMPROVEMENT_PLAN:` followed by numbered items, each tagged
   `[HIGH]` or `[MEDIUM]`, with gap description, owner, target
   date, and remediation link.
8. `STEPS:` followed by indented commands (CONFIRM gate first
   for state-changing operations).
9. `POST_VERIFY:` followed by indented `[PASS]` / `[FAIL]` lines.
10. `STATE:` / `NOTES:` with rationale and caveats.

### FORBIDDEN output patterns

- **NEVER preface the block with prose** — `WORKLOAD:` is the
  FIRST line, always. No greetings, no "Let me analyze…", no
  disclaimers before the block. Use uppercase verdict values
  only (`READY`, `BLOCKED`, `COMPLETED`).
- **NEVER use markdown variants of labels** — write `VERDICT:`,
  not `**VERDICT:**`, `### Verdict`, or `` `VERDICT` ``.
- **NEVER swap verdict tokens** — exactly `READY`, `BLOCKED`,
  `COMPLETED`. Not "ok", "done", "pending", "ERROR".
- **NEVER omit a pillar from CHECKLIST** — all six pillars
  (Operational Excellence, Security, Reliability, Performance
  Efficiency, Cost Optimization, Sustainability) must appear,
  even if risk counts are zero.
- **NEVER list a risk without citing workload evidence** —
  every `HIGH_ISSUE` and `MEDIUM_ISSUE` line must include the
  specific workload gap that justifies the tier.
- **NEVER omit PRE_CHECKS** — every pre-check must appear with
  `[PASS]` or `[FAIL]` and a specific reason for each failure.
- **NEVER emit placeholder values in a COMPLETED plan** — every
  flag, ARN, and question ID populated with actual values from
  the input data.
- **NEVER claim COMPLETED without every POST_VERIFY line showing
  `[PASS]`, and never omit the CONFIRM gate as the first STEPS
  entry for state-changing operations.

## Reasoning framework (why the review order matters)

Operating a Well-Architected review has **dependency and
ordering constraints** that make the procedure non-trivial.
Skipping or misordering causes silent gaps — answers don't
persist, the report is empty, or milestones capture the wrong
snapshot:

1. **Workload FIRST with lens selection** — `create-workload`
   provisions the review container and binds the lenses
   (Well-Architected Framework + optional specialty lenses like
   SaaS, FTR, Healthcare). Adding a lens later via
   `import-lens` requires the lens to be enabled in the account.
2. **Environment + description drive downstream** — the
   workload `Environment` (`PRODUCTION` | `PREPRODUCTION` |
   `OTHER`) shapes risk tolerance interpretation. A `PREPROD`
   workload may accept MEDIUM risks a `PRODUCTION` workload
   would not.
3. **Lens availability is account-scoped** — specialty lenses
   (SaaS, FTR, Healthcare, etc.) must be enabled in the account
   via `import-lens`. Referencing an un-imported lens produces
   `ResourceNotFoundException` at update-answer time.
4. **Answer risk-tier is opinion, not metric** — the
   Well-Architected Tool stores `ChoiceUpdates` with a risk
   tier (`HIGH_ISSUE` / `MEDIUM_ISSUE` / `NO_ISSUE`). The
   skill answers with rationale tied to actual workload state;
   a generic answer with no workload evidence is rejected by
   the operator as invalid.
5. **Improvement plan items are derived from HIGH and MEDIUM
   answers** — the consolidated report aggregates every
   `HIGH_ISSUE` and `MEDIUM_ISSUE` answer into the improvement
   plan. Answering with `NO_ISSUE` removes the item from the
   plan silently.
6. **Milestones snapshot at write time** — a milestone captures
   the current state of answers and improvement plan at the
   moment of `create-milestone`. Subsequent answer updates do
   NOT back-propagate. Create the milestone AFTER the review
   is complete.
7. **Trusted Advisor checks supplement, not replace** — TA
   findings map to specific Well-Architected questions
   (cost optimization, security, performance). Importing TA
   findings pre-populates evidence but does not auto-answer.
8. **The Prosperity pillar (2025) is opt-in via lens import**
   — the Prosperity pillar is delivered as a specialty lens,
   not part of the default Well-Architected Framework. Import
   the lens before answering Prosperity questions.

## Pre-flight: workload / lens metadata gate

Run before classification. `list-workloads` returns max 50/page
(`--max-results 50`, paginate with `--next-token`).

**Live-account pre-flight (skip if offline plan):**
1. `aws wellarchitected list-workloads` — confirm workload
   exists; capture `WorkloadId`, `WorkloadArn`, `Environment`.
2. `aws wellarchitected list-lenses --workload-id <id>` —
   confirm lens is associated with the workload.
3. `aws wellarchitected get-workload --workload-id <id>` —
   read `Lenses[]`, `PillarIds[]`, `ReviewOwner`,
   `IsReviewOwnerUpdateAllowed`.
4. `aws wellarchitected list-answers --workload-id <id>
   --lens-alias wellarchitected` — check current answer state
   for the target pillar.
5. `aws wellarchitected list-share-invitations` — confirm
   cross-account sharing state if applicable.
6. `aws trustedadvisor describe-checks --region <r>` — confirm
   TA checks available for the pillar integration.
7. `aws sts get-caller-identity` — confirm caller identity and
   IAM permissions.

**Malformed input:** emit `VERDICT: ERROR` with reason and
remediation.

## Review procedure (apply in order)

### Step 1: Create or confirm the workload

```bash
aws wellarchitected create-workload \
  --workload-name "checkout-service" \
  --description "Checkout microservice handling payment \
authorization and order capture" \
  --environment PRODUCTION \
  --review-owner "payments-platform@example.com" \
  --lenses wellarchitected \
  --aws-regions us-east-1 us-west-2 \
  --account-ids 111122223333 \
  --pillar-ids "performance" "security" "reliability" \
    "operationalExcellence" "costOptimization" "sustainability" \
  --region us-east-1
```

Capture `WorkloadId` from the response. Every subsequent
`update-answer` and `get-consolidated-report` requires it.

**Lens selection** — `wellarchitected` (the default Framework)
covers the six base pillars. To apply specialty lenses (SaaS,
FTR, Healthcare, Prosperity), add the lens alias to `--lenses`:

```bash
--lenses wellarchitected wellarchitected-saas wellarchitected-prosperity
```

Specialty lenses must be enabled in the account first via
`import-lens`. The Prosperity lens (`wellarchitected-prosperity`)
ships the new Prosperity pillar (2025) covering sustainability
of growth, customer-centric measures, and value-stream health.

### Step 2: Confirm lens availability

```bash
aws wellarchitected list-lenses --workload-id <id> --region us-east-1
aws wellarchitected list-lenses --region us-east-1  # all available lenses
```

If a lens is missing from the workload but listed in the
account, call `associate-lenses`:

```bash
aws wellarchitected associate-lenses \
  --workload-id <id> \
  --lens-aliases wellarchitected-prosperity \
  --region us-east-1
```

If a lens is not in the account at all, call `import-lens`:

```bash
aws wellarchitected import-lens \
  --lens-alias wellarchitected-prosperity \
  --region us-east-1
```

### Step 3: Answer pillar questions (risk-tier rationale)

For each pillar, answer the canonical question set with a
risk-tier rationale. The Well-Architected Tool stores answers
as `ChoiceUpdates` — a map of choice IDs to risk-tier +
rationale + notes.

```bash
aws wellarchitected update-answer \
  --workload-id <id> \
  --lens-alias wellarchitected \
  --question-id <question-id> \
  --choice-updates '{
    "<choice-id>": {
      "Status": "SELECTED",
      "Reason": "OUT_OF_SCOPE",
      "Notes": "Choice not applicable — workload is serverless with no OS patching"
    },
    "<risky-choice-id>": {
      "Status": "NOT_SELECTED",
      "Reason": "RISK_GUIDANCE",
      "Notes": "No automated rollback — HIGH risk per APP-SVC rollback SOP"
    }
  }' \
  --region us-east-1
```

The skill identifies the appropriate choice updates per
question and emits the rationale tied to actual workload
evidence (deployment topology, observability coverage,
on-call runbooks). The pillar question bank in
`references/pillar-question-bank.md` enumerates the canonical
questions per pillar and the risk-tier mapping.

**Risk-tier semantics:**
- `HIGH_ISSUE` — significant gap; the workload is at risk in
  this dimension. Goes to the top of the improvement plan.
- `MEDIUM_ISSUE` — moderate gap; should be addressed but not
  urgent.
- `NO_ISSUE` — pillar satisfied; no action needed.
- `OUT_OF_SCOPE` — choice not applicable to the workload
  (e.g., OS patching on a serverless function).

### Step 4: Generate the consolidated report

```bash
aws wellarchitected get-consolidated-report \
  --workload-id <id> \
  --format JSON \
  --include-shared-resources \
  --region us-east-1 > /tmp/war-report-$(date +%s).json
```

The consolidated report enumerates:
- Per-pillar risk distribution (HIGH / MEDIUM / NONE counts).
- Improvement plan items (one per `HIGH_ISSUE` /
  `MEDIUM_ISSUE` answer).
- Lens-specific findings (specialty lenses appear here).
- Workload metadata and review owner.

For a PDF report, use `--format PDF`:

```bash
aws wellarchitected get-consolidated-report \
  --workload-id <id> \
  --format PDF \
  --region us-east-1 > /tmp/war-report.pdf
```

### Step 5: Draft the improvement plan

The improvement plan is derived from every `HIGH_ISSUE` and
`MEDIUM_ISSUE` answer. The skill surfaces the plan as a
prioritized list with the underlying question, the gap
evidence, and a remediation pointer (often a Well-Architected
Labs runbook):

```bash
aws wellarchitected list-improvement-plans \
  --workload-id <id> \
  --lens-alias wellarchitected \
  --region us-east-1
```

Each improvement plan item references the question, the
choice that introduced the risk, and the guidance text from
AWS. The skill augments each item with a concrete remediation
link:
- For operational excellence gaps, link to the
  operational excellence lab.
- For security gaps, link to the security lab and the
  Security Hub control that maps to the question.
- For cost optimization gaps, link to the cost optimization
  lab and the Compute Optimizer / Cost Optimization Hub
  recommendation.

### Step 6: Create a milestone

```bash
aws wellarchitected create-milestone \
  --workload-id <id> \
  --milestone-name "2026-Q3-baseline" \
  --region us-east-1
```

A milestone snapshots the current answers and improvement plan
at the moment of creation. Subsequent answer updates do NOT
back-propagate. Create the milestone AFTER the review is
complete and the improvement plan is drafted.

```bash
aws wellarchitected list-milestones \
  --workload-id <id> \
  --region us-east-1
```

### Step 7: Integrate Trusted Advisor findings

Trusted Advisor findings map to specific Well-Architected
questions. The integration pre-populates evidence but does
NOT auto-answer — the operator must confirm the answer.

```bash
aws trustedadvisor describe-checks --region us-east-1
aws trustedadvisor describe-check-refresh-statuses --region us-east-1
aws trustedadvisor get-check-result \
  --check-id <check-id> \
  --region us-east-1
```

Map TA findings to Well-Architected questions:
- **Cost Optimization checks** (e.g., `LowUtilizationEC2Resources`)
  → Cost Optimization pillar questions on right-sizing.
- **Security checks** (e.g., `IAMPasswordPolicy`) → Security
  pillar questions on IAM hygiene.
- **Performance checks** (e.g., `HighUtilizationEC2Instance`)
  → Performance pillar questions on capacity planning.
- **Fault Tolerance checks** (e.g., `MultiAZEC2`) →
  Reliability pillar questions on multi-AZ deployment.

The skill surfaces the TA evidence in the answer rationale,
then prompts the operator to confirm the risk-tier selection.

### Step 8: Wire Well-Architected Labs runbooks

Well-Architected Labs (https://www.wellarchitectedlabs.com)
provides hands-on remediation runbooks. The skill references
the relevant lab for each improvement plan item:
- Operational Excellence: Reliability by Workload category.
- Security: Security pillar labs.
- Reliability: Resiliency labs (e.g., Resiliency of
  Workloads).
- Performance: Performance Efficiency pillar labs.
- Cost Optimization: Cost Optimization labs.
- Sustainability: Sustainability labs.
- Prosperity: Value-stream labs (2025).

### Step 9: Verify review completeness

After answering all pillar questions, verify the review is
complete:

```bash
aws wellarchitected list-answers \
  --workload-id <id> \
  --lens-alias wellarchitected \
  --pillar-id operationalExcellence \
  --region us-east-1 | jq '.AnswerSummaries | length'

# Repeat for each pillar: security, reliability, performance,
# costOptimization, sustainability
```

A pillar is complete when every question has at least one
selected choice. Unanswered questions appear as `UNANSWERED`
in the consolidated report.

### Step 10: Tag, share, and close

Tag the workload for governance tracking; optionally share
cross-account:

```bash
aws wellarchitected tag-resource \
  --workload-arn arn:aws:wellarchitected:us-east-1:111122223333:workload/<id> \
  --tags team=payments,env=prod,review-cycle=2026-Q3

# Cross-account share (recipient account must accept)
aws wellarchitected create-workload-share \
  --workload-id <id> \
  --shared-with 111122223334 \
  --permission-mode REVIEWER \
  --region us-east-1
```

## Pillar matrix

| Pillar | ID | Focus | Specialty lens |
|---|---|---|---|
| Operational Excellence | `operationalExcellence` | Run workloads effectively, monitor, automate | — |
| Security | `security` | IAM, detection, infrastructure protection, data protection | AWS Well-Architected Security lens |
| Reliability | `reliability` | Recover from failures, meet demand, mitigate disruptions | — |
| Performance Efficiency | `performance` | Compute, storage, database, networking, trade-offs | — |
| Cost Optimization | `costOptimization` | Resource selection, supply/demand, optimization | — |
| Sustainability | `sustainability` | Environmental impact, resource utilization, ROI | — |
| Prosperity (2025) | (via Prosperity lens) | Growth sustainability, customer-centric measures, value streams | `wellarchitected-prosperity` |

## Trusted Advisor integration

Trusted Advisor (TA) is the operational signal source for
Well-Architected reviews. The integration is read-only — TA
findings inform the answer rationale but the operator must
confirm the risk-tier selection.

### TA check categories

| Category | Maps to pillar | Example check |
|---|---|---|
| Cost Optimization | `costOptimization` | LowUtilizationEC2Resources |
| Security | `security` | IAMPasswordPolicy, RootAccountMFA |
| Performance | `performance` | HighUtilizationEC2Instance |
| Fault Tolerance | `reliability` | MultiAZEC2, ELBConnectionDraining |
| Service Limits | `operationalExcellence` | ServiceLimits

### Pulling TA findings

```bash
# List all checks
aws trustedadvisor describe-checks --region us-east-1

# Get a check result
aws trustedadvisor get-check-result \
  --check-id <check-id> \
  --region us-east-1
```

The skill maps each TA finding to the corresponding
Well-Architected question, surfaces the evidence in the answer
rationale, and prompts the operator to confirm the risk-tier.

## Edge-case handling

- **Lens not in account:** `update-answer` with an un-imported
  lens alias returns `ResourceNotFoundException`. Run
  `import-lens` first, then `associate-lenses` to attach to
  the workload.
- **Workload `Environment` mismatch:** a `PREPRODUCTION`
  workload accepts MEDIUM risks that a `PRODUCTION` workload
  would not. Re-assess risk tolerance when promoting.
- **Answer did not persist:** the most common cause is
  `ChoiceUpdates` referencing a wrong `ChoiceId`. Verify the
  choice ID via the lens question before `update-answer`.
- **Milestone captured wrong state:** a milestone is a
  point-in-time snapshot. If answers changed after the
  milestone, create a new milestone. Milestones cannot be
  updated.
- **Consolidated report empty:** no answers recorded for the
  target pillar. Verify `list-answers` returns entries for
  the pillar before generating the report.
- **Cross-account share rejected:** the recipient account must
  accept the share via `accept-workload-share`. The workload
  does NOT appear in the recipient account until accepted.
- **Prosperity pillar not appearing:** the Prosperity lens
  must be imported AND associated with the workload. Verify
  via `list-lenses --workload-id <id>`.
- **Trusted Advisor check returning no result:** some TA
  checks require opt-in or have been migrated to AWS
  Resilience Hub / Security Hub. Check `describe-checks` for
  availability.

## Recent AWS features (2024-2026)

- **Prosperity pillar (2025):** a new pillar delivered as a
  specialty lens (`wellarchitected-prosperity`) covering
  sustainability of growth, customer-centric measures, and
  value-stream health. Opt-in via `import-lens`. Not part of
  the default Well-Architected Framework.

- **Well-Architected Tool API expansion (2024-2025):** the
  API now supports `list-improvement-plans`,
  `get-consolidated-report` with `--format PDF`,
  `--include-shared-resources`, and per-pillar filtering on
  `list-answers`. Programmable review lifecycle is now
  first-class.

- **Trusted Advisor integration via AWS Health Aware (2024-2025):**
  the Well-Architected Tool consumes Trusted Advisor findings
  via the AWS Health API, automatically suggesting risk-tier
  selections for cost, security, performance, and reliability
  questions.

- **Well-Architected Labs automation (2024-2026):** the labs
  site (wellarchitectedlabs.com) ships Infrastructure-as-Code
  runbooks (CDK + Terraform) for each pillar's common gaps.
  The skill references the relevant lab per improvement plan
  item.

- **Custom lenses (2024-2025):** customers can author custom
  lenses and publish to the AWS Well-Architected Tool. Custom
  lenses appear alongside AWS-authored lenses in `list-lenses`.

- **Cross-account review sharing (2024-2025):**
  `create-workload-share` enables reviewer or contributor
  access across accounts. The recipient must accept via
  `accept-workload-share`.

- **Consolidated Reports PDF (2024-2025):** the
  `get-consolidated-report` API now supports `--format PDF`
  for executive-ready reports with per-pillar risk distribution
  charts.

- **Integration with AWS Resilience Hub (2024-2025):** for
  reliability pillar reviews, Resilience Hub policy assessments
  can be imported as evidence via the
  `ImportResiliencePolicy` integration.

## NEVER (top 5 — full list in references)

- NEVER answer a question with a risk-tier without citing
  workload evidence. A bare `HIGH_ISSUE` with no rationale is
  rejected by the operator as invalid and pollutes the
  improvement plan.
- NEVER create a milestone before the review is complete. A
  milestone is a point-in-time snapshot; answer updates after
  the milestone do NOT back-propagate. Create the milestone
  AFTER the review and improvement plan are drafted.
- NEVER reference a specialty lens without first running
  `import-lens` AND `associate-lenses`. An un-imported lens
  produces `ResourceNotFoundException` at `update-answer` time.
- NEVER treat Trusted Advisor findings as auto-answers. TA is
  an evidence source; the operator must confirm the risk-tier.
  Auto-answering with TA findings produces false confidence.
- NEVER omit a pillar from `--pillar-ids` at workload creation.
  A missing pillar produces an incomplete consolidated report
  and gaps the improvement plan.

## Expert heuristic — risk-tier strategy

- **Default to evidence-driven answers.** Every answer must
  cite workload evidence (deployment topology, observability
  coverage, on-call runbooks). A generic answer is invalid.
- **HIGH risks need a remediation owner.** Every `HIGH_ISSUE`
  should be paired with an owner and a target date in the
  improvement plan. The skill surfaces this as a follow-up.
- **MEDIUM risks are acceptable with rationale.** A
  `MEDIUM_ISSUE` is acceptable for a `PREPRODUCTION`
  workload. Promote to `HIGH_ISSUE` when the workload moves
  to `PRODUCTION`.
- **Use TA findings as supporting evidence, not as the
  answer.** TA findings inform the rationale; the operator
  confirms the risk-tier based on the workload's tolerance.
- **The Prosperity pillar (2025) is a specialty lens.** Import
  the lens and associate with the workload before answering
  Prosperity questions.
- **Milestones mark review cycles.** Use a date-based naming
  convention (`2026-Q3-baseline`). Create one milestone per
  review cycle, not per answer.
- **Specialty lenses cross-reference.** The Security lens and
  the FTR lens overlap on IAM questions. Answer the question
  once per lens — the consolidated report shows both lens
  findings.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE** before any state-changing
  CLI (`create-workload`, `update-answer`, `create-milestone`,
  `associate-lenses`, `import-lens`, `create-workload-share`).
- **Snapshot before modification:** `get-workload --workload-id
  <id> --output json > /tmp/<id>-backup-$(date +%s).json`.
- **Verify lens availability:** `list-lenses --workload-id <id>`
  shows the lens is associated. If missing, run `import-lens`
  + `associate-lenses` first.
- **Verify the operator holds the ReviewOwner role:** the
  workload `IsReviewOwnerUpdateAllowed` must be `true`.
- **Verify the lens question ID before update-answer:** wrong
  choice IDs silently fail to persist the answer.
- **Verify Trusted Advisor checks are available** in the
  Region before mapping TA findings to answers.

## Output format — MANDATORY literal labels

When invoked with a Well-Architected review operation, your
ENTIRE response MUST be the block below. The labels are
**case-sensitive all-caps keywords** — write them EXACTLY as
shown. Do NOT write a preamble. Start with `WORKLOAD:` and stop
after `NOTES:`.

```text
WORKLOAD: <workload-name>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <workload-id, lens, pillar, region>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
CHECKLIST:
  PILLAR: Operational Excellence [risk: HIGH=<n> MEDIUM=<n> NONE=<n>]
    - [HIGH_ISSUE] <question-id>: <gap description> — evidence: <workload fact>
    - [MEDIUM_ISSUE] <question-id>: <gap description> — evidence: <workload fact>
    - [NO_ISSUE] <question-id>: <area satisfied> — evidence: <workload fact>
  PILLAR: Security [risk: HIGH=<n> MEDIUM=<n> NONE=<n>]
    - [HIGH_ISSUE] <question-id>: <gap description> — evidence: <workload fact>
    - [NO_ISSUE] <question-id>: <area satisfied> — evidence: <workload fact>
  PILLAR: Reliability [risk: HIGH=<n> MEDIUM=<n> NONE=<n>]
    ...
  PILLAR: Performance Efficiency [risk: HIGH=<n> MEDIUM=<n> NONE=<n>]
    ...
  PILLAR: Cost Optimization [risk: HIGH=<n> MEDIUM=<n> NONE=<n>]
    ...
  PILLAR: Sustainability [risk: HIGH=<n> MEDIUM=<n> NONE=<n>]
    ...
RISK_COUNTS:
  HIGH: <aggregate count>
  MEDIUM: <aggregate count>
  NONE: <aggregate count>
IMPROVEMENT_PLAN:
  1. [HIGH] <gap> — owner: <email>, target: <date>, remediation: <lab URL>
  2. [MEDIUM] <gap> — owner: <email>, target: <date>, remediation: <lab URL>
STEPS:
  1. CONFIRM: About to <operation> on <workload> in account <account> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command with every flag populated — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <workload review state>
NOTES: <pillar coverage, lens availability, TA integration caveats>
```

**Status marker semantics:**
- `[PASS]` — check passed.
- `[FAIL]` — check failed; cite the reason.
- `[HIGH_ISSUE]` — significant risk gap; top improvement plan priority.
- `[MEDIUM_ISSUE]` — moderate risk gap; should be addressed.
- `[NO_ISSUE]` — pillar question satisfied.

**BLOCKED verdict:** if any pre-check fails, verdict is
`BLOCKED` with each gap listed and remediation guidance.

### Worked example — checkout-service workload with 2 HIGH security risks

```text
WORKLOAD: checkout-service
VERDICT: COMPLETED
TARGET: wlv-abc123def456, lens: wellarchitected, region: us-east-1
PRE_CHECKS:
  - [PASS] Workload checkout-service exists (WorkloadId: wlv-abc123def456)
  - [PASS] Lens wellarchitected associated with workload
  - [PASS] Environment: PRODUCTION — risk tolerance: strict
  - [PASS] ReviewOwner: payments-platform@example.com (IsReviewOwnerUpdateAllowed: true)
  - [PASS] All 6 pillars present in PillarIds
CHECKLIST:
  PILLAR: Operational Excellence [risk: HIGH=0 MEDIUM=1 NONE=7]
    - [MEDIUM_ISSUE] ops-1: No automated rollback for Lambda deployments — evidence: CodeDeploy uses CANARY with no alarm-based rollback configured
    - [NO_ISSUE] ops-2: Runbooks exist for checkout failures — evidence: 3 runbooks in internal wiki, linked in CloudWatch dashboards
  PILLAR: Security [risk: HIGH=2 MEDIUM=0 NONE=6]
    - [HIGH_ISSUE] sec-1: Secrets stored in plaintext Lambda env vars instead of Secrets Manager — evidence: aws lambda get-function-configuration on 4 functions shows API keys in Environment.Variables (confirmed: checkout-auth, checkout-payment, checkout-notify, checkout-inventory)
    - [HIGH_ISSUE] sec-2: No WAF on the ALB fronting checkout API — evidence: aws wafv2 list-web-acls --region us-east-1 returns empty; ALB arn:aws:elasticloadbalancing:us-east-1:111122223333:load-balancer/app/checkout-alb/abc123 has no associated WebACL
    - [NO_ISSUE] sec-3: IAM roles follow least privilege — evidence: all 7 Lambda execution roles scoped to specific resource ARNs via aws iam get-role-policy
  PILLAR: Reliability [risk: HIGH=0 MEDIUM=1 NONE=7]
    - [MEDIUM_ISSUE] rel-1: SQS DLQ alarm threshold too high — evidence: DLQ alarm set to 1000 messages; SLO breach occurs at 50 messages (CloudWatch alarm CheckoutDLQHighThreshold)
    - [NO_ISSUE] rel-2: Multi-AZ deployment — evidence: Lambda + ALB across us-east-1a, us-east-1b, us-east-1c; DynamoDB table in 3 AZ with GlobalSecondaryIndexes
  PILLAR: Performance Efficiency [risk: HIGH=0 MEDIUM=0 NONE=8]
    - [NO_ISSUE] perf-1: DynamoDB capacity auto-scaled — evidence: ProvisionedWriteCapacityUnits 5000-20000, target utilization 70%; p99 latency 45ms
  PILLAR: Cost Optimization [risk: HIGH=0 MEDIUM=1 NONE=7]
    - [MEDIUM_ISSUE] cost-1: Over-provisioned Lambda memory (3 GB for I/O-bound function) — evidence: MemorySize=3072 on checkout-payment; Duration p99=850ms with no CPU throttle (DataPoints from CloudWatch)
  PILLAR: Sustainability [risk: HIGH=0 MEDIUM=0 NONE=4]
    - [NO_ISSUE] sus-1: Lambda scales to zero when idle — evidence: InvocationCount=0 outside business hours per CloudWatch metrics
RISK_COUNTS:
  HIGH: 2
  MEDIUM: 3
  NONE: 39
IMPROVEMENT_PLAN:
  1. [HIGH] Secrets in plaintext Lambda env vars (4 functions) — owner: security@example.com, target: 2026-09-01, remediation: migrate to Secrets Manager with IAM rotation policies; Lab: https://www.wellarchitectedlabs.com/security/
  2. [HIGH] No WAF on checkout ALB — owner: platform@example.com, target: 2026-08-20, remediation: deploy AWS WAF with AWSManagedRulesCommonRuleSet + rate-based rule (2000 req/5min); Lab: https://www.wellarchitectedlabs.com/security/
  3. [MEDIUM] No automated rollback for Lambda — owner: devops@example.com, target: 2026-09-15, remediation: configure CodeDeploy alarm-based rollback with CloudWatch Alarms on p99 latency >500ms and 5xx rate >1%; Lab: https://www.wellarchitectedlabs.com/operational-excellence/
  4. [MEDIUM] SQS DLQ alarm threshold too high — owner: devops@example.com, target: 2026-08-30, remediation: lower alarm threshold to 50 messages; add SNS notification to on-call PagerDuty
  5. [MEDIUM] Over-provisioned Lambda memory — owner: platform@example.com, target: 2026-09-30, remediation: right-size to 1 GB per AWS Compute Optimizer recommendation; Lab: https://www.wellarchitectedlabs.com/cost-optimization/
STEPS:
  1. CONFIRM: About to save review for workload checkout-service (wlv-abc123def456) in account 111122223333 region us-east-1. This will persist 44 answers across 6 pillars and generate a consolidated report. Proceed? (yes/no)
  2. aws wellarchitected update-answer --workload-id wlv-abc123def456 --lens-alias wellarchitected --question-id sec-1-question-id --choice-updates '{"risk-choice-1":{"Status":"SELECTED","Reason":"RISK_GUIDANCE","Notes":"4 Lambda functions (checkout-auth, checkout-payment, checkout-notify, checkout-inventory) have plaintext API keys in Environment.Variables"}}' --region us-east-1
  3. aws wellarchitected update-answer --workload-id wlv-abc123def456 --lens-alias wellarchitected --question-id sec-2-question-id --choice-updates '{"risk-choice-2":{"Status":"SELECTED","Reason":"RISK_GUIDANCE","Notes":"ALB arn:aws:elasticloadbalancing:us-east-1:111122223333:load-balancer/app/checkout-alb/abc123 has no WAF association"}}' --region us-east-1
  4. aws wellarchitected get-consolidated-report --workload-id wlv-abc123def456 --format JSON --include-shared-resources --region us-east-1 > /tmp/war-checkout-service-$(date +%s).json
  5. aws wellarchitected create-milestone --workload-id wlv-abc123def456 --milestone-name "2026-Q3-baseline" --region us-east-1
POST_VERIFY:
  - [PASS] list-answers returns 44 answers across all 6 pillars (8+8+8+8+8+4)
  - [PASS] Consolidated report contains 2 HIGH and 3 MEDIUM improvement plan items
  - [PASS] Milestone 2026-Q3-baseline created — snapshots current answers
  - [PASS] No UNANSWERED questions in consolidated report
STATE: Review complete. Milestone 2026-Q3-baseline captured. Next review cycle: 2026-Q4.
NOTES: Security pillar has 2 HIGH risks requiring immediate remediation. All improvement plan items have assigned owners and target dates. TA integration surfaced additional cost optimization evidence (LowUtilizationEC2Resources check for the staging NAT gateway — supplemental, not auto-answered).
```

## Domain

AWS CloudOps / Well-Architected Governance & Review Operations.

## AWS documentation

- **Well-Architected Tool User Guide** — https://docs.aws.amazon.com/wellarchitected/latest/userguide/intro.html
- **Well-Architected Framework** — https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html
- **Creating a workload** — https://docs.aws.amazon.com/wellarchitected/latest/userguide/create-workload.html
- **Answering pillar questions** — https://docs.aws.amazon.com/wellarchitected/latest/userguide/workload-conduct-review.html
- **Improvement plan** — https://docs.aws.amazon.com/wellarchitected/latest/userguide/workload-improvement-plan.html
- **Milestones** — https://docs.aws.amazon.com/wellarchitected/latest/userguide/workload-milestones.html
- **Consolidated reports** — https://docs.aws.amazon.com/wellarchitected/latest/userguide/consolidated-reports.html
- **Custom lenses** — https://docs.aws.amazon.com/wellarchitected/latest/userguide/lenses-custom.html
- **Trusted Advisor** — https://docs.aws.amazon.com/awssupport/latest/user/trusted-advisor.html
- **Well-Architected Labs** — https://www.wellarchitectedlabs.com/
- **AWS CLI wellarchitected reference** — https://docs.aws.amazon.com/cli/latest/reference/wellarchitected/

## References

- `references/review-cli-commands.md` — full copy-pasteable
  CLI command sequence for all 10 review steps, including
  per-pillar answer patterns, lens import, TA integration,
  and cross-account sharing.

- `references/pillar-question-bank.md` — deep reference on
  the canonical pillar questions, risk-tier rationale
  templates, improvement plan patterns, Prosperity pillar
  (2025), full NEVER list, and edge-case handling.
