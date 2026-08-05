---
name: wellarchitected-workload-auditor
description: >-
  Audits AWS Well-Architected Tool workloads for review staleness, per-pillar
  high-risk issue counts, milestone tracking gaps, and remediation plan
  completeness. Emits a deterministic verdict (STALE_REVIEW | HIGH_RISK |
  CONFIG_GAP | OK) per workload with per-pillar risk breakdown, milestone
  trend analysis, and specific remediation. Use when reviewing Well-Architected
  workloads, checking WA review freshness, auditing high-risk issues per
  pillar, validating milestone coverage, or tracking remediation plans.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline workload-document classification.
  Live-account audits use aws wellarchitected describe-workload,
  list-milestones, list-answers, and list-workload-shares (AWS CLI v2, SSO
  or key-based credentials).
keywords:
  - Well-Architected Tool
  - workload review
  - staleness
  - high-risk issues
  - pillar risk
  - milestone tracking
  - remediation plan
  - Well-Architected Framework
  - risk counts
  - lens audit
  - workload auditor
  - WA review
  - improvement plan
  - UNANSWERED
  - review freshness
  - RiskCounts
tags: [wellarchitected, governance, review-audit, risk-assessment, milestones, remediation, compliance]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Governance
  verdict_shape: "STALE_REVIEW | HIGH_RISK | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a Well-Architected Tool workload for staleness or freshness,
    auditing high-risk issues per pillar, checking milestone coverage, tracking
    remediation plan progress, validating lens coverage, or preparing a
    workload for a compliance gate or executive review.
  trigger_regex: '(?i)(well[-\s]?architected|WA[-\s]?(?:tool|review|workload)|pillar[-\s]?risk|review[-\s]?(?:stale|fresh)|milestone[-\s]?track|remediation[-\s]?plan|RiskCounts|list-answers|describe-workload)'
---

# Well-Architected Workload Auditor

## Mindset

**One-line takeaway:** STALE_REVIEW always wins over HIGH_RISK because a stale
review invalidates the entire risk picture — a 200-day-old HIGH_RISK finding
may already be remediated in the live infrastructure, and the review gives you
no way to tell.

The Well-Architected Tool captures a **point-in-time human assessment**, not
live state. A reviewer answers questions per pillar, the tool computes risk
levels, and milestones snapshot the review at intervals. The audit evaluates
four dimensions in strict priority order: freshness, risk severity,
configuration completeness, healthy. The first dimension that trips
determines the verdict — do not evaluate later dimensions after a trip,
because they operate on potentially unreliable data.

**Three rules govern every verdict (memorize before proceeding):**
1. **Priority:** STALE_REVIEW > HIGH_RISK > CONFIG_GAP > OK — first trip wins.
2. **Security is zero-tolerance:** `security.HIGH_RISK > 0` triggers HIGH_RISK
   immediately. Other pillars need **total** HIGH_RISK `> 5`. Never flatten
   this to a single threshold across all pillars.
3. **`effectiveReviewDate` = max(`LastUpdated`, most-recent milestone
   `RecordedAt`).** Never use `LastUpdated` alone — it tracks metadata edits,
   not review progression.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| `effectiveReviewDate` > 180 days from today | **STALE_REVIEW** | 1b |
| No milestones AND `LastUpdated` > 90 days | **STALE_REVIEW** | 1c |
| `UNANSWERED` count / total questions > 50% | **STALE_REVIEW** | 1d |
| Per-pillar `security.HIGH_RISK` > 0 | **HIGH_RISK** | 2a |
| Total `HIGH_RISK` across all pillars > 5 | **HIGH_RISK** | 2b |
| No milestones ever created | **CONFIG_GAP** | 3a |
| `Lenses` contains only `wellarchitected` (no additional) | **CONFIG_GAP** | 3b |
| `Environment` field empty or null | **CONFIG_GAP** | 3c |
| All above checks pass | **OK** | 4 |

