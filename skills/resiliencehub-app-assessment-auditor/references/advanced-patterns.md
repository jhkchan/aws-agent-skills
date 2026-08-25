# Advanced Patterns — Resilience Hub App Assessment Auditor

Expert-knowledge deep dives, edge cases, and internals moved out of the SKILL.md body. Loaded on demand.


## Step 0: Expert knowledge — non-obvious Resilience Hub behaviors

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
