---
name: auditmanager-assessment-auditor
description: >-
  Audits AWS Audit Manager assessments for evidence-collection integrity,
  control compliance rate, delegation wiring, and account-level settings
  posture. Evaluates assessment lifecycle state (ACTIVE vs stopped/INACTIVE),
  the data-source dependency chain (AWS Config recording + CloudTrail
  management-event logging), NOT_ASSESSED burden, FAIL burden, framework
  scope coverage, KMS-key/SNS-topic/reports-destination/process-owner
  configuration, and outstanding delegations. Emits a deterministic verdict
  (INCOMPLETE_EVIDENCE | LOW_COMPLIANCE | CONFIG_GAP | OK) per assessment
  with enumerated findings and CLI remediation. Use when reviewing an Audit
  Manager assessment, validating evidence completeness before a compliance
  report, checking whether a stopped assessment has stale compliance data,
  or auditing Audit Manager account settings.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline config-snapshot classification.
  Live-account audits use aws auditmanager get-assessment, get-settings,
  get-account-status, list-assessments, list-delegations, and
  list-assessment-control-insights-by-control-domain (AWS CLI v2, SSO or
  key-based credentials). AWS Config and CloudTrail status are read via
  aws configservice describe-configuration-recorder-status and aws
  cloudtrail describe-trails.
keywords:
  - Audit Manager
  - assessment
  - compliance
  - evidence collection
  - framework
  - control compliance
  - NOT_ASSESSED
  - delegation
  - AWS Config
  - CloudTrail
  - INACTIVE assessment
  - stopped assessment
  - defaultProcessOwners
  - kmsKey
  - assessment reports destination
  - SNS topic
  - scope
  - SOC 2
  - PCI DSS
  - HIPAA
  - control response
  - governance audit