`effectiveReviewDate` = max(`LastUpdated`, most-recent milestone `RecordedAt`).
If no milestones exist, `effectiveReviewDate` = `LastUpdated`.

## Pre-flight: workload metadata context (run before classification)

- **`Environment`**: `PRODUCTION` → HIGH_RISK findings carry maximum urgency.
  `PREPRODUCTION` → lower urgency. Empty/null → flag as CONFIG_GAP (Step 3c);
  risk tolerance cannot be determined.
- **`Lenses`**: Custom lens ARNs expand scope with additional questions beyond
  the six standard pillars. Only `["wellarchitected"]` → CONFIG_GAP (Step 3b).
- **`IsReviewOwner`**: If `false`, recommendations target the `ReviewOwner`,
  not the caller.
- **Share `PermissionType`**: `CONTRIBUTOR` grants write access — a shared
  contributor can resolve HIGH_RISK issues without infrastructure changes.
  Audit the contributor list.

**If the workload data is malformed** (missing `WorkloadId`, no `RiskCounts`,
unparseable dates), output:

```text
WORKLOAD: <workload-name or id>
VERDICT: ERROR
REASON: Workload data is incomplete or malformed — cannot classify.
REMEDIATION: Re-fetch with aws wellarchitected describe-workload --workload-id <id> and re-audit.
```

**Date-specific malforming:** `LastUpdated` or `RecordedAt` may arrive as
ISO-8601 (`2026-01-10T08:00:00Z`), date-only (`2026-01-10`), or epoch.
Parse in that order of preference. If a date is null, empty, or cannot be
parsed by any format, do NOT guess or default to today — output the ERROR
verdict above and instruct the operator to re-fetch. A guessed date
produces a false STALE_REVIEW or false OK, both of which are worse than an
explicit error.

## Process — Classification logic (apply in order, first trip wins)

### Step 0: Critical behaviors that change classification (read before Step 1)

- **`effectiveReviewDate` uses milestones, not just `LastUpdated`.** A
  workload's `LastUpdated` reflects metadata edits (name, description, lenses).
  Milestone `RecordedAt` reflects review-answer progression. Always use
  `max(LastUpdated, most-recent milestone.RecordedAt)` for staleness.

- **`RiskCounts` at the workload level is an aggregate across ALL pillars.**
  The `describe-workload` API returns a single `RiskCounts` map — it does NOT
  break down by pillar. You must call `list-answers --pillar-id <pillar>` per
  pillar and aggregate client-side to know whether HIGH_RISK issues are in
  `security` (urgent) or `costOptimization` (less urgent).

- **Security pillar is zero-tolerance.** One HIGH_RISK in `security` is more
  dangerous than five in `costOptimization` — security risks are exploitable
  attack vectors. Rule 2a triggers on `security.HIGH_RISK > 0`; other pillars
  need total > 5.

- **`UNANSWERED > 50%` means the review was abandoned.** The operator may
  have answered easy questions and skipped hard ones, producing a falsely
  optimistic risk picture. Classify as STALE_REVIEW — the data is not
  trustworthy enough to evaluate HIGH_RISK or CONFIG_GAP.

> Additional non-obvious WA Tool internals (milestone immutability, lens
> versioning, improvement-plan composition, Trusted Advisor check-summaries,
> API parameter requirements) are in the **Deep Reference** section at the
> end of this document.

### Step 0.5: Live-data acquisition (for live-account audits only)

If reading from the AWS API (not offline documents), drain pagination and
handle throttling before classifying:

1. **`list-workloads` / `list-milestones`:** loop `--next-token` until empty
   (both cap at 50/page). The long tail is where stale reviews hide.
2. **`list-answers`:** call once per pillar (6 calls), each with
   `--pillar-id`. Each may paginate — drain `NextToken`.
3. **Throttling:** `ThrottlingException` is expected under load. Retry with
   exponential backoff: 1s → 2s → 4s → 8s → 16s, max 5 retries. The
   Well-Architected Tool shares account-level API quotas — aggressive retries
   exhaust the bucket.
