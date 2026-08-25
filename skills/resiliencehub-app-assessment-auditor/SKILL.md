---
name: resiliencehub-app-assessment-auditor
description: Audits AWS Resilience Hub application assessments for assessment staleness (older than 90 days), resiliency policy binding and tier-to-RTO/RPO calibration, per-tier compliance breaches (MissionCritical or Critical NonCompliant triggers HIGH_RISK), aggregate compliance score below 80 (LOW_COMPLIANCE), app-version drift since the last assessment, failed or pending assessment status (no compliance data), and unimplemented alarm / SDD / test recommendations. Emits a deterministic verdict (STALE_ASSESSMENT | HIGH_RISK | LOW_COMPLIANCE | CONFIG_GAP | OK) per app with enumerated findings and CLI remediation. Use when reviewing Resilience Hub app assessments, checking RTO/RPO compliance, validating resiliency policy coverage, or auditing assessment freshness before a production launch.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline assessment-document classification. Live-account audits use aws resiliencehub list-app-assessments, describe-app-assessment, describe-app, list-resiliency-policies, and describe-resiliency-policy (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  verdict_shape: STALE_ASSESSMENT | HIGH_RISK | LOW_COMPLIANCE | CONFIG_GAP | OK
  when_to_use: Reviewing a Resilience Hub app assessment before production launch, checking RTO/RPO compliance against a resiliency policy, auditing assessment freshness, validating that the app version has not drifted since the last assessment, or confirming alarm/SDD/test recommendation coverage.
  activation_triggers: audit this resilience hub assessment, is my app assessment stale, check RTO RPO compliance, resiliency policy coverage, assessment freshness check, app version drift resilience hub, compliance score too low, MissionCritical tier non compliant, resilience hub recommendations, resiliency policy not attached
  invocation_schema: 'Input: either (a) a Resilience Hub app-assessment snapshot (assessment metadata + compliance map + policy + recommendations), optionally paired with describe-app metadata, OR (b) an app-ARN for live-account audit. Output: deterministic APP/VERDICT/REASON/FINDINGS/REMEDIATION block per app, where VERDICT is one of STALE_ASSESSMENT, HIGH_RISK, LOW_COMPLIANCE, CONFIG_GAP, OK, or ERROR.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Resilience Hub, app assessment, RTO, RPO, resiliency policy, compliance score, MissionCritical, Critical tier, NonCompliant, assessment staleness, app version drift, alarm recommendations, SDD recommendations, resiliency audit, compliance breach, assessment freshness, publish-app-version, start-app-assessment, policy binding, resiliency tier
  tags: resiliencehub, management, resiliency, rto, rpo, compliance, assessment, audit
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
> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#live-account-pre-flight-checks).
> Three live-account checks: caller identity, published app version, assessment-list snapshot.

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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-0-expert-knowledge--non-obvious-resilience-hub-behaviors).
> Eleven non-obvious API behaviors (ordering, freezing, policy semantics) that change verdicts.

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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#edge-case-handling).
> Seven input anomalies: missing score, ad-hoc policy, drafts, multiple assessments, enum aliases, custom tiers, zero resources.

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

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#pre-flight-safety-checks-run-before-any-remediation-cli).
> MANDATORY confirmation gate plus describe-app, version, publish-state, and rollback-snapshot checks.

## Remediation guidance

> Moved to [references/remediation-guidance.md](references/remediation-guidance.md#remediation-guidance).
> Per-verdict remediation playbooks: STALE_ASSESSMENT, HIGH_RISK (5a/5b), LOW_COMPLIANCE, CONFIG_GAP, OK.

## Deep reference: Resilience Hub internals

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#deep-reference-resilience-hub-internals).
> Assessment lifecycle, list ordering, tier targets, recommendation taxonomy, versioning, drift semantics.

## Recent AWS features (2024-2026)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#recent-aws-features-2024-2026).
> Terraform sources, scheduling, new tiers, Amazon Q integration.

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — Step-0 expert behaviors, edge cases, deep internals, recent features
- [diagnostic-commands](references/diagnostic-commands.md) — live-account pre-flight and pre-remediation safety checks
- [remediation-guidance](references/remediation-guidance.md) — per-verdict remediation playbooks

## Domain

AWS CloudOps / Resilience Hub Application Resiliency & Compliance.

## AWS documentation

- **AWS Resilience Hub User Guide** — https://docs.aws.amazon.com/resilience-hub/latest/userguide/what-is.html
- **Resilience Hub Security** — https://docs.aws.amazon.com/resilience-hub/latest/userguide/security.html
- **Resilience Hub API Reference** — https://docs.aws.amazon.com/resilience-hub/latest/APIReference/
- **Resilience Hub CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/resiliencehub/