tags: [auditmanager, governance, compliance, evidence-collection, delegation, config, cloudtrail, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Governance
  verdict_shape: "INCOMPLETE_EVIDENCE | LOW_COMPLIANCE | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing an Audit Manager assessment before generating a compliance
    report, validating that evidence collection is trustworthy (not stale or
    data-source-broken), checking whether a stopped/INACTIVE assessment is
    producing a false compliance picture, auditing Audit Manager account
    settings (KMS key, SNS topic, reports destination, process owners), or
    scoping an assessment against the full organisation estate.
  when_not_to_use: >-
    Do NOT invoke for AWS Config conformance-pack evaluation, Security Hub
    finding triage, or generic IAM-policy review — these have their own
    auditors. Do NOT invoke if the caller only wants a compliance-score
    dashboard (use the Audit Manager console); this skill emits findings and
    remediation, not a score widget.
  activation_triggers:
    - "audit this Audit Manager assessment"
    - "is my assessment evidence complete"
    - "check assessment compliance"
    - "stopped assessment stale evidence"
    - "Audit Manager settings"
    - "assessment delegation pending"
    - "NOT_ASSESSED controls"
    - "assessment scope gap"
    - "compliance report readiness"
    - "Audit Manager config gap"
  invocation_schema: >-
    Input: either (a) an Audit Manager assessment snapshot (assessment
    metadata + control statistics + settings + data-source status), OR
    (b) an assessment id/ARN for live-account audit. Output: deterministic
    ASSESSMENT/VERDICT/REASON/FINDINGS/REMEDIATION block per assessment,
    where VERDICT is INCOMPLETE_EVIDENCE, LOW_COMPLIANCE, CONFIG_GAP, or OK.
---

# Audit Manager Assessment Auditor

**Bottom line — check in this order, worst finding wins:**
1. Is evidence collection broken? (`INACTIVE` | `NOT_ASSESSED > 30%` | stalled delegation | scope gap) → **INCOMPLETE_EVIDENCE**
2. Is compliance low? (`PASS < 60%` | `FAIL > 25%`) → **LOW_COMPLIANCE**
3. Is a setting missing? (no KMS | no SNS | no reports dest | no process owners) → **CONFIG_GAP**
4. Otherwise → **OK**

Exemption: a brand-new assessment (`creationTime < 24h`) is exempt from
check 1's NOT_ASSESSED rule — the first collection cycle has not finished.

## Quick reference — verdict thresholds

Apply the steps **in order** — the first matching step produces the verdict.
Deep Audit Manager behaviours that change classification are in
[Step 0](#step-0-expert-knowledge-non-obvious-audit-manager-behaviours);
the *why* behind the verdict priority is in
[Mindset](#mindset) below.

**24-hour warm-up exemption:** if `creationTime` is less than 24 hours
ago, a high NOT_ASSESSED% is EXPECTED (first collection cycle not
complete). Do NOT fire Step 1b — skip to Step 3 and emit an advisory.

| Condition | Verdict | Step |
|---|---|---|
| Assessment `status` = `INACTIVE` (stopped) | **INCOMPLETE_EVIDENCE** | 1a |
| `NOT_ASSESSED` controls > 30% of total (data-source break) | **INCOMPLETE_EVIDENCE** | 1b |
| Outstanding delegation `PENDING`/`IN_PROGRESS` > 7 days on ACTIVE assessment | **INCOMPLETE_EVIDENCE** | 1c |
| Assessment scope covers fewer accounts than the org/member-account estate | **INCOMPLETE_EVIDENCE** | 1d |
| Evidence complete (NOT_ASSESSED ≤ 30%) AND PASS% < 60% | **LOW_COMPLIANCE** | 2a |
| Evidence complete AND FAIL% > 25% of total controls | **LOW_COMPLIANCE** | 2b |
| Evidence complete AND PASS% ≥ 60% AND any setting missing (no KMS / no SNS / no reports dest / no process owners) | **CONFIG_GAP** | 3 |
| Evidence complete AND PASS% ≥ 60% AND all settings configured AND scope complete | **OK** | 4 |

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

**If the assessment metadata block is malformed** (missing `status`,
missing `controlSets`, missing `scope`), output:

```text
ASSESSMENT: <id>
VERDICT: ERROR
REASON: Assessment snapshot is missing required fields (status/controlSets/scope) — cannot classify.
REMEDIATION: Re-fetch with `aws auditmanager get-assessment --assessment-id <id> --region <r>` and re-audit.
```

**If an Audit Manager API call fails** during a live audit
(`AccessDeniedException`, `ThrottlingException`, `ResourceNotFoundException`,
or any non-2xx), do NOT guess a verdict from partial data. Emit:

```text
ASSESSMENT: <id>
VERDICT: ERROR
REASON: <API name> returned <errorClass>: <message> — audit aborted.
REMEDIATION: <permission/quota/retry hint, e.g. "grant auditmanager:GetAssessment"
  or "request Service Quota increase for auditmanager:ListAssessments per account">.
```

**Pagination contract.** `list-assessments`, `list-delegations`, and
`list-assessment-control-insights-by-control-domain` are paginated and
return at most 100 records per call. Always loop until `nextToken` is
null before classifying — a single call truncates large estates and
under-counts NOT_ASSESSED.

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious Audit Manager behaviours that change classification

These behaviours are easy to misjudge without operational Audit Manager
experience. Each changes a verdict if ignored.

- **`NOT_ASSESSED` is a collection signal, not a failure signal.** A
  control in `NOT_ASSESSED` means Audit Manager never evaluated it — the
  data source (Config or CloudTrail) did not produce the inputs the
  control's evidence finder expects. Treating `NOT_ASSESSED` the same as
  `FAIL` produces a LOW_COMPLIANCE verdict and prescribes "fix the failing
  control," when the correct remediation is "repair the data source." The
  30% threshold on NOT_ASSESSED (Step 1b) exists to route these cases to
  INCOMPLETE_EVIDENCE instead.

- **Audit Manager cannot collect without AWS Config recording in EVERY
  in-scope account × region.** Config-based controls read configuration
  snapshots from the Config recorder. If the recorder is `OFF` or
  `notRecording` in any account listed in `scope.awsAccounts`, every
  Config-based control in that account returns `NOT_ASSESSED`. The
  assessment remains `ACTIVE` — there is no alarm. Recorders are also
  per-region: Audit Manager does not auto-fan-out across regions, so
  every region in the compliance perimeter must have its own recorder
  `recording: true`, or regional controls silently return `NOT_ASSESSED`.
  Verify with `aws configservice describe-configuration-recorder-status`
  per account × region.

- **CloudTrail management events are the second silent dependency.**
  API-based controls read CloudTrail management events. A trail that logs
  only data events (S3/Lambda), or a trail that was deleted, produces
  `NOT_ASSESSED` for every API-based control. Management-event logging
  must be ON. Verify with `aws cloudtrail describe-trails` and confirm
  `IncludeManagementEvents: true` on at least one active trail per region
  in scope. For org-scoped assessments, only a trail with
  `IsOrganizationTrail: true` delivers management events to member
  accounts — a per-account trail in the management account does NOT
  satisfy the dependency for delegated members.

- **Cross-account delegations silently stall when the member account has
  not enabled Audit Manager.** `list-delegations` returning
  `IN_PROGRESS` for more than 7 days almost always means the delegated
  account has not registered with Audit Manager (no
  `AWSServiceRoleForAuditManager` service-linked role) or has been
  removed from the organization. A delegation cannot be force-completed
  from the administrator side — remediation is "fix the member account",
  not "retry the API". Treat a stalled delegation older than the
  assessment's `creationTime` as evidence of a missing-member break.

- **Compliance % is `PASS / total controls` (NOT_ASSESSED counts against
  you).** The Audit Manager console computes compliance as the fraction of
  controls with response `PASS` over the total control count. Controls in
  `NOT_ASSESSED`, `UNDER_REVIEW`, `MANUAL`, and `FAIL` all count as
  non-compliant in the denominator. A 50% compliance score may mean "50%
  FAIL, 50% PASS" (a real LOW_COMPLIANCE case) OR "50% PASS, 50%
  NOT_ASSESSED" (a data-source break). Read the response distribution,
  not just the percentage.

- **`MANUAL` controls require human attestation and never auto-resolve.**
  A control with response `MANUAL` is non-automatable — a human must
  upload evidence and mark it PASS/FAIL. If the assessment has many
  `MANUAL` controls in `UNDER_REVIEW`, the compliance % is structurally
  capped until a human acts. A high `MANUAL` + `UNDER_REVIEW` count with
  no `defaultProcessOwners` configured is a CONFIG_GAP (no one is
  designated to close them).

- **An INACTIVE (stopped) assessment retains its evidence but freezes its
  compliance score.** `status: INACTIVE` means Audit Manager stopped
  collecting. The last compliance % is preserved in the metadata and
  still displayed. `lastUpdated` stops advancing. An operator reading the
  dashboard sees a number and may treat it as live. The remedy is either
  reactivate (`update-assessment-status --status ACTIVE`) or formally
  retire the assessment and start a new one — never report against a
  frozen score.

- **Deleting an assessment is NOT the same as stopping it.** A deleted
  assessment's evidence is permanently removed within 90 days. A stopped
  (INACTIVE) assessment's evidence is preserved. When an operator says
  "we stopped the assessment," verify whether `status: INACTIVE` (evidence
  safe) or the assessment is absent from `list-assessments` (evidence
  gone). Do not recommend deletion as remediation without confirming no
  compliance period depends on the retained evidence.

- **Delegations are per-assessment evidence-collection requests to linked
  accounts.** `list-delegations` returns delegations with `status`
  `IN_PROGRESS`, `COMPLETE`, or `FAILED`. A delegation `IN_PROGRESS` for
  more than 7 days on an otherwise-ACTIVE assessment means the delegated
  account has not returned evidence — a scoped INCOMPLETE_EVIDENCE
  condition. A `FAILED` delegation is an immediate collection break.

- **`defaultProcessOwners` is the human-review pipeline.** Audit Manager
  settings' `defaultProcessOwners` lists the IAM principals designated to
  review and approve `UNDER_REVIEW` evidence. When empty, `UNDER_REVIEW`
  controls accumulate with no owner — the assessment runs but its
  human-attested dimension stalls. This is a CONFIG_GAP, not a compliance
  finding.

- **`kmsKey` in settings encrypts assessment reports and evidence-finder
  data at rest.** When unset, Audit Manager falls back to AWS-owned keys
  — you lose customer-managed key control and break the encryption-
  ownership chain that most frameworks (SOC 2 CC6.1, PCI 3.5/3.6) require.
  This is a CONFIG_GAP.

- **`defaultAssessmentReportsDestination` gates report generation.**
  Without an S3 bucket + prefix in settings, `generate-assessment-report`
  fails. A compliance program that cannot produce reports is a CONFIG_GAP.

- **Assessment scope is `awsAccounts` × `awsServices`.** An empty
  `awsAccounts` means the assessment audits only the Audit Manager
  administrator account. An empty `awsServices` means all services (broad
  scope). For an Org-wide compliance program, `awsAccounts` must cover
  every member account; a subset produces an INCOMPLETE_EVIDENCE verdict
  because the compliance picture does not cover the estate.

- **`list-assessment-control-insights-by-control-domain` is the
  domain-level view.** When the per-control response distribution is not
  available in the snapshot, this API returns `controlInsights` per
  domain with `evidenceCount` and `complianceScore`. A domain with
  `evidenceCount: 0` on an ACTIVE assessment is a scoped
  INCOMPLETE_EVIDENCE signal for that domain.

- **Resolving conflicting conditions — the worst verdict wins, never
  average.** Multiple findings often co-occur (e.g., a stopped
  assessment that also has FAIL% > 25% AND a missing KMS key). The
  VERDICT line is the *single* highest-priority finding (Step 1 > 2 > 3 >
  4), never a blend. Report ALL findings; only the VERDICT collapses to
  the worst. Do NOT suppress a CONFIG_GAP finding because
  INCOMPLETE_EVIDENCE fired — the operator fixes both in one pass, and
  the settings gap will silently degrade the next period once the
  assessment is reactivated.

- **Audit Manager end-of-service lifecycle.** AWS has signalled Audit
  Manager end-of-service. An active assessment on a service in
  end-of-service still produces evidence today, but the compliance program
  must plan a migration path (manual evidence collection or an
  alternative). Flag lifecycle as advisory context in REMEDIATION; do NOT
  let it override the data-driven verdict.

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
The verification is a per-account × per-region loop, not a single call:
`for acct in scope.awsAccounts: for region in scope.regions (or the
administrator home region): aws configservice
describe-configuration-recorder-status --profile <acct> --region <region>`
and the equivalent `aws cloudtrail describe-trails` — a recorder that is
`STOPPED` in only one account/region is enough to depress the compliance %
silently. Even if you cannot see the data-source status, a > 30%
NOT_ASSESSED ratio on an assessment that has been ACTIVE long enough to
collect (> 7 days) is a data-source break by induction.

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

- **ACTIVE assessment created < 24 hours ago.** Evidence collection has
  not completed its first cycle. A high NOT_ASSESSED% here is EXPECTED,
  not a data-source break. Do NOT fire Step 1b if `creationTime` is less
  than 24 hours ago — emit an advisory note and skip to Step 3. The
  compliance number is not yet meaningful.

- **Mixed response distribution (borderline).** If PASS% is 58% (just
  under 60%) and NOT_ASSESSED% is 28% (just under 30%), both thresholds
  are narrowly missed. Classify as CONFIG_GAP only if a Step 3 setting is
  missing; otherwise classify as OK with a borderline advisory. Do NOT
  round into LOW_COMPLIANCE or INCOMPLETE_EVIDENCE — the thresholds are
  strict boundaries.

- **MANUAL-heavy framework.** Some frameworks (e.g., a custom GRC
  framework) may have > 50% MANUAL controls by design. These are
  structurally `UNDER_REVIEW` until a human attests. Do NOT treat
  UNDER_REVIEW as NOT_ASSESSED. If `defaultProcessOwners` is set and the
  MANUAL controls are recent, this is OK. If `defaultProcessOwners` is
  empty AND MANUAL/UNDER_REVIEW > 30%, classify as CONFIG_GAP (no review
  pipeline), not INCOMPLETE_EVIDENCE.

- **Settings vs assessment-level overrides.** An assessment may carry its
  own `assessmentReportsDestination` that overrides the settings default.
  Check BOTH — if settings has one but the assessment does not, the
  settings default applies (OK). If neither has one, it is a CONFIG_GAP.

- **Single-account Org.** If `scope.awsAccounts` has exactly one account
  and the org also has exactly one account (standalone, not Org-joined),
  there is no scope gap. Step 1d only fires when the scope is a strict
  subset of a multi-account org.

- **Delegation COMPLETE but evidenceInsufficient.** A delegation marked
  COMPLETE does not guarantee sufficient evidence — the delegated account
  may have returned partial data. If `evidenceCount` per domain is 0 on a
  COMPLETE delegation, treat as a scoped INCOMPLETE_EVIDENCE finding under
  Step 1c.

- **API failure / pagination fallback.** `list-assessments`,
  `list-delegations`, and `list-assessment-control-insights-by-control-domain`
  are paginated — a single call without `--next-token` truncates large
  estates. Always loop on `nextToken`. If a `ThrottlingException` or
  `AccessDeniedException` returns on `get-assessment`, emit `VERDICT: ERROR`
  with the API error class (do NOT guess a verdict from a missing snapshot),
  and re-route the operator to check IAM `auditmanager:GetAssessment` and
  the account Service Quota. An empty `list-accounts` response from
  Organizations is *not* "no members" — it usually means the caller is in
  a member account, not the management account; treat as "scope cannot be
  determined" per Step 1d, not as "single-account org".

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
  irreversible after 90 days.
- Prefer additive changes (set a missing KMS key, add process owners)
  over destructive changes (delete an assessment). Additive changes are
  reversible; destructive changes are not.
- Verify the caller's role has `auditmanager:UpdateAssessmentStatus` /
  `UpdateSettings` before emitting remediation CLI — most read-only
  auditor roles CANNOT, and the command will fail with `AccessDenied`.
  Surface this before the operator approves.

## Remediation guidance

### For INCOMPLETE_EVIDENCE — stopped assessment (Step 1a)

1. Determine whether the stop was intentional (e.g., framework retired) or
   accidental. Check `lastUpdated` age.
2. If unintentional, reactivate:
   `aws auditmanager update-assessment-status --assessment-id <id> --status ACTIVE --region <r>`.
3. After reactivation, wait one full collection cycle (~24h) before
   re-reading the compliance %. The first cycle repopulates evidence.
4. If the stop was intentional, retire the assessment formally and migrate
   to a new assessment with the current framework version.

### For INCOMPLETE_EVIDENCE — data-source break (Step 1b)

1. Verify AWS Config in EVERY in-scope account:
   `aws configservice describe-configuration-recorder-status`. If
   `recording: false`, restart:
   `aws configservice start-configuration-recorder --configuration-recorder-name default`.
2. Verify CloudTrail management-event logging in EVERY in-scope region:
   `aws cloudtrail describe-trails`. Confirm at least one trail has
   `IncludeManagementEvents: true` and is logging. If not, create or
   update a multi-region management-event trail.
3. After repair, wait one collection cycle (~24h) for Audit Manager to
   re-evaluate the NOT_ASSESSED controls. Re-run
   `aws auditmanager get-assessment --assessment-id <id>` and re-audit.

### For INCOMPLETE_EVIDENCE — outstanding delegation (Step 1c)

1. List delegations:
   `aws auditmanager list-delegations --assessment-id <id> --region <r>`.
2. For each `IN_PROGRESS` delegation older than 7 days, contact the
   delegated account owner. Re-send if needed:
   the delegation cannot be force-completed from the administrator side.
3. For `FAILED` delegations, review the failure reason and re-create the
   delegation after resolving the underlying permission/connectivity issue.

### For INCOMPLETE_EVIDENCE — scope gap (Step 1d)

1. Update the assessment scope to include all org member accounts:
   `aws auditmanager update-assessment --assessment-id <id> --scope
   awsAccounts='<json>'`. Use
   `aws organizations list-accounts` to enumerate the full membership.
2. Re-evaluate after the next collection cycle.

### For LOW_COMPLIANCE (Steps 2a/2b)

1. Identify the FAIL controls and their control domains. Use
   `aws auditmanager list-assessment-control-insights-by-control-domain
   --assessment-id <id>` to find the weakest domains.
2. For each FAIL control, review the collected evidence in the Audit
   Manager console and remediate the underlying AWS resource (e.g.,
   enable encryption, restrict a security group, add an IAM condition).
3. After remediation, wait for the next collection cycle to re-evaluate.
   Audit Manager will re-test the control and update the response.
4. For FAIL controls that are false positives (e.g., a control that tests
   for a setting that is enforced upstream), document the exception in the
   assessment report rather than suppressing the control.

### For CONFIG_GAP (Step 3)

1. Set KMS key (customer-managed):
   `aws auditmanager update-settings --kms-key arn:aws:kms:<region>:<acct>:key/<id>`.
2. Set SNS topic:
   `aws auditmanager update-settings --sns-topic arn:aws:sns:<region>:<acct>:<topic-name>`.
   Ensure the topic policy permits `auditmanager.amazonaws.com` to publish.
3. Set assessment reports destination:
   `aws auditmanager update-settings --default-assessment-reports-destination
   s3://<bucket>/<prefix>`. Ensure the bucket policy permits Audit Manager
   to write.
4. Set default process owners:
   `aws auditmanager update-settings --default-process-owners
   roleArns=<arn1>,<arn2>`. Designate at least one reviewer principal.

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit (monthly) to catch Config/CloudTrail
   regressions before they invalidate a compliance period.
3. Recommend generating an assessment report at the close of each
   compliance period to formalise the evidence.

## Domain

AWS CloudOps / Audit Manager Governance & Compliance Evidence Integrity.