4. **Malformed dates:** if `LastUpdated` or `RecordedAt` is unparseable or
   missing, output `VERDICT: ERROR` (see malformed-data block in Pre-flight)
   and halt — do not guess a date.

### Step 1: Staleness check (STALE_REVIEW) — highest priority

A stale review invalidates every risk finding. Evaluate freshness before any
risk or configuration dimension.

**1a. Compute `effectiveReviewDate`:**
- If milestones exist: `effectiveReviewDate = max(LastUpdated, max(all milestone.RecordedAt))`
- If no milestones exist: `effectiveReviewDate = LastUpdated`

**1b.** If `effectiveReviewDate` is **more than 180 days** from today →
**STALE_REVIEW**. The review is stale enough that risk data is unreliable.
Stop — do not evaluate HIGH_RISK or CONFIG_GAP on stale data.

**1c.** If **no milestones exist** AND `LastUpdated` is **more than 90 days**
from today → **STALE_REVIEW**. A workload with no milestones for 90+ days
has no review discipline — the operator started the review and never
returned.

**1d.** If `UNANSWERED` count / total questions is **greater than 50%** →
**STALE_REVIEW**. The review was abandoned mid-way. The answered subset
is not representative of the workload's actual posture.

**1e. Corroboration via check-summaries (if available):** If
`list-check-summaries` returns failing checks, this strengthens a
STALE_REVIEW verdict — automated checks detect divergence between review
answers and live infrastructure. Note: an empty check-summary result means
no AppRegistry association exists (cross-check not connected), which is
neutral — do not treat it as all-passing.

**Rationale for precedence:** a 200-day-old HIGH_RISK in the Security pillar
may have been fixed months ago via an infrastructure change that was never
reflected back into the WA review. Acting on stale HIGH_RISK findings
wastes remediation effort on issues that may not exist.

### Step 2: High-risk check (HIGH_RISK)

Only evaluate if staleness checks (Step 1) did not trip.

**2a.** If per-pillar `security.HIGH_RISK` count is **greater than 0** →
**HIGH_RISK**. Security pillar risk is zero-tolerance. Even one unmitigated
security risk is an exploitable attack surface.

**2b.** If total `HIGH_RISK` count across **all six pillars** is **greater
than 5** → **HIGH_RISK**. An aggregate threshold catches workloads where
risk is spread across non-security pillars (reliability, performance, cost)
but the total volume indicates systemic architectural gaps.

**Security-weighting rationale:** `security.HIGH_RISK = 1` triggers
HIGH_RISK via rule 2a. `security.HIGH_RISK = 0` but total > 5 triggers via
rule 2b. A workload with `security.HIGH_RISK = 0` and total = 4 does NOT
trigger — 4 non-security HIGH_RISK issues are concerning but not
verdict-level without the security dimension.

**Tie-breaking when both 2a and 2b trip:** if `security.HIGH_RISK > 0` AND
total > 5, the verdict is still HIGH_RISK (only one verdict per workload).
Cite rule 2a (security) as the primary REASON — it is the more urgent
trigger. Enumerate the non-security HIGH_RISK findings in FINDINGS but do
not change the verdict.

**Lens-version caveat:** if the lens was upgraded since the review, risk
levels may have shifted without any architectural change. Compare
`LensVersion` from `list-answers` against the current published version. If
they differ, note it in FINDINGS — the HIGH_RISK count may be inflated or
deflated by the version gap.

### Step 3: Configuration gap check (CONFIG_GAP)

Only evaluate if staleness (Step 1) and high-risk (Step 2) did not trip.

**3a.** If **no milestones have ever been created** → **CONFIG_GAP**. Without
milestones, there is no historical audit trail — the operator cannot compare
risk over time or demonstrate remediation progress to auditors.

**3b.** If `Lenses` contains **only `["wellarchitected"]`** (the default
Framework lens) and no additional lenses → **CONFIG_GAP**. The workload has
no specialized guidance (Security lens, Reliability lens, custom lenses)
applied. Additional lenses add pillar-specific best-practice questions that
the default Framework lens does not cover in depth.

