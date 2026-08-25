---
name: auditmanager-assessment-auditor
description: Audits AWS Audit Manager assessments for evidence-collection integrity, control compliance rate, delegation wiring, and account-level settings posture. Evaluates assessment lifecycle state (ACTIVE vs stopped/INACTIVE), the data-source dependency chain (AWS Config recording + CloudTrail management-event logging), NOT_ASSESSED burden, FAIL burden, framework scope coverage, KMS-key/SNS-topic/reports-destination/process-owner configuration, and outstanding delegations. Emits a deterministic verdict (INCOMPLETE_EVIDENCE | LOW_COMPLIANCE | CONFIG_GAP | OK) per assessment with enumerated findings and CLI remediation. Use when reviewing an Audit Manager assessment, validating evidence completeness before a compliance report, checking whether a stopped assessment has stale compliance data, or auditing Audit Manager account settings.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline config-snapshot classification. Live-account audits use aws auditmanager get-assessment, get-settings, get-account-status, list-assessments, list-delegations, and list-assessment-control-insights-by-control-domain (AWS CLI v2, SSO or key-based credentials). AWS Config and CloudTrail status are read via aws configservice describe-configuration-recorder-status and aws cloudtrail...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  verdict_shape: INCOMPLETE_EVIDENCE | LOW_COMPLIANCE | CONFIG_GAP | OK
  when_to_use: Reviewing an Audit Manager assessment before generating a compliance report, validating that evidence collection is trustworthy (not stale or data-source-broken), checking whether a stopped/INACTIVE assessment is producing a false compliance picture, auditing Audit Manager account settings (KMS key, SNS topic, reports destination, process owners), or scoping an assessment against the full organisation estate.
  when_not_to_use: Do NOT invoke for AWS Config conformance-pack evaluation, Security Hub finding triage, or generic IAM-policy review — these have their own auditors. Do NOT invoke if the caller only wants a compliance-score dashboard (use the Audit Manager console); this skill emits findings and remediation, not a score widget.
  activation_triggers: audit this Audit Manager assessment, is my assessment evidence complete, check assessment compliance, stopped assessment stale evidence, Audit Manager settings, assessment delegation pending, NOT_ASSESSED controls, assessment scope gap, compliance report readiness, Audit Manager config gap
  invocation_schema: 'Input: either (a) an assessment snapshot with required fields — assessment.id (str, ARN), assessment.name (str), assessment.status ("ACTIVE"|"INACTIVE"), assessment.creationTime (ISO-8601), assessment.lastUpdated (ISO-8601), scope.awsAccounts (list[accountId]), scope.awsServices (list[serviceName]), controlSets[].controls[].response ("PASS"|"FAIL"|"NOT_ASSESSED"| "MANUAL"|"UNDER_REVIEW"), settings.kmsKey (str|""), settings.snsTopic (str|""), settings.defaultAssessmentReportsDestination (s3Uri|""), settings.defaultProcessOwners (list[roleArn]) — plus optional dataSources.configRecorders (per account × region, recording bool), dataSources.cloudTrails (per region, IncludeManagementEvents bool), delegations[].status ("IN_PROGRESS"|"COMPLETE"|"FAILED") and delegations[].creationTime; OR (b) assessmentId (str) for live-account audit. Output: deterministic block per assessment — ASSESSMENT (id), FRAMEWORK (str), VERDICT ("INCOMPLETE_EVIDENCE"|"LOW_COMPLIANCE"| "CONFIG_GAP"|"OK"), REASON (1-2 sentences citing worst finding + step number), CONTROL BREAKDOWN (total, PASS, FAIL, NOT_ASSESSED, MANUAL, UNDER_REVIEW, compliance%), FINDINGS (list[finding]), REMEDIATION (list[action]).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Audit Manager, assessment, compliance, evidence collection, framework, control compliance, NOT_ASSESSED, delegation, AWS Config, CloudTrail, INACTIVE assessment, stopped assessment, defaultProcessOwners, kmsKey, assessment reports destination, SNS topic, scope, SOC 2, PCI DSS, HIPAA, control response, governance audit
  tags: auditmanager, governance, compliance, evidence-collection, delegation, config, cloudtrail, audit
