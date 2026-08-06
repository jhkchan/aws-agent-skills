---
name: resiliencehub-app-assessment-auditor
description: >-
  Audits AWS Resilience Hub application assessments for assessment staleness
  (older than 90 days), resiliency policy binding and tier-to-RTO/RPO
  calibration, per-tier compliance breaches (MissionCritical or Critical
  NonCompliant triggers HIGH_RISK), aggregate compliance score below 80
  (LOW_COMPLIANCE), app-version drift since the last assessment, failed or
  pending assessment status (no compliance data), and unimplemented
  alarm / SDD / test recommendations. Emits a deterministic verdict
  (STALE_ASSESSMENT | HIGH_RISK | LOW_COMPLIANCE | CONFIG_GAP | OK) per app
  with enumerated findings and CLI remediation. Use when reviewing Resilience
  Hub app assessments, checking RTO/RPO compliance, validating resiliency
  policy coverage, or auditing assessment freshness before a production
  launch.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline assessment-document
  classification. Live-account audits use aws resiliencehub
  list-app-assessments, describe-app-assessment, describe-app,
  list-resiliency-policies, and describe-resiliency-policy (AWS CLI v2,
  SSO or key-based credentials).
keywords:
  - Resilience Hub
  - app assessment
  - RTO
  - RPO
  - resiliency policy
  - compliance score
  - MissionCritical
  - Critical tier
  - NonCompliant
  - assessment staleness
  - app version drift
  - alarm recommendations
  - SDD recommendations
  - resiliency audit
  - compliance breach
  - assessment freshness
  - publish-app-version
  - start-app-assessment
  - policy binding
  - resiliency tier