**3c.** If `Environment` is **empty or null** → **CONFIG_GAP**. The
environment classification (PRODUCTION vs PREPRODUCTION) drives risk
tolerance and remediation urgency. An unset environment means the review
cannot be triaged relative to other workloads.

### Step 4: OK

If none of Steps 1-3 tripped, the workload verdict is **OK**: the review is
fresh, no security-critical HIGH_RISK issues exist, total HIGH_RISK is within
tolerance, milestones are tracked, lenses are applied, and the environment
is classified.

### Step 5: Aggregation

The final verdict is the **first step that tripped**, in priority order
STALE_REVIEW > HIGH_RISK > CONFIG_GAP > OK. Do not report a lower-priority
verdict if a higher-priority step tripped — but DO enumerate all findings
from all evaluated steps in the FINDINGS list.

## Output format (per workload)

```text
WORKLOAD: <workload-name> (<workload-id>)
VERDICT: STALE_REVIEW | HIGH_RISK | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [STALE_REVIEW] <description (Step Nb)>
  - [HIGH_RISK] <description (Step Na)>
  - [CONFIG_GAP] <description (Step Nc)>
  - [OK] <dimensions that passed>
PILLAR_RISK:
  - security: HIGH=<n> MED=<n> NONE=<n> UNANSWERED=<n>
  - reliability: HIGH=<n> MED=<n> NONE=<n> UNANSWERED=<n>
  - performance: HIGH=<n> MED=<n> NONE=<n> UNANSWERED=<n>
  - costOptimization: HIGH=<n> MED=<n> NONE=<n> UNANSWERED=<n>
  - operationalExcellence: HIGH=<n> MED=<n> NONE=<n> UNANSWERED=<n>
  - sustainability: HIGH=<n> MED=<n> NONE=<n> UNANSWERED=<n>
MILESTONES: <count>, latest: <date> (<n> days ago)
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — stale review with compounding high-risk

```text
WORKLOAD: payments-api-prod (abc123def4567890abc123def4567890)
VERDICT: STALE_REVIEW
REASON: effectiveReviewDate is 207 days old (Step 1b) — the review is stale
and the underlying HIGH_RISK findings cannot be trusted as current.
FINDINGS:
  - [STALE_REVIEW] effectiveReviewDate 2026-01-10 is 207 days ago (> 180) (Step 1b)
  - [HIGH_RISK] Security pillar has 2 HIGH_RISK issues — noted but unverified due to staleness (Step 2a)
PILLAR_RISK:
  - security: HIGH=2 MED=1 NONE=3 UNANSWERED=0
  - reliability: HIGH=1 MED=2 NONE=2 UNANSWERED=0
  - performance: HIGH=0 MED=1 NONE=4 UNANSWERED=0
  - costOptimization: HIGH=0 MED=1 NONE=3 UNANSWERED=0
  - operationalExcellence: HIGH=0 MED=0 NONE=4 UNANSWERED=2
  - sustainability: HIGH=0 MED=0 NONE=1 UNANSWERED=0
MILESTONES: 1, latest: 2026-01-10 (207 days ago)
REMEDIATION:
  1. Re-run the review: update answers to reflect current architecture.
     aws wellarchitected list-answers --workload-id abc123def4567890abc123def4567890
     --pillar-id security --profile <p>
  2. Create a milestone after the review update to snapshot the new state.
  3. Re-audit after the review is current — the HIGH_RISK findings may no longer apply.
