---
description: Optimise Amazon Macie cost through discovery mode selection (automated data discovery vs targeted classification jobs), scan frequency tuning (daily vs weekly for large data lakes), bucket selection (excluding log/archive/known-safe buckets), S3 object sampling vs full scan, custom data identifier regex audit, managed data identifier scope reduction, finding suppression rules, multi-account Macie administrator delegation, and classification export to S3 for Athena batch analysis with monthly savings estimates.
nl_triggers:
  - "optimise Macie cost"
  - "Macie spend too high"
  - "Macie classification job cost"
  - "Macie automated discovery"
  - "Macie targeted classification"
  - "Macie scan frequency"
  - "Macie daily scan cost"
  - "Macie bucket selection"
  - "Macie exclude buckets"
  - "Macie object sampling"
  - "Macie full scan cost"
  - "Macie custom data identifier"
  - "Macie managed data identifier"
  - "Macie suppression rules"
  - "Macie finding suppression"
  - "Macie delegated administrator"
  - "Macie multi-account"
  - "Macie classification export"
  - "Macie Athena export"
  - "Macie data lake cost"
  - "Macie FinOps"
  - "reduce Macie bill"
  - "security cost review"
routes_to: macie-cost-optimizer
---

# /aws:optimize-macie-cost

Activate the `macie-cost-optimizer` skill and optimize an Amazon Macie
deployment's cost across eight dimensions: discovery mode, scan
frequency, bucket selection, sampling, custom identifiers, managed
identifiers, suppression rules, multi-account delegation, and
classification export pipeline.

## What it does

Reads Macie job configurations, automated discovery status,
classification scope, bucket statistics, Cost Explorer Macie spend,
finding volume, and delegation status, then applies the ordered
optimization logic:

1. **Pre-flight** — data sufficiency gate. If Cost Explorer Macie line
   items are absent, emits NEED_MORE_INFO. If Macie is not enabled,
   emits BLOCKED.
2. **Discovery mode** — automated data discovery manages scope
   incrementally (new/changed objects only); recurring targeted jobs
   re-scan the full included scope every run. Migrate recurring
   coverage to automated discovery; reserve one-time targeted jobs for
   ad-hoc investigations.
3. **Scan frequency tuning** — for targeted jobs that must stay
   targeted, reduce daily to weekly or monthly based on the compliance
   window.
4. **Bucket selection** — exclude log, archive, system, and known-safe
   buckets from the classification scope.
5. **Sampling vs full scan** — Macie samples per bucket by default;
   forcing deep evaluation multiplies per-object cost. Keep default
   sampling unless compliance mandates otherwise.
6. **Custom identifier audit** — consolidate overlapping custom
   identifiers, remove unused ones, audit regex performance for
   catastrophic backtracking.
7. **Managed identifier scope** — narrow `managedDataIdentifierSelector`
   from ALL to INCLUDE with only the compliance-required categories.
8. **Suppression rules** — add finding filters (ARCHIVE action) for
   validated known-safe prefixes to prevent re-evaluation.
9. **Multi-account delegation** — consolidate onto a single delegated
   Macie administrator; avoid per-account standalone Macie on member
   accounts.
10. **Classification export** — pipe classification results to S3 for
    batch Athena analysis instead of re-invoking Macie or paginating
    the findings API.
11. **Impact estimation** — monthly + annual savings, assumptions
    documented.
12. **Verdict** — FURTHER_OPTIMIZATION_AVAILABLE (any dimension has a
    recommendation), OPTIMIZED (all dimensions verified), or
    NEED_MORE_INFO.

Emits a deterministic optimization block per deployment:

```text
TARGET: <macie-deployment-or-job-id>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <discovery mode>, <frequency>, <bucket count>, <identifier scope>, <delegation>
  Proposed: <discovery mode>, <frequency>, <bucket count>, <identifier scope>, <delegation>
  Dimensions changed: <mode | frequency | buckets | sampling | identifiers | suppression | delegation | export>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a Macie deployment's configuration and ask any of:

- "optimise our Macie cost"
- "is this recurring Macie job worth it?"
- "should we switch to automated discovery?"
- "why is our Macie bill so high?"
- "should we exclude these log buckets from Macie?"
- "is managedDataIdentifierSelector: ALL overkill?"
- "how do we reduce Macie finding noise?"
- "Macie fleet cost optimization review"

A bare deployment reference + any optimization verb ("optimize Macie
spend", "security cost review") also routes here via the orchestrator.

## Inputs

- Deployment metadata: Macie account status, delegated administrator
  status, region.
- Classification jobs (last 14-30 days):
  - `jobType` (ONE_TIME | SCHEDULED)
  - `scheduleFrequency` (daily | weekly | monthly)
  - `bucketCriteria` (buckets in scope)
  - `managedDataIdentifierSelector` (ALL | INCLUDE | EXCLUDE)
  - `sampling` configuration
  - `bytesProcessed`, `objectsProcessed`, `jobsRun`
- Automated discovery configuration (enabled/disabled, scope).
- Classification scope (includes/excludes).
- Cost Explorer Macie spend (last 14-30 days).
- Bucket statistics (total count, storage class breakdown).
- Findings volume and recurring-prefix analysis (for suppression
  evaluation).
- Optional: compliance regime (PCI, HIPAA, GDPR) for identifier scope
  decisions.

## Outputs

- One optimization block per deployment or job.
- Confidence level with rationale (HIGH requires job configuration
  citation + Cost Explorer cross-check).
- Estimated monthly and annual savings, broken down by dimension.
- Specific migration steps with CLI commands (update-classification-
  scope, update-classification-job, create-findings-filter, put-
  classification-export-configuration).
- Coverage impact surfaced alongside cost (a mode migration may preserve
  coverage while cutting cost).
- Staged cutover with coverage verification between each phase.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for Macie security data discovery cost).
- `/aws:audit-macie-data-classification` for Macie finding triage and
  data classification review (not cost optimization).
- `/aws:operate-macie-data-discovery` for operating Macie discovery jobs
  (run, monitor, troubleshoot — not cost optimization).
- `/aws:optimize-guarddut-cost` for GuardDuty cost optimization (the
  threat-detection counterpart).