---

# Audit Manager Assessment Auditor

## Quick start

**Worst finding wins.** Verdict priority: `INCOMPLETE_EVIDENCE` > `LOW_COMPLIANCE` > `CONFIG_GAP` > `OK`.

1. `INACTIVE` OR `NOT_ASSESSED > 30%` OR delegation stalled > 7d OR scope ⊊ org → **INCOMPLETE_EVIDENCE**
2. `PASS < 60%` OR `FAIL > 25%` → **LOW_COMPLIANCE**
3. Missing KMS / SNS / reports-destination / process-owners → **CONFIG_GAP**
4. Else → **OK**

**24-hour warm-up:** a new assessment (`creationTime < 24h`) is exempt from Step 1b — skip to Step 3.
**Critical NEVERs:** see [Quick NEVERs](#critical-nevers-quick-reference) below; full reasoning in [Anti-Patterns](#anti-patterns--never).
**Full algorithm + thresholds:** see [Process](#process--classification-logic-apply-in-order-aggregate-worst).
**Expert gotchas:** see [Reference](#reference--operational-gotchas-not-in-aws-docs).

## Critical NEVERs (quick reference)

Full reasoning in [Anti-Patterns](#anti-patterns--never). One-liners:

- **NEVER** report `LOW_COMPLIANCE` when `NOT_ASSESSED > 30%` — data-source break → `INCOMPLETE_EVIDENCE`.
- **NEVER** trust an `INACTIVE` assessment's compliance % — frozen → `INCOMPLETE_EVIDENCE` (1a).
- **NEVER** assume `ACTIVE` means "collecting" — Config/CloudTrail off in any account × region → silent `NOT_ASSESSED`.
- **NEVER** proceed when only a subset of data-source checks succeed — emit scoped findings, reduce confidence.
- **NEVER** retry `ThrottlingException` past 4 attempts — backoff + jitter; escalate as Quota increase.
- **NEVER** delete without a double-CONFIRM gate — evidence removal is irreversible after 90 days.

## Mindset

**One-line takeaway:** the verdict priority is fixed —
INCOMPLETE_EVIDENCE beats LOW_COMPLIANCE beats CONFIG_GAP beats OK — because
you cannot trust a compliance percentage when the evidence collection
machinery that produced it is broken.

Audit Manager automates evidence collection against a framework (PCI DSS,
HIPAA, SOC 2, custom) by reading two upstream AWS data sources:
- **AWS Config** feeds every `Config-based` control. If the Config recorder
  is off in an in-scope account, those controls silently produce **no
  evidence**.
- **AWS CloudTrail** feeds every `API-based` control. If no trail is
  logging management events, those controls produce **no evidence**.

When the data sources are broken, `NOT_ASSESSED` controls accumulate. The
root cause is a **collection gap**, not a control failure — classify
INCOMPLETE_EVIDENCE so the operator repairs Config/CloudTrail before
re-reading the number. A **stopped (INACTIVE) assessment** is the sharpest
case: the dashboard still shows a frozen score that an operator may read as
"current."

## Pre-flight: account-status and framework gate

Before evaluating any single assessment, verify the account-level
foundations. Several conditions **short-circuit** the audit.

| Check | Value | Effect |
|---|---|---|
| `get-account-status` | `ACTIVE` | Audit Manager is registered for the account. Proceed. |
| `get-account-status` | `INACTIVE` / not registered | Audit Manager is not enabled — no assessments exist by definition. Emit a single account-level finding: "Audit Manager is not enabled for this account; enable it before framework evidence can be collected." Do NOT emit per-assessment verdicts. |
| Assessment count | 0 | Account is enabled but has zero assessments. Flag as a **CONFIG_GAP** at the account level (framework coverage absent). |
| Framework id | Custom vs AWS-managed (PCI/HIPAA/SOC2/FFIEC/CIS/CMMC/GDPR/ISO/ABAC/... ) | Note the framework for context; do NOT change the verdict on framework choice. A custom framework is audited identically to a managed one. |
| Service lifecycle | End-of-support announced | Flag as advisory context. Do NOT change the verdict solely for lifecycle — the assessment may still be the system of record for the current compliance period. See Step 0. |

Malformed-snapshot and API-failure ERROR-verdict output blocks (missing status/controlSets/scope; AccessDeniedException / ThrottlingException / ResourceNotFoundException handling): [Error handling](references/error-handling.md).

**Pagination contract.** `list-assessments`, `list-delegations`, and
`list-assessment-control-insights-by-control-domain` are paginated and
return at most 100 records per call. Always loop until `nextToken` is
null before classifying — a single call truncates large estates and
under-counts NOT_ASSESSED.

## Process — Classification logic (apply in order, aggregate worst)

### Verdict thresholds (first match wins)

| Condition | Verdict | Step |
|---|---|---|
| `status` = `INACTIVE` | **INCOMPLETE_EVIDENCE** | 1a |
| `NOT_ASSESSED` > 30% (and not warm-up) | **INCOMPLETE_EVIDENCE** | 1b |
| Delegation `IN_PROGRESS` > 7d OR `FAILED` | **INCOMPLETE_EVIDENCE** | 1c |
| Scope ⊊ org members (multi-account org) | **INCOMPLETE_EVIDENCE** | 1d |
| PASS% < 60% (evidence complete) | **LOW_COMPLIANCE** | 2a |
| FAIL% > 25% (evidence complete) | **LOW_COMPLIANCE** | 2b |
| Any setting missing (KMS/SNS/reports/owners) | **CONFIG_GAP** | 3 |
| All checks pass | **OK** | 4 |

```text
not_assessed_pct = NOT_ASSESSED / total
pass_pct         = PASS / total
fail_pct         = FAIL / total
is_warm_up       = (now - creationTime) < 24h

if status == "INACTIVE":                            -> INCOMPLETE_EVIDENCE  # 1a
if not is_warm_up AND not_assessed_pct > 0.30:      -> INCOMPLETE_EVIDENCE  # 1b
if any delegation IN_PROGRESS > 7d OR == FAILED:    -> INCOMPLETE_EVIDENCE  # 1c
if scope ⊊ org members (multi-account org):         -> INCOMPLETE_EVIDENCE  # 1d
if pass_pct < 0.60:                                 -> LOW_COMPLIANCE       # 2a
if fail_pct > 0.25:                                 -> LOW_COMPLIANCE       # 2b
if any setting missing (kms/sns/reports/owners):    -> CONFIG_GAP           # 3
else:                                               -> OK                   # 4
```

### Step 0: Expert knowledge — non-obvious Audit Manager behaviours that change classification

All fifteen Step-0 expert behaviours — NOT_ASSESSED is a collection signal, Config must record in every in-scope account × region, CloudTrail management-event dependency, delegations stall without member registration, compliance % counts NOT_ASSESSED against you, MANUAL controls need humans, INACTIVE freezes the score, deleting ≠ stopping, delegation states, defaultProcessOwners, kmsKey, reports destination, scope = awsAccounts × awsServices, domain insights API, worst verdict never averages, end-of-service lifecycle: [Advanced patterns](references/advanced-patterns.md).

### Step 0b: Operational gotchas (summary — full detail in Reference)

The four most load-bearing traps (full operational detail in
[Reference — operational gotchas](#reference--operational-gotchas)):

- **SLR deletion silently breaks future delegations.**
  `AWSServiceRoleForAuditManager` auto-creates only at account
  registration; manual deletion stalls all subsequent delegations with no
  alarm. Verify before re-sending a delegation.
- **Insights API `complianceScore` ≠ assessment compliance %.** Different
  denominators (insights excludes `MANUAL`/`UNDER_REVIEW`); always
  recompute from the raw `controlSets[].controls[].response` distribution.
- **Framework version immutability.** Assessments pin to the framework at
  creation; parent-framework updates do NOT propagate. Re-baselining
  requires a new assessment.
- **INACTIVE ≠ free.** Evidence storage charges continue until
  `delete-assessment`; surface as an OPEX finding in REMEDIATION.

### Step 1: Evidence-collection integrity (INCOMPLETE_EVIDENCE drivers)

Evaluate first — these conditions invalidate the compliance number. If any
fires, the verdict is INCOMPLETE_EVIDENCE regardless of the PASS%.

**1a. Assessment lifecycle state.**
If `status` is `INACTIVE` (stopped), the assessment is no longer
collecting. The compliance score is frozen. → **INCOMPLETE_EVIDENCE**.
Cite `lastUpdated` age as evidence of staleness.

**1b. Data-source break — NOT_ASSESSED burden.**
Compute `NOT_ASSESSED_count / total_controls`. If the ratio exceeds
**30%**, the collection machinery is broken. → **INCOMPLETE_EVIDENCE**.
Cross-reference the data-source status to identify the root:
- AWS Config recorder `OFF` or absent in an in-scope account → Config-based
  controls cannot fire.
- No CloudTrail trail with `IncludeManagementEvents: true` in an in-scope
  region → API-based controls cannot fire.
The verification is a per-account × per-region loop, not a single call.
For each `acct` in `scope.awsAccounts` × each `region` in scope (default
to the assessment's `awsRegion` when scope.regions is absent), run:
`aws configservice describe-configuration-recorder-status --profile <acct>
--region <region> --query 'ConfigurationRecorders[*].{name:name,
recording:recording,lastStatus:lastStatus}'` — check `recording: true`
AND `lastStatus: SUCCESS` (a recorder with `recording: true` but
`lastStatus: FAILURE` is silently producing no snapshots). Then
`aws cloudtrail describe-trails --profile <acct> --region <region>
--query 'trailList[?IncludeManagementEvents && IsLogging].Name'` —
empty result means no management-event trail is delivering in that
perimeter. A recorder that is `STOPPED` in only one account/region is
enough to depress the compliance % silently. Even if you cannot see the
data-source status, a > 30% NOT_ASSESSED ratio on an assessment that has
been ACTIVE long enough to collect (> 7 days) is a data-source break by
induction.

**1c. Outstanding delegation.**
If any delegation for the assessment has `status` `IN_PROGRESS` for more
than 7 days (or `FAILED`), evidence for the delegated scope is missing.
→ **INCOMPLETE_EVIDENCE**.

**1d. Scope-coverage gap.**
If `scope.awsAccounts` is a strict subset of the org's member accounts
(and the framework is org-scoped — PCI/HIPAA/SOC2 typically are), the
compliance picture does not cover the estate. → **INCOMPLETE_EVIDENCE**.
To obtain the authoritative org membership, run
`aws organizations list-accounts --query 'Accounts[*].Id' --output json`
from the management account and diff against `scope.awsAccounts`; any
member account in the org but absent from scope is an uncovered account
(and, if it has no `AWSServiceRoleForAuditManager`, also a future
delegation stall — see Step 0). If the org membership is not provided
in the input and the auditor role cannot call `organizations:ListAccounts`,
skip 1d (cannot determine) and note the limitation explicitly in FINDINGS
so the operator can run the diff manually.

### Step 2: Compliance evaluation (LOW_COMPLIANCE drivers)

Only reached when Step 1 did not fire (evidence is ≥ 70% complete). Now
the compliance rate is trustworthy enough to evaluate.

**2a. Low overall compliance.** If `PASS% < 60%` (PASS_count /
total_controls), the assessed controls are predominantly failing.
→ **LOW_COMPLIANCE**.

**2b. High FAIL burden.** If `FAIL_count / total_controls > 25%`, the
control-failure burden is severe even if PASS% is borderline.
→ **LOW_COMPLIANCE**.

If neither 2a nor 2b fires, compliance is acceptable for this assessment
(≥ 60% PASS, ≤ 25% FAIL) — proceed to Step 3.

### Step 3: Configuration evaluation (CONFIG_GAP drivers)

Evaluate Audit Manager settings and assessment configuration. Any missing
setting is a governance gap. → **CONFIG_GAP**.

| Setting | Missing → Finding |
|---|---|
| `settings.kmsKey` | No customer-managed encryption — framework encryption-ownership control unsupported |
| `settings.snsTopic` | No notification wiring — collection-complete and attention events silently dropped |
| `settings.defaultAssessmentReportsDestination` | Cannot generate assessment reports — `generate-assessment-report` will fail |
| `settings.defaultProcessOwners` (empty) | No designated evidence reviewers — `UNDER_REVIEW` controls pile up with no owner |
| `assessment.assessmentReportsDestination` (assessment-level, unset) | Per-assessment report destination absent (settings default not inherited) |

If ALL settings are configured, proceed to Step 4.

### Step 4: Aggregation — worst verdict wins

The verdict priority is fixed (worst-first):

```text
verdict = first_match(
    any Step 1 condition  -> INCOMPLETE_EVIDENCE,
    any Step 2 condition  -> LOW_COMPLIANCE,
    any Step 3 condition  -> CONFIG_GAP,
    otherwise             -> OK
)
```

If no findings (evidence complete, compliance ≥ 60%, all settings
configured, scope covers the estate), the verdict is **OK**.

## Output format (per assessment)

```text
ASSESSMENT: <assessment-id or name>
FRAMEWORK: <framework name>
VERDICT: INCOMPLETE_EVIDENCE | LOW_COMPLIANCE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
CONTROL BREAKDOWN:
  total: <N>, PASS: <n>, FAIL: <n>, NOT_ASSESSED: <n>, MANUAL: <n>, UNDER_REVIEW: <n>
  compliance%: <PASS / total * 100, one decimal>
FINDINGS:
  - [<severity note>] <finding description (Step Na)>
  - [<severity note>] <finding description (Step Nb)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

**JSON-equivalent schema** (for runtimes that prefer structured output):

```json
{
  "assessment": "str (id or ARN)",
  "framework": "str",
  "verdict": "INCOMPLETE_EVIDENCE | LOW_COMPLIANCE | CONFIG_GAP | OK | ERROR",
  "reason": "str (worst finding + step number)",
  "control_breakdown": {
    "total": "int", "PASS": "int", "FAIL": "int",
    "NOT_ASSESSED": "int", "MANUAL": "int", "UNDER_REVIEW": "int",
    "compliance_pct": "float"
  },
  "findings": [{"severity": "str", "description": "str", "step": "str"}],
  "remediation": ["str"]
}
```

### Worked example — stopped assessment with high NOT_ASSESSED

```text
ASSESSMENT: arn:aws:auditmanager:us-east-1:111111111111:assessment/stopped-assessment
FRAMEWORK: SOC 2
VERDICT: INCOMPLETE_EVIDENCE
REASON: Assessment status is INACTIVE (stopped) since 2026-02-14 — no new
evidence collected for ~6 months; additionally 42% of controls are
NOT_ASSESSED, indicating the Config/CloudTrail data sources were broken
before the assessment was stopped (Steps 1a, 1b).
CONTROL BREAKDOWN:
  total: 312, PASS: 98, FAIL: 41, NOT_ASSESSED: 131, MANUAL: 30, UNDER_REVIEW: 12
  compliance%: 31.4
FINDINGS:
  - [STALE] Assessment status INACTIVE since 2026-02-14; compliance score frozen (Step 1a)
  - [COLLECTION BREAK] NOT_ASSESSED 131/312 (42%) — data-source break suspected (Step 1b)
  - [CONFIG] No Config recorder status provided — verify in each in-scope account
REMEDIATION:
  1. Verify data sources: `aws configservice describe-configuration-recorder-status`
     and `aws cloudtrail describe-trails` for each in-scope account.
  2. Reactivate: `aws auditmanager update-assessment-status --assessment-id <id> --status ACTIVE`.
  3. Re-baseline the compliance % after a full collection cycle (~24h).
```

## Edge-case handling

Edge cases — < 24h warm-up, borderline mixed distribution, MANUAL-heavy frameworks, settings vs assessment-level overrides, single-account org, COMPLETE delegation with evidenceInsufficient: [Advanced patterns](references/advanced-patterns.md).
API failure, pagination fallback, and partial-success data-source fan-out (scoped [UNVERIFIED] findings, verified-subset classification, > 25% unverified escalation): [Error handling](references/error-handling.md).

## Anti-Patterns — NEVER

- NEVER report LOW_COMPLIANCE when the NOT_ASSESSED ratio is > 30%. The
  low compliance % in that case is a symptom of a broken data source, not
  of failing controls. The correct verdict is INCOMPLETE_EVIDENCE; the
  remediation is to repair Config/CloudTrail, not to chase failing
  controls. Conflating the two wastes the operator's time on the wrong
  fix.

- NEVER treat an INACTIVE (stopped) assessment's compliance % as current.
  The number is frozen at stop time. Reporting it as if live is a
  material misrepresentation in a compliance context. Always cite the
  `lastUpdated` age and classify as INCOMPLETE_EVIDENCE (Step 1a).

- NEVER assume an ACTIVE assessment is collecting evidence. Status ACTIVE
  only means Audit Manager is "trying" to collect — if Config or
  CloudTrail is off in an in-scope account, the collection silently
  produces nothing and controls fall to NOT_ASSESSED. Always cross-check
  the data-source status (Step 1b) before trusting ACTIVE.

- NEVER flag `MANUAL` controls as failures. MANUAL is a control-design
  choice (non-automatable), not a defect. Flag the LACK of a review
  pipeline (empty `defaultProcessOwners`) as CONFIG_GAP, not the MANUAL
  controls themselves.

- NEVER recommend deleting an assessment as remediation without
  confirming no active compliance period depends on its retained
  evidence. Deletion permanently removes evidence within 90 days. The
  safe path is `update-assessment-status --status INACTIVE` (preserve) or
  reactivate.

- NEVER recommend generating an assessment report when
  `defaultAssessmentReportsDestination` (settings or assessment-level) is
  unset. `generate-assessment-report` will fail. Remediate the
  destination first, then generate.

- NEVER treat a brand-new assessment (< 24 hours old) with high
  NOT_ASSESSED as INCOMPLETE_EVIDENCE. The first evidence-collection
  cycle has not completed. This is a false positive.

- NEVER downgrade the verdict because the framework is custom (not
  AWS-managed PCI/HIPAA/SOC2). Custom frameworks are audited identically.
  The verdict is data-driven, not framework-driven.

- NEVER ignore a `FAILED` delegation. A delegation that FAILED is a
  collection break for its scoped accounts — the evidence for those
  accounts is missing regardless of the overall NOT_ASSESSED ratio. Fire
  Step 1c.

- NEVER assume a stalled `IN_PROGRESS` delegation is a network blip.
  Delegations to a member account require that account to (a) be in the
  same AWS Organization, (b) have Audit Manager enabled, and (c) carry
  the `AWSServiceRoleForAuditManager` service-linked role plus
  `iam:CreateServiceLinkedRole` permission. A delegation older than the
  assessment's `creationTime` is almost always a missing-SLR or
  removed-from-org condition, not a retryable API fault — re-sending the
  delegation without fixing the member account burns another 7-day wait.

- NEVER confuse `get-account-status` (Audit Manager registration) with
  assessment `status` (ACTIVE/INACTIVE). The account-status `status`
  reflects whether Audit Manager is enabled for the account; the
  assessment `status` reflects whether a specific assessment is running.
  A registered account can have all assessments INACTIVE.

- NEVER suppress CONFIG_GAP findings (missing KMS / SNS / reports
  destination / process owners) just because the verdict is already
  INCOMPLETE_EVIDENCE. An INACTIVE assessment is usually reactivated
  later, and a settings gap silently degrades the next compliance
  period the moment it goes ACTIVE again. Surface the settings gap in
  FINDINGS even though the VERDICT line collapses to the worst — the
  operator fixes both in one pass.

- NEVER proceed with classification when only a subset of data-source
  checks succeed. Each unchecked account × region is a Step 1b
  collection break for that perimeter — emit a scoped finding per
  unverified scope (`[UNVERIFIED] Config status for account X in region
  Y not retrievable — treat as suspected collection break`), classify on
  what you verified, and explicitly note in REASON that the verdict
  confidence is reduced. If > 25% of the in-scope perimeter is
  unverified, escalate the verdict to INCOMPLETE_EVIDENCE regardless of
  the visible NOT_ASSESSED ratio — averaging over a partial perimeter
  hides the worst accounts.

- NEVER retry a `ThrottlingException` past 4 attempts without
  exponential backoff + jitter. Audit Manager throttles at the account
  level via a token-bucket limiter; the AWS SDK default (4 retries with
  backoff) is the safe ceiling. Blind retries in a tight loop widen the
  throttle window for every other consumer of the account and can push
  the limiter into a multi-minute cooldown. If still throttled after the
  SDK budget is exhausted, escalate as a Service Quota increase
  (`auditmanager:GetAssessment`, `auditmanager:ListAssessments`,
  `auditmanager:ListDelegations` per account/region) — re-calling the
  API is not a fix.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-assessment-status`, `delete-assessment`,
  `update-settings`, `generate-assessment-report`), the auditor MUST emit:
  `CONFIRM: About to <action> on assessment <id> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`. Do NOT execute the CLI
  command until the operator confirms.
- Before reactivating a stopped assessment, confirm no replacement
  assessment was created in the interim. Two ACTIVE assessments on the
  same framework double-collect and can confuse the compliance picture.
- Before changing account `settings`, capture the current settings for
  rollback: `aws auditmanager get-settings --region <r> --output json >
  /tmp/auditmanager-settings-backup-$(date +%s).json`. Settings changes
  apply to ALL assessments in the account.
- Before deleting an assessment, verify no active compliance period
  (audit, examination window) depends on its evidence. Deletion is
  irreversible after 90 days. **For `delete-assessment` specifically,
  require a SECOND confirmation** — single CONFIRM is insufficient for
  an irreversible bulk-evidence-destruction operation. Emit:
  `CONFIRM (2 of 2): Deleting assessment <id> permanently removes all
  collected evidence after 90 days. This cannot be undone. Type the
  assessment id verbatim to proceed:`. Only execute the CLI when the
  operator echoes the assessment id character-for-character. For
  `update-assessment-status` (reversible) and `update-settings`
  (reversible with backup), single CONFIRM is sufficient.
- Prefer additive changes (set a missing KMS key, add process owners)
  over destructive changes (delete an assessment). Additive changes are
  reversible; destructive changes are not.
- Verify the caller's role has `auditmanager:UpdateAssessmentStatus` /
  `UpdateSettings` before emitting remediation CLI — most read-only
  auditor roles CANNOT, and the command will fail with `AccessDenied`.
  Surface this before the operator approves.

## Remediation guidance

Full per-verdict remediation playbooks with CLI (INCOMPLETE_EVIDENCE 1a/1b/1c/1d, LOW_COMPLIANCE, CONFIG_GAP, OK): [Advanced patterns](references/advanced-patterns.md).

## Reference — operational gotchas (NOT in AWS docs)

Operational gotchas NOT in AWS docs — SLR deletion stalls delegations, insights complianceScore denominator, framework version immutability, INACTIVE evidence storage cost, deprecated `state` field, insights vs get-assessment control counts, Config→Audit Manager propagation latency: [Advanced patterns](references/advanced-patterns.md).

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026): none affecting the audit surface as of 2026-08 — see [Advanced patterns](references/advanced-patterns.md).

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — Step-0 expert behaviours, edge-case catalog, per-verdict remediation playbooks, operational gotchas not in AWS docs, recent AWS features
- [Error handling](references/error-handling.md) — malformed-snapshot and API-failure ERROR blocks, pagination fallback, partial-success fan-out handling

## Domain

AWS CloudOps / Audit Manager Governance & Compliance Evidence Integrity.

## AWS documentation

- **AWS Audit Manager User Guide** — https://docs.aws.amazon.com/audit-manager/latest/userguide/what-is.html
- **Audit Manager Security** — https://docs.aws.amazon.com/audit-manager/latest/userguide/security.html
- **Audit Manager API Reference** — https://docs.aws.amazon.com/audit-manager/latest/APIReference/
- **Audit Manager CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/auditmanager/