```

## Anti-Patterns — NEVER

- NEVER classify a workload as HIGH_RISK when `effectiveReviewDate` is > 180
  days. The risk data is stale — a HIGH_RISK finding from 200 days ago may
  already be remediated. Staleness takes precedence. Reporting HIGH_RISK on
  stale data creates alert fatigue and wastes remediation effort on phantom
  issues.

- NEVER use `LastUpdated` alone for staleness without checking milestones.
  `LastUpdated` reflects metadata edits (renaming the workload, adding a
  lens), not review-answer progression. A workload renamed yesterday but
  last reviewed 300 days ago is stale. Use `effectiveReviewDate` = max of
  `LastUpdated` and the most recent milestone `RecordedAt`.

- NEVER evaluate HIGH_RISK or CONFIG_GAP when `UNANSWERED > 50%`. An
  incomplete review produces a falsely optimistic risk picture — the
  unanswered questions may hide HIGH_RISK issues. Classify as STALE_REVIEW.

- NEVER treat the aggregate `RiskCounts` as sufficient for the audit. A
  workload with `RiskCounts.HIGH_RISK = 3` does not tell you whether those 3
  issues are in Security (urgent) or Cost Optimization (lower urgency). You
  MUST drill into per-pillar data via `list-answers --pillar-id <pillar>`.

- NEVER set the HIGH_RISK threshold the same for all pillars. Security is
  zero-tolerance (`> 0` triggers). Other pillars use the aggregate `> 5`
  threshold. A flat "any pillar > 3" rule misses the security-weighting
  principle and produces false negatives on security-critical workloads.

- NEVER assume `ImprovementPlan` items equal remediated issues. Improvement
  plan items are committed actions, not completed fixes. An improvement plan
  with 10 items means 10 things were planned — it says nothing about whether
  any were executed. Check milestone-to-milestone risk-count trends to verify
  actual remediation.

- NEVER ignore the `Environment` field. A PRODUCTION workload with HIGH_RISK
  issues is an active risk requiring immediate remediation. A PREPRODUCTION
  workload with the same issues is a planning concern. Conflating the two
  leads to over-triaging test environments and under-triaging production.

- NEVER skip milestone trend analysis. A workload where HIGH_RISK went from
  8 to 2 between the last two milestones is trending positive — the
  remediation plan is working. A workload where HIGH_RISK went from 1 to 5
  is regressing. The verdict captures the current state, but the trend
  provides the action signal.

- NEVER recommend deleting a workload review without confirming it is not
  referenced by compliance reports or executive dashboards. Workload
  deletion is irreversible — the entire review history, milestones, and
  improvement plan are permanently lost.

- NEVER assume a workload shared cross-account is read-only. `PermissionType:
  CONTRIBUTOR` grants write access to the shared party. A contributor can
  mark HIGH_RISK issues as resolved without any infrastructure change. Audit
  the contributor list and restrict shares to `READ` unless active
  collaboration is intended.

- NEVER call `list-answers` without `--pillar-id`. The API requires it —
  omitting it returns an error, not all answers. You must iterate all six
  pillars individually.

- NEVER retry a throttled WA Tool API call without exponential backoff. The
  Well-Architected Tool shares account-level API quotas — hammering retries
  exhausts the bucket and prolongs the `ThrottlingException` window. Use
  1s → 2s → 4s → 8s → 16s backoff, max 5 retries, then surface the error.

- NEVER use `list-workloads` first-page results for an account-wide audit.
  The API caps at 50 per page. The workloads most likely to be stale or
  abandoned are in the long tail (created early, never revisited). Always
  drain `NextToken`.

- NEVER ignore `list-check-summaries` results when they are present. Failing
  checks mean the review answers diverge from the live infrastructure — a
  stronger staleness signal than date arithmetic alone. An empty
  check-summary (no association) is different from all-passing; do not
  conflate them.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (updating answers, creating milestones, sharing/unsharing a workload,
  deleting a workload), the auditor MUST emit:
  `CONFIRM: About to <action> on workload <id>. This affects <consequence>.
  Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **Snapshot before answer updates.** Before modifying review answers
  (e.g., resolving a HIGH_RISK issue), create a milestone to capture the
  current state:
  `aws wellarchitected create-milestone --workload-id <id> --milestone-name "Pre-remediation snapshot <date>"`
  Milestones are immutable — they are the only rollback reference for review
  state.