tags: [resiliencehub, management, resiliency, rto, rpo, compliance, assessment, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Management
  verdict_shape: "STALE_ASSESSMENT | HIGH_RISK | LOW_COMPLIANCE | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a Resilience Hub app assessment before production launch,
    checking RTO/RPO compliance against a resiliency policy, auditing
    assessment freshness, validating that the app version has not drifted
    since the last assessment, or confirming alarm/SDD/test recommendation
    coverage.
  activation_triggers:
    - "audit this resilience hub assessment"
    - "is my app assessment stale"
    - "check RTO RPO compliance"
    - "resiliency policy coverage"
    - "assessment freshness check"
    - "app version drift resilience hub"
    - "compliance score too low"
    - "MissionCritical tier non compliant"
    - "resilience hub recommendations"
    - "resiliency policy not attached"
  invocation_schema: >-
    Input: either (a) a Resilience Hub app-assessment snapshot (assessment
    metadata + compliance map + policy + recommendations), optionally paired
    with describe-app metadata, OR (b) an app-ARN for live-account audit.
    Output: deterministic APP/VERDICT/REASON/FINDINGS/REMEDIATION block per
    app, where VERDICT is one of STALE_ASSESSMENT, HIGH_RISK, LOW_COMPLIANCE,
    CONFIG_GAP, OK, or ERROR.
---

# Resilience Hub App Assessment Auditor

## Mindset

**One-line takeaway:** the verdict is the **worst** finding across all
dimensions, evaluated in a fixed precedence — STALE_ASSESSMENT > HIGH_RISK >
LOW_COMPLIANCE > CONFIG_GAP > OK — because staleness invalidates every
downstream signal, and a MissionCritical-tier RTO/RPO breach is
qualitatively worse than the same breach on a Standard-tier component.

A Resilience Hub assessment is a **point-in-time snapshot**, not a live
view. The compliance score, the per-component compliance map, and the
recommendation list are all frozen at `assessment.endTime`. Three facts
follow from this that a generic auditor misses:

- An assessment older than 90 days reflects an infrastructure state that
  almost certainly no longer exists. Its compliance score is not "the app's
  compliance" — it is "the app's compliance three months ago". Treat it as
  historical, not current.
- `appVersion` drift means the published app version has advanced since the
  assessment ran. The assessment results reference a version that is no
  longer the current one — the compliance map may omit resources added in
  the newer version and include resources that were removed.
- A `PolicyCompliant` assessment does NOT mean the application is resilient.
  It means the application meets **the policy's** RTO/RPO targets. If the
  policy itself is miscalibrated (e.g., a MissionCritical tier with a 24-hour
  RTO), a perfect score merely proves the app meets a broken target. The
  policy must be validated before the compliance score is trusted.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| Latest `assessmentStatus` is `Failed`, `Pending`, or `InProgress` | **CONFIG_GAP** | Step 1 |
| No successful assessment has ever run for the app | **CONFIG_GAP** | Step 1 |
| Latest successful assessment `endTime` > 90 days from today | **STALE_ASSESSMENT** | Step 2 |
| Any `MissionCritical` or `Critical` tier component is `NonCompliant` | **HIGH_RISK** | Step 5a |
| `complianceScore` < 50 (systemic failure) | **HIGH_RISK** | Step 5b |
| `complianceScore` < 80 (and not HIGH_RISK) | **LOW_COMPLIANCE** | Step 6 |
| App has no resiliency policy attached (`policyArn` is null) | **CONFIG_GAP** | Step 4 |
| `appVersion` in assessment differs from current app version | **CONFIG_GAP** (additive) | Step 3 |
| Policy tier and RTO/RPO targets are inconsistent (e.g., MissionCritical + 24h RTO) | **CONFIG_GAP** (additive) | Step 4 |
| Unimplemented `Alarm` recommendations with count > 0 | **CONFIG_GAP** (additive) | Step 7 |
| All dimensions pass, score >= 80, policy attached, no drift | **OK** | Step 8 |

See the ordered steps below for edge cases and precedence. Deep Resilience
Hub internals (API quirks, recommendation semantics, assessment lifecycle)
are in the [Deep reference](#deep-reference-resilience-hub-internals)
section at the end.

## Pre-flight: app and assessment metadata gate

Before evaluating compliance, classify the assessment itself. Several
assessment-level attributes **short-circuit** the audit — classifying them
wrong produces false confidence in stale or absent data.

**Multi-app / account-wide sweep note (pagination):** when auditing every
app in an account, `aws resiliencehub list-apps --max-results 100` pages via
`--next-token`. For each app, retrieve the LATEST assessment with
`aws resiliencehub list-app-assessments --app-arn <arn> --reverse-order
--max-results 1`. **The `--reverse-order` flag is mandatory** — without it,
`--max-results 1` returns the OLDEST assessment (chronological order is the
default), and the auditor silently classifies a months-old baseline as the
current state. Always drain `--next-token` to completion on both calls.

**Live-account pre-flight checks (skip if doing offline snapshot audit):**
1. Verify the caller's identity can run
   `resiliencehub:StartAppAssessment` if remediation is intended — most
   read-only auditor roles CANNOT, and re-assessment commands will fail
   with `AccessDeniedException`. Surface this BEFORE the operator approves
   a re-run.
2. Confirm the app version is published
   (`aws resiliencehub describe-app --app-arn <arn>` shows `appVersion`).
   An app with draft changes has unpublished resources; the assessment
   covers only the last published version, not the draft.
3. Snapshot the current assessment list BEFORE any change:
   `aws resiliencehub list-app-assessments --app-arn <arn> --output json >
   /tmp/<app>-assessments-backup-$(date +%s).json`. Assessments are
   immutable once complete, but the "latest" pointer moves when a new
   assessment runs — capture the baseline first.

| Attribute | Value | Effect on audit |
|---|---|---|
| `assessmentStatus` | `Failed` | **No compliance data.** The `compliance` map is empty or absent. Jump to Step 1 — emit CONFIG_GAP. Do NOT treat a Failed assessment as "zero compliance" (that would incorrectly produce HIGH_RISK or LOW_COMPLIANCE). |
| `assessmentStatus` | `Pending` / `InProgress` | **Assessment not finished.** No compliance data yet. Emit CONFIG_GAP. |
| `assessmentStatus` | `Success` | Proceed with full audit. |
| `appVersion` (in assessment) | != current app version | **Version drift.** Additive CONFIG_GAP finding (Step 3). The assessment covers a stale version. |
| `policyArn` (on app) | `null` / empty | **No policy bound to the app.** Additive CONFIG_GAP finding (Step 4). The assessment may have used an ad-hoc policy; future assessments could use a different policy, producing inconsistent compliance. |
| `compliance` map | empty (`{}`) on a `Success` assessment | **Anomaly.** A successful assessment with zero components in the compliance map means the app has no resolvable resources. Emit CONFIG_GAP. |
| `driftStatus` | `Drifted` | **Resource drift detected.** The app's resources have changed since the assessment. Additive finding — reinforces staleness even if endTime is recent. |

**If the assessment snapshot is malformed** (invalid JSON, missing
`assessmentStatus`, missing `compliance` map on a Success assessment),
output:

```text
APP: <app-arn>
VERDICT: ERROR
REASON: Assessment snapshot is malformed — assessmentStatus or compliance map is missing. Cannot classify.
REMEDIATION: Re-fetch with `aws resiliencehub describe-app-assessment --assessment-arn <arn> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious Resilience Hub behaviors

These behaviors change a verdict if ignored. Each is a genuine operational
trap that a senior resiliency engineer would catch and a generalist would
not:

- **`list-app-assessments` returns oldest-first by default.** Without
  `--reverse-order`, `--max-results 1` returns the FIRST (oldest)
  assessment, not the latest. An auditor that omits `--reverse-order`
  silently classifies a months-old baseline as the current state. This is
  the single most common Resilience Hub audit error.

- **Assessment results are frozen at `endTime`; they do NOT update in real
  time.** The compliance score reflects the infrastructure as it was when
  the assessment ran. If the app has been modified since (new resources,
  changed components, updated policy), the score is stale regardless of
  its numeric value. A "95" from three months ago is not a current 95.

- **`PolicyCompliant` proves alignment with the policy, NOT actual
  resilience.** A MissionCritical tier with a 24-hour RTO target will report
  `PolicyCompliant` for a workload that takes 20 hours to recover —
  technically compliant, operationally catastrophic. Validate the policy's
  tier-to-RTO/RPO mapping before trusting the compliance score. The
  default tier targets (which the skill checks against) are:
  MissionCritical: RTO 5 min / RPO 5 min; Critical: RTO 1 hr / RPO 15 min;
  Important: RTO 4 hr / RPO 1 hr; Standard: RTO 24 hr / RPO 24 hr;
  NonCritical: RTO 72 hr / RPO 72 hr.

- **`appVersion` drift is silent.** The assessment still shows
  `assessmentStatus: Success`, but its `appVersion` field references an
  older published version. After `publish-app-version`, the version
  increments and old assessments do not update. The only way to detect
  drift is to compare `assessment.appVersion` against `describe-app`'s
  `appVersion`.

- **`publish-app-version` is required before an assessment can run.** An
  app with draft (unpublished) changes cannot be assessed against the
  draft — the assessment runs against the last published version. If the
  operator believes the assessment covers their latest changes but the
  version is stale, the assessment is covering a subset of the app.

- **A `Failed` assessment produces NO compliance data.** The `compliance`
  map is empty or absent. Treating a Failed assessment as "zero compliance"
  (score 0) incorrectly produces HIGH_RISK or LOW_COMPLIANCE — the correct
  verdict is CONFIG_GAP (no data to classify against).

- **Recommendation categories are independent, not interchangeable.**
  `Alarm` recommendations (CloudWatch Composite Alarms) detect metric
  breaches in real time. `SDD` recommendations (Standard Operating
  Procedures, Diagnostics, Design documents) provide operator runbooks.
  `Test` recommendations (fault injection) validate recovery procedures
  under controlled failure. Missing alarms means no automated detection;
  missing SDDs means no manual recovery procedure; missing tests means no
  validated recovery. Each gap has a different operational impact.

- **Recommendations are per-assessment, not cumulative.** Each assessment
  generates its own recommendation set. Implementing recommendations from
  assessment N does not suppress the same recommendation type in
  assessment N+1 — the new assessment re-evaluates from scratch. Track
  implementation status against the LATEST assessment's recommendations
  only.

- **`start-app-assessment` is asynchronous.** It returns immediately with
  `assessmentStatus: Pending`, transitions to `InProgress`, then reaches
  `Success` or `Failed` (minutes to hours depending on app size). An
  assessment in `Pending` or `InProgress` has no compliance data — treat
  as CONFIG_GAP, not as "passing" (a naive auditor might see no
  NonCompliant resources and emit OK).

- **The compliance score is the percentage of assessed application
  components whose computed recovery time/objective meets the policy's
  RTO and RPO targets for their assigned tier.** A component's compliance
  is determined by Resilience Hub's internal simulation (which models
  failure scenarios against the component's infrastructure). The score is
  NOT a simple config check — it reflects simulated recovery performance.
  This means a "low" score is a meaningful resiliency signal, not just a
  configuration issue.

- **An app can be assessed against a policy that is not its own.**
  `start-app-assessment --policy-arn <arn>` accepts any policy ARN. If the
  app's `policyArn` (from `describe-app`) differs from the assessment's
  `policy.policyArn`, the assessment was run with an ad-hoc policy. This
  is not necessarily wrong (e.g., what-if analysis), but it means the
  compliance score does not reflect the app's steady-state target. Flag
  the mismatch as a CONFIG_GAP finding.

### Step 1: Assessment status gate (highest priority — no data = no classification)

If the latest assessment has `assessmentStatus` other than `Success`,
emit **CONFIG_GAP** and stop — there is no compliance data to evaluate:

- `Failed` — the assessment encountered an error (e.g., resource resolution
  failure, internal error). The `compliance` map is empty. Emit CONFIG_GAP
  with finding: "Latest assessment Failed — no compliance data available.
  Re-run the assessment."
- `Pending` or `InProgress` — the assessment has not finished. Emit
  CONFIG_GAP with finding: "Latest assessment is <status> — await
  completion before auditing."

If NO assessment has ever been run for the app (the `list-app-assessments`
response is empty), emit **CONFIG_GAP** with finding: "No assessment has
ever been run for this app — no resiliency baseline exists."

This step runs FIRST because every subsequent step depends on compliance
data. Classifying a Failed assessment as LOW_COMPLIANCE (score 0) is a
false positive — the correct classification is "no data".

### Step 2: Assessment staleness (time-based — invalidates all downstream signals)

If the latest successful assessment's `endTime` is more than **90 days** in
the past relative to today's date, emit **STALE_ASSESSMENT** and stop.

- The 90-day threshold is an operational heuristic, not an API-enforced
  value. AWS recommends re-running assessments after every infrastructure
  change. For production workloads, 90 days is the maximum acceptable gap;
  for MissionCritical workloads, consider 30 days.
- Staleness is evaluated BEFORE compliance because a stale score is
  unreliable — infrastructure changes, new resources, and updated policies
  may have invalidated the results. Reporting "complianceScore: 95" from a
  6-month-old assessment gives false confidence.
- Compute the age as: `today - assessment.endTime` in days. If the input
  provides a day count directly, use it; otherwise compute from the dates.

If the assessment is fresh (<= 90 days), continue to Step 3.

### Step 3: App version drift (additive finding)

Compare `assessment.appVersion` to the app's current `appVersion` (from
`describe-app` or the input metadata):

- **Versions differ** → add a CONFIG_GAP finding: "Assessment references
  appVersion <X> but current app version is <Y>. Resources added, removed,
  or modified since version <X> are not covered by this assessment."
- **Versions match** → OK for this dimension (no finding).

This step produces an ADDITIVE finding — it does not override the
staleness check (Step 2) or the HIGH_RISK/LOW_COMPLIANCE checks (Steps
5-6). Its role is to surface a config gap that would otherwise be
invisible (the assessment shows "Success" but covers a stale version).

### Step 4: Resiliency policy binding and tier sanity

Check the app's policy configuration:

- **App `policyArn` is null or empty** → add a CONFIG_GAP finding: "No
  resiliency policy is bound to this app. The assessment used an ad-hoc
  policy; future assessments may use a different policy, producing
  inconsistent compliance results. Attach a policy with
  `aws resiliencehub put-app-policy` or bind via the console."
- **App has a policy attached** → validate the policy's tier-to-RTO/RPO
  mapping. For each tier defined in the policy, check that the RTO and RPO
  targets are consistent with the tier's semantic meaning:

  | Tier | Expected RTO range | Expected RPO range |
  |---|---|---|
  | MissionCritical | <= 1 hour (default 5 min) | <= 15 min (default 5 min) |
  | Critical | <= 4 hours (default 1 hr) | <= 1 hour (default 15 min) |
  | Important | <= 12 hours (default 4 hr) | <= 4 hours (default 1 hr) |
  | Standard | <= 48 hours (default 24 hr) | <= 48 hours (default 24 hr) |
  | NonCritical | <= 168 hours / 7 days (default 72 hr) | <= 168 hours (default 72 hr) |

  If a tier's RTO or RPO exceeds the upper bound of its expected range,
  add a CONFIG_GAP finding: "Policy tier <tier> has RTO <X> which exceeds
  the expected maximum for this tier (<max>). The tier-to-target mapping
  is miscalibrated — a permissive target on a high tier masks real
  resiliency risk."

This step produces ADDITIVE findings. The policy-binding gap (no policy)
is sufficient on its own to set the final verdict to CONFIG_GAP if no
higher-precedence verdict (STALE_ASSESSMENT, HIGH_RISK, LOW_COMPLIANCE)
applies.

### Step 5: Per-tier RTO/RPO compliance — HIGH_RISK triggers

Evaluate the compliance map for tier-specific breaches:

**Step 5a: MissionCritical or Critical tier breach.** If ANY application
component with tier `MissionCritical` or `Critical` has
`complianceStatus: NonCompliant` (or the equivalent in the compliance
map), emit **HIGH_RISK**. These tiers carry the strictest RTO/RPO targets
and the highest business impact — a single breach means a business-critical
workload cannot meet its recovery objectives.

**Step 5b: Systemic failure.** If `complianceScore` < 50, emit
**HIGH_RISK** regardless of which tiers are breached. A score below 50
means fewer than half the assessed components meet their policy targets —
this is systemic resiliency failure, not an isolated gap.

If neither 5a nor 5b triggers, continue to Step 6.

### Step 6: Aggregate compliance score — LOW_COMPLIANCE trigger

If `complianceScore` < 80 (and Step 5 did not trigger HIGH_RISK), emit
**LOW_COMPLIANCE**. A score between 50 and 80 indicates a meaningful
fraction of components miss their RTO/RPO targets — not systemic failure,
but enough to concern a resiliency reviewer.

- This step runs AFTER Step 5 so that HIGH_RISK takes precedence when the
  score is low AND a critical-tier breach exists. A score of 75 with a
  MissionCritical NonCompliant is HIGH_RISK, not LOW_COMPLIANCE.
- If `complianceScore` >= 80, continue to Step 7 (no LOW_COMPLIANCE).

### Step 7: Recommendation and alarm coverage (additive findings)

Evaluate the recommendation inventory from the assessment. Distinguish
**operational gaps** (verdict-impacting) from **improvement opportunities**
(informational — included in FINDINGS for awareness but does NOT change
the verdict from OK to CONFIG_GAP):

- **Unimplemented `Alarm` recommendations** (count > 0) → add a CONFIG_GAP
  finding: "<N> CloudWatch alarm recommendations are not implemented.
  Without these alarms, metric breaches will not trigger automated
  detection." Unimplemented alarms are the most operationally impactful
  gap — they are the early-warning system. This is verdict-impacting: if
  the only finding is unimplemented alarms, the verdict is CONFIG_GAP.
- **Unimplemented `SDD` recommendations** (count > 0) → add an
  informational finding: "<N> runbook / diagnostic recommendations are
  not implemented." Operators lack documented recovery procedures. This
  is NOT verdict-impacting on its own — an app with all alarms
  implemented but SDD gaps can still be OK (the alarms detect the
  condition; the runbook gap is an improvement opportunity).
- **Unimplemented `Test` recommendations** (count > 0) → add an
  informational finding: "<N> resilience-test recommendations are not
  implemented." Recovery procedures are unvalidated under fault
  injection. NOT verdict-impacting — many healthy production apps do not
  implement every fault-injection test. Flag for awareness, not as a
  config gap.

This operational-vs-improvement distinction is deliberate: alarms are
the automated detection layer (missing alarms means blind spots in
production); SDDs and Tests are maturation layers (missing them means
the recovery process is less practised, not that detection is broken).
An app with perfect compliance, attached policy, no drift, all alarms
implemented, but some unimplemented Tests is OK — the core resiliency
posture is sound.

### Step 8: Aggregation — worst verdict wins

The final verdict is the **maximum-precedence** verdict across all steps,
where the precedence order is:

```
STALE_ASSESSMENT > HIGH_RISK > LOW_COMPLIANCE > CONFIG_GAP > OK
```

```text
verdict = max_precedence(step1_verdict, step2_verdict, step5_or_6_verdict, additive_config_gaps)
```

Only the following conditions produce a CONFIG_GAP verdict:
(1) Failed/Pending/InProgress assessment status (Step 1);
(2) no policy attached to the app (Step 4);
(3) tier-to-RTO/RPO miscalibration in the policy (Step 4);
(4) unimplemented `Alarm` recommendations with count > 0 (Step 7);
(5) appVersion drift, IF no higher-precedence verdict applies (Step 3).

**Unimplemented `SDD` and `Test` recommendations do NOT produce a
CONFIG_GAP verdict.** They are informational findings only. An app with
a fresh assessment, score >= 80, policy attached, no version drift, all
Alarm recommendations implemented, but some unimplemented SDD or Test
recommendations → verdict is **OK**. SDD/Test gaps are improvement
notes, not configuration defects. This distinction is deliberate: alarms
are the automated detection layer (a missing alarm is a production blind
spot); SDDs and Tests are maturation layers (a missing runbook or test
is a process improvement opportunity, not a broken configuration).

If no verdict-impacting condition is met (all dimensions pass, score >=
80, policy attached, no drift, all Alarm recommendations implemented),
the verdict is **OK**.

## Output format (per app)

```text
APP: <app-name or ARN>
VERDICT: STALE_ASSESSMENT | HIGH_RISK | LOW_COMPLIANCE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the triggering step and the worst finding>
FINDINGS:
  - [STALE_ASSESSMENT] <finding description (Step N)>
  - [HIGH_RISK] <finding description (Step Na)>
  - [CONFIG_GAP] <additive finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — MissionCritical breach with fresh assessment

```text
APP: arn:aws:resiliencehub:us-east-1:111111111111:app/payment-processor
VERDICT: HIGH_RISK
REASON: Assessment (5 days old) reports component "payment-api-lambda" in
tier MissionCritical as NonCompliant — the RTO target of 5 minutes is not
met (Step 5a). The aggregate complianceScore is 75, which also falls below
the LOW_COMPLIANCE threshold but is superseded by HIGH_RISK.
FINDINGS:
  - [HIGH_RISK] MissionCritical component "payment-api-lambda" is NonCompliant
    against RTO 5 min / RPO 5 min (Step 5a)
  - [LOW_COMPLIANCE] complianceScore 75 is below 80 (Step 6) — superseded by
    HIGH_RISK; retained as context
  - [OK] Assessment is fresh (5 days old, Step 2)
  - [OK] appVersion matches current version (Step 3)
  - [OK] Resiliency policy is attached and tier-to-RTO/RPO mapping is valid (Step 4)
REMEDIATION:
  1. Investigate the NonCompliant MissionCritical component — review the
     assessment's per-component compliance details for the specific RTO/RPO
     breach. Typically the cause is single-AZ deployment, missing Multi-AZ,
     or no standby capacity.
  2. Re-run the assessment after remediation:
     aws resiliencehub start-app-assessment --app-arn <arn> --app-version <v> \
       --assessment-name post-remediation-$(date +%Y%m%d) --policy-arn <policy>
  3. Implement pending alarm recommendations to detect future breaches.
```

## Edge-case handling

- **Assessment with `compliance` map present but `complianceScore` absent.**
  Compute the score as:
  `(count of components with complianceStatus PolicyCompliant / total components) * 100`.
  If the map is empty on a Success assessment, emit CONFIG_GAP (anomaly —
  successful assessment with zero components means no resolvable resources).

- **Assessment run with a different policy than the app's attached policy.**
  If `assessment.policy.policyArn` differs from the app's `policyArn`,
  add a finding: "Assessment was run with policy <arn> which differs from
  the app's attached policy <arn>. Compliance results may not reflect the
  steady-state target." This is an additive CONFIG_GAP finding — it does
  not override HIGH_RISK or LOW_COMPLIANCE but should be investigated.

- **App with draft (unpublished) changes.** The current `appVersion` is the
  last published version. If the operator mentions recent changes but the
  version is unchanged, those changes are not assessed. Add a finding:
  "App has unpublished changes — run `aws resiliencehub publish-app-version`
  then re-assess to cover the new resources."

- **Multiple assessments, different verdicts.** If the input includes
  multiple assessments, classify each independently and report the LATEST
  successful assessment's verdict as the app's current verdict. Note prior
  assessments in FINDINGS for trend context only.

- **Compliance map uses `PolicyCompliant` / `PolicyNotCompliant` rather
  than `Compliant` / `NonCompliant`.** These are the same concept — the
  API uses `PolicyCompliant` and `PolicyNotCompliant` as the
  `complianceStatus` enum values. Treat `PolicyNotCompliant` as
  `NonCompliant` for all classification purposes.

- **Policy with custom tiers (not in the standard 5).** Resilience Hub
  allows custom tier names. If a policy defines a tier not in the standard
  set (MissionCritical, Critical, Important, Standard, NonCritical), skip
  the tier-sanity check (Step 4) for that tier — the expected RTO/RPO
  ranges apply only to the standard tiers. Still evaluate compliance for
  components assigned to custom tiers in Step 5/6.

- **Zero resources in the app.** An app with no resources produces an
  empty compliance map on a Success assessment. Emit CONFIG_GAP: "App has
  no resolvable resources — add resources via
  `aws resiliencehub create-app-input-source` or
  `aws resiliencehub import-resources-to-protected-app`."

## Anti-Patterns — NEVER

- NEVER treat a `Failed` assessment as "zero compliance." A Failed
  assessment has NO compliance data — the map is empty. Classifying it as
  score 0 incorrectly produces HIGH_RISK or LOW_COMPLIANCE. The correct
  verdict is CONFIG_GAP (no data). This is the most common Resilience Hub
  audit error.

- NEVER report a compliance score from a stale assessment as the app's
  current compliance. A score of 95 from six months ago is a historical
  data point, not a current posture. Always check `endTime` against
  today's date FIRST. If the assessment is stale (> 90 days), emit
  STALE_ASSESSMENT regardless of the score.

- NEVER omit `--reverse-order` when calling
  `list-app-assessments --max-results 1`. Without `--reverse-order`, the
  API returns the OLDEST assessment. The auditor will then classify a
  months-old baseline as the current state. This API quirk is silent —
  the response looks identical to a latest-assessment response.

- NEVER classify a `PolicyCompliant` result as proof that the app is
  resilient without validating the policy. `PolicyCompliant` means the app
  meets the policy's targets. If the policy is miscalibrated (e.g.,
  MissionCritical with a 7-day RTO), the compliance score is measuring
  against a broken yardstick. Always check tier-to-RTO/RPO consistency
  (Step 4) before trusting the score.

- NEVER treat `Pending` or `InProgress` assessments as "passing." An
  assessment that has not finished has no compliance data. A naive auditor
  sees zero NonCompliant components and emits OK — the correct verdict is
  CONFIG_GAP (assessment not complete).

- NEVER assume `appVersion` in the assessment matches the current app
  version. After `publish-app-version`, the version increments and old
  assessments do not update. Always compare
  `assessment.appVersion` against the current `appVersion` from
  `describe-app`. A mismatch means the assessment covers a stale version
  of the app.

- NEVER equate a missing explicit `complianceScore` field with a zero
  score. Some API responses omit the score field. Compute it from the
  compliance map: `(PolicyCompliant count / total components) * 100`. A
  missing field is a serialization choice, not a zero score.

- NEVER treat recommendation categories as interchangeable. `Alarm`
  recommendations are the early-warning system (CloudWatch alarms);
  `SDD` recommendations are operator runbooks; `Test` recommendations are
  validated recovery procedures. Missing alarms is the most operationally
  critical gap. Do not collapse them into a single "recommendations"
  count.

- NEVER recommend running `start-app-assessment` without confirming the
  app version is current. If the app has unpublished changes, the
  assessment will run against the OLD version. Publish first:
  `aws resiliencehub publish-app-version --app-arn <arn>`, then assess.

- NEVER ignore policy-attachment status. An app without a bound policy
  (`policyArn: null`) may have been assessed with an ad-hoc policy. Future
  assessments could use a different policy, producing incomparable
  compliance scores. Always flag a null `policyArn` as CONFIG_GAP.

- NEVER classify an app as CONFIG_GAP solely because of unimplemented SDD
  or Test recommendations. SDD gaps (missing runbooks) and Test gaps
  (missing fault-injection tests) are improvement opportunities, not
  configuration defects. Only unimplemented **Alarm** recommendations
  produce a CONFIG_GAP verdict (missing alarms = production blind spots).
  An otherwise-clean app with all alarms implemented but some unimplemented
  SDDs/Tests is OK — the core resiliency posture is sound.

- NEVER treat `driftStatus: Drifted` as equivalent to `appVersion` drift.
  `driftStatus` reflects resource-level changes (resources added/removed
  since the assessment); `appVersion` drift reflects a published version
  increment. Both are staleness signals, but they have different causes
  and different remediation paths (drift requires re-assessment; version
  drift requires re-publish and re-assessment).

- NEVER suppress a LOW_COMPLIANCE finding when HIGH_RISK triggers. The
  LOW_COMPLIANCE finding provides context (the score is low) even though
  the verdict is HIGH_RISK (the worse finding). Omitting it hides the
  aggregate signal from the operator. Include it as a contextual finding,
  clearly marked as superseded.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`start-app-assessment`, `publish-app-version`, `put-app-policy`,
  `delete-app-assessment`), the auditor MUST emit:
  `CONFIRM: About to <action> on app <arn> (version <v>). This affects
  <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. This gate
  prevents automated pipelines from silently triggering assessments or
  publishing versions.
- Confirm the app exists and is accessible:
  `aws resiliencehub describe-app --app-arn <arn> --profile <p>` — fail
  closed (skip remediation) if it returns an error.
- Before starting a new assessment, verify the app version is current:
  `aws resiliencehub describe-app --app-arn <arn>` — if
  `evaluationLimitExceeded` is true, resolve the limit before assessing.
- Before publishing a new version, confirm no other version is mid-publish:
  check `describe-app` for `status: Administering`. Publishing over an
  in-flight publish can corrupt the version state.
- Capture the current assessment list for rollback:
  `aws resiliencehub list-app-assessments --app-arn <arn> --output json >
  /tmp/<app>-assessments-$(date +%s).json` BEFORE triggering a new
  assessment. The "latest" pointer moves irreversibly when a new
  assessment starts.
- Prefer additive changes (implement an alarm recommendation) over
  destructive changes (delete an old assessment). Deleting an assessment
  removes historical compliance context — keep old assessments for trend
  analysis.

## Remediation guidance

### For STALE_ASSESSMENT

1. Re-run the assessment against the current app version:
   ```bash
   aws resiliencehub start-app-assessment \
     --app-arn <arn> --app-version <current-version> \
     --assessment-name fresh-$(date +%Y%m%d) \
     --policy-arn <policy-arn> --profile <p>
   ```
2. Before re-running, confirm the app version is current (Step 3). If the
   app has unpublished changes, publish first:
   `aws resiliencehub publish-app-version --app-arn <arn>`.
3. For MissionCritical workloads, schedule recurring assessments (weekly
   or bi-weekly). Resilience Hub does not auto-schedule — use EventBridge
   or a CI/CD pipeline trigger.
4. After the new assessment completes (Success), re-audit to confirm the
   fresh verdict.

### For HIGH_RISK — MissionCritical/Critical tier breach (Step 5a)

1. Review the per-component compliance details in the assessment:
   `aws resiliencehub describe-app-assessment --assessment-arn <arn>`.
   Identify the specific RTO/RPO target that the NonCompliant component
   missed.
2. Typical root causes: single-AZ deployment, missing Multi-AZ, no
   standby/replica capacity, missing auto-failover, or insufficient
   monitoring coverage. Apply the infrastructure fix.
3. Implement any pending `Alarm` recommendations for the NonCompliant
   component — alarms detect the breach in real time.
4. Re-run the assessment after remediation (see STALE_ASSESSMENT
   remediation for the CLI).

### For HIGH_RISK — systemic low score (Step 5b, score < 50)

1. This indicates systemic resiliency failure — multiple components across
   multiple tiers miss their targets. Prioritise by tier: fix
   MissionCritical/Critical breaches first, then Important, then Standard.
2. Review the resiliency policy — if the targets are intentionally strict,
   the low score is a real finding. If the targets were aspirational and
   never achievable, recalibrate the policy (but document the trade-off).
3. Implement `SDD` recommendations for recovery procedures before
   attempting `Test` recommendations — operators need runbooks before
   tests can validate them.

### For LOW_COMPLIANCE

1. Review which components are NonCompliant and their tiers. Standard or
   NonCritical tier breaches are lower priority but still warrant
   remediation.
2. Implement `Alarm` recommendations first — they provide ongoing
   detection of the conditions that produced the NonCompliant result.
3. Schedule a re-assessment after implementing remediation. Do NOT
   change the policy targets to make the score look better — that is
   compliance theatre, not resiliency improvement.

### For CONFIG_GAP

- **No assessment ever run:** start the first assessment:
  `aws resiliencehub start-app-assessment --app-arn <arn> --app-version <v>
  --policy-arn <policy> --assessment-name baseline`.
- **Failed assessment:** review the failure reason in
  `describe-app-assessment --assessment-arn <arn>`. Common causes:
  unresolved CloudFormation stacks, missing IAM permissions for resource
  enumeration, or app resources in unsupported Regions. Fix the root cause
  and re-run.
- **No policy attached:** attach a policy:
  `aws resiliencehub put-app-policy --app-arn <arn> --policy-arn <policy>`,
  or create one:
  `aws resiliencehub create-resiliency-policy --policy-name <name>
  --policy '{"MissionCritical":{"rto":300,"rpo":300},...}' --tier MissionCritical`.
- **appVersion drift:** publish the current draft and re-assess:
  `aws resiliencehub publish-app-version --app-arn <arn>` then
  `start-app-assessment`.
- **Unimplemented alarm recommendations:** implement via the recommendation
  template:
  `aws resiliencehub get-recommendation-template --template-arn <arn>`,
  then deploy the CloudWatch composite alarms via CloudFormation.

### For OK

1. No remediation required for the current posture.
2. Recommend scheduling the next assessment within 90 days (or 30 days for
   MissionCritical workloads).
3. Verify any `Test` recommendations are implemented — even an OK app
   should validate its recovery procedures periodically.
4. Review the resiliency policy annually to ensure tier-to-RTO/RPO targets
   match evolving business requirements.

## Deep reference: Resilience Hub internals

### Assessment lifecycle

`start-app-assessment` is asynchronous. The lifecycle is:

1. `Pending` — the assessment is queued. No compliance data.
2. `InProgress` — Resilience Hub is resolving resources, running
   simulations, and computing compliance. No compliance data.
3. `Success` — the assessment completed. The `compliance` map is populated.
4. `Failed` — the assessment encountered an error. The `compliance` map is
   empty. The `complianceStatus` on the assessment is absent.

Only `Success` assessments carry compliance data. Every other state
produces CONFIG_GAP.

### `list-app-assessments` ordering

The API returns assessments in chronological order (oldest first) by
default. The `--reverse-order` (`--reverse-order` / `reverseOrder=true`)
flag reverses to newest-first. To retrieve the LATEST assessment:

```bash
aws resiliencehub list-app-assessments \
  --app-arn <arn> --reverse-order --max-results 1 --profile <p>
```

Without `--reverse-order`, `--max-results 1` returns the OLDEST assessment.
This is the most common API misuse in Resilience Hub auditing.

### Policy tiers and default targets

| Tier | Default RTO | Default RPO | Semantic meaning |
|---|---|---|---|
| MissionCritical | 5 min | 5 min | Revenue-critical, customer-facing, unrecoverable brand damage if down |
| Critical | 1 hr | 15 min | Core business function, significant revenue/impact if down |
| Important | 4 hr | 1 hr | Important workload, moderate impact if down |
| Standard | 24 hr | 24 hr | Standard workload, tolerable overnight recovery |
| NonCritical | 72 hr | 72 hr | Non-critical, can wait days for recovery |

A policy that assigns a tier but overrides the default RTO/RPO is valid
only if the override is stricter (lower) than the default. A permissive
override (e.g., MissionCritical with 24-hour RTO) indicates the tier
label does not match the business criticality — flag as miscalibrated.

### Recommendation taxonomy

| Category | What it covers | Operational impact if missing |
|---|---|---|
| `Alarm` | CloudWatch Composite Alarms that detect RTO/RPO-relevant metric breaches | No automated detection of resiliency-relevant conditions (high latency, error rates, failover gaps) |
| `SDD` | Standard Operating Procedures (runbooks), Diagnostic procedures, Design documents | Operators lack documented recovery procedures; recovery depends on tribal knowledge |
| `Test` | Fault injection and resilience testing scenarios | Recovery procedures are unvalidated; the first real test is a production outage |

### `appVersion` and `publish-app-version`

An app's resources are versioned. `publish-app-version` creates an
immutable snapshot of the app's resource mappings. Assessments run against
a specific published version — not the live draft. The workflow is:

1. Add/remove resources (`create-app-input-source`,
   `import-resources-to-protected-app`).
2. Publish a new version (`publish-app-version`). The version increments.
3. Run assessment against the new version (`start-app-assessment
   --app-version <new>`).

If step 2 is skipped, the assessment runs against the OLD version, missing
any resources added in step 1.

### `driftStatus` vs `appVersion` drift

These are distinct signals:

- **`appVersion` drift** (Step 3) — the published version number has
  advanced since the assessment. The assessment references version N; the
  current published version is N+1. Remediation: re-assess against the
  current version.
- **`driftStatus: Drifted`** — Resilience Hub has detected that the app's
  resources have changed since the assessment, even if the version number
  has not advanced (e.g., a CloudFormation stack managed by the app was
  updated out-of-band). Remediation: re-resolve resources and re-assess.

Both are staleness signals, but they have different root causes and
different detection paths.

## Recent AWS features (2024-2026)

- **Resilience Hub Terraform support (2024):** Resilience Hub now supports Terraform as an app template source. Auditors should verify that the Terraform template version matches the deployed infrastructure — template drift means the assessment does not reflect reality.
- **Enhanced assessment scheduling (2024-2025):** Improved assessment scheduling with scheduled re-assessment and drift detection. Auditors should verify that assessments are scheduled to re-run after infrastructure changes, not just on a fixed calendar.
- **New resiliency policy tiers:** Additional policy tiers and RTO/RPO calibration options. Auditors should verify that the resiliency policy matches the application's actual business-criticality tier.
- **Integration with Amazon Q (2024-2025):** AI-driven resiliency recommendations. No new audit-surface fields.

## Domain

AWS CloudOps / Resilience Hub Application Resiliency & Compliance.

## AWS documentation

- **AWS Resilience Hub User Guide** — https://docs.aws.amazon.com/resilience-hub/latest/userguide/what-is.html
- **Resilience Hub Security** — https://docs.aws.amazon.com/resilience-hub/latest/userguide/security.html
- **Resilience Hub API Reference** — https://docs.aws.amazon.com/resilience-hub/latest/APIReference/
- **Resilience Hub CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/resiliencehub/