- **Verify the caller is the review owner.** Most auditor roles have
  read-only access (`wellarchitected:Get*`, `wellarchitected:List*`). Answer
  updates require `wellarchitected:UpdateAnswer` — verify the caller's
  permissions via `aws iam get-user --query 'User.UserName'` and check
  the attached policy for `wellarchitected:Update*` actions before proposing
  remediation commands. Surface `AccessDenied` proactively.

- **Lens removal is destructive.** Removing a lens from a workload deletes
  all answers associated with that lens's questions. Always create a
  milestone before removing a lens. Prefer adding lenses over removing them.

- **Workload deletion is irreversible.** `delete-workload` permanently
  removes the workload, all milestones, all answers, and all improvement
  plan items. There is no undo. Never recommend deletion without explicit
  operator confirmation and a final milestone export.

- **Timeout + rollback for failed CLI commands.** If a remediation CLI call
  (`update-answer`, `associate-lenses`) times out or returns a
  non-recoverable error, do NOT retry blindly. Re-run `describe-workload` to
  verify the actual state before retrying. If an answer update partially
  succeeded, restore prior `SelectedChoices` from the pre-remediation
  milestone's `WorkloadSummary` — milestones are the only rollback
  reference.

## Remediation guidance

### For STALE_REVIEW

1. **Re-run the review.** The current answers may not reflect the live
   architecture. Walk through each pillar's questions and update answers:
   `aws wellarchitected list-answers --workload-id <id> --pillar-id security`
2. **Create a milestone after the review update** to snapshot the new state:
   `aws wellarchitected create-milestone --workload-id <id> --milestone-name "Q-review <date>"`
3. **Re-audit after the review is current.** The HIGH_RISK findings from the
   stale review may no longer apply — verify against the updated answers
   before allocating remediation effort.
4. **Set a recurring review cadence.** AWS recommends reviewing each workload
   at least every 6 months. Use EventBridge Scheduler to remind the review
   owner. A workload untouched for > 180 days will trip STALE_REVIEW again.
5. **For UNANSWERED > 50%:** prioritize completing the unanswered questions.
   Use `list-answers --pillar-id <pillar>` to identify which pillars have the
   most unanswered questions and address them first.

### For HIGH_RISK

1. **Security pillar first (rule 2a).** Any `security.HIGH_RISK > 0` is an
   active exploit surface. Review each HIGH_RISK answer, identify the
   architectural gap, and create an improvement plan item:
   `aws wellarchitected update-answer --workload-id <id> --pillar-id security --question-id <qid> --selected-choices <better-choices>`
2. **Aggregate > 5 (rule 2b).** When HIGH_RISK is spread across non-security
   pillars, prioritize by pillar priority order. The `PillarPriorities` field
   on the workload indicates which pillars the team considers most critical.
3. **Create a milestone after remediation** to track the risk reduction:
   `aws wellarchitected create-milestone --workload-id <id> --milestone-name "Post-remediation <date>"`
4. **Cross-reference with Trusted Advisor checks.**
   `aws wellarchitected list-check-summaries --workload-id <id>` — automated
   checks validate whether the review answers match the actual infrastructure.
5. **Verify remediation in the next review cycle.** After implementing the
   architectural fix, update the answer to reflect the new state and confirm
   the risk level drops from HIGH_RISK to MEDIUM_RISK or NO_RISK.

### For CONFIG_GAP

1. **No milestones (Step 3a):** create the first milestone immediately to
   establish a baseline:
   `aws wellarchitected create-milestone --workload-id <id> --milestone-name "Initial baseline"`
2. **Only default lens (Step 3b):** apply additional lenses based on the
   workload's domain:
   `aws wellarchitected associate-lenses --workload-id <id> --lens-aliases security reliability`
   The Security and Reliability lenses add pillar-specific best-practice
   questions that the Framework lens covers at a higher level.
3. **Environment not set (Step 3c):** update the workload:
   `aws wellarchitected update-workload --workload-id <id> --environment PRODUCTION`
   (or PREPRODUCTION as appropriate).

### For OK

1. No remediation required for the current posture.
2. Recommend scheduling the next review cycle within 180 days to prevent
   the workload from tripping STALE_REVIEW.
3. Recommend creating a milestone after any significant architectural change
   to keep the audit trail current.

## Deep reference: WA Tool API internals

### Non-obvious WA Tool behaviors (extended)

- **Milestones are immutable once created.** You cannot delete or edit a
  milestone — `RecordedAt` and `WorkloadSummary` are frozen. This makes
  milestones the authoritative audit trail and the only rollback reference.

- **`list-answers` requires `--pillar-id` as a mandatory parameter.** There
  is no "list all answers" API call. The six pillar IDs are fixed:
  `security`, `reliability`, `performance`, `costOptimization`,
  `operationalExcellence`, `sustainability`.

- **`list-workloads` and `list-milestones` both cap at 50 per page.** For
  account-wide sweeps, drain `NextToken` to completion.

- **Workload ID is a 32-character hex string**, not an ARN. All WA Tool API
  calls take `--workload-id <hex>`.

- **Lens aliases are lowercase identifiers, not display names.** The default
  Framework lens is `wellarchitected`. Additional lenses appear as aliases
  or custom lens ARNs.

- **`ImprovementPlan` from `describe-workload` mixes manual and
  tool-generated items.** The API does not distinguish human-committed
  actions from auto-generated gap-report suggestions. A non-zero
  `ImprovementPlanItems` count does NOT mean a human reviewed each item —
  check whether items carry a `GapReport` origin before citing the count as
  evidence of an active remediation plan.

- **Lens versioning silently remaps answer risk.** If a lens is upgraded
  after the review, `list-answers` returns answers against the new version.
  `QuestionId` is stable across versions, but `SelectedChoices` may map to
  different risk levels. A review that was OK under lens v1 may show new
  HIGH_RISK under v2 without any architectural change.

- **`list-check-summaries` returns empty (not error) when no AppRegistry
  association exists.** Automated Trusted Advisor checks require a linked
  CloudFormation stack or AppRegistry application. An empty result does NOT
  validate the review answers — it means the cross-check infrastructure is
  not connected. Do not treat "no failing checks" as evidence of correctness
  when the association is absent.

### Per-pillar risk enumeration

The `describe-workload` API returns aggregate `RiskCounts`. To produce the
`PILLAR_RISK` block in the output, iterate all six pillars:

```bash
for pillar in security reliability performance costOptimization operationalExcellence sustainability; do
  aws wellarchitected list-answers \
    --workload-id <id> --pillar-id $pillar \
    --query 'AnswerSummaries[*].Risk' --output text | sort | uniq -c
done
```

Each answer summary includes a `Risk` field (`HIGH_RISK`, `MEDIUM_RISK`,
`NO_RISK`, `NOT_APPLICABLE`, `UNANSWERED`). Aggregate these client-side to
produce per-pillar counts.

### Milestone trend analysis

Compare the `WorkloadSummary.RiskCounts` from the two most recent milestones:

```bash
aws wellarchitected get-milestone \
  --workload-id <id> --milestone-number <latest> \
  --query 'Milestone.WorkloadSummary.RiskCounts'
```

If HIGH_RISK decreased between milestones, remediation is progressing. If it
increased, the architecture is regressing — flag in REMEDIATION.

### Account-wide sweep (pagination)

```bash
aws wellarchitected list-workloads --max-results 50
# Drain NextToken:
aws wellarchitected list-workloads --max-results 50 --next-token <token>
```

For each workload, run `describe-workload` + `list-milestones`. The sweep
should flag STALE_REVIEW workloads first — these are the highest-priority
candidates for re-review. Process in batches of 10 workloads to avoid API
rate limits and keep output manageable.

### Share audit

```bash
aws wellarchitected list-workload-shares --workload-id <id>
```

Check `PermissionType` for each share. `CONTRIBUTOR` grants write access —
the shared principal can modify answers. Restrict to `READ` unless active
collaboration is intended.

## Domain

AWS CloudOps / Well-Architected Governance & Review Compliance.
