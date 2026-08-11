---
description: >-
  Optimise S3 storage cost with Intelligent-Tiering — enable
  bucket-level IntelligentTieringConfiguration, tune Archive Access
  (90-day) and Deep Archive Access (180-day) tiers, model the
  $0.0025/1,000-objects monitoring fee, and emit a deterministic
  VERDICT with the exact put-bucket-intelligent-tiering-configuration
  payload and net dollar savings estimate.
nl_triggers:
  - "enable S3 Intelligent-Tiering"
  - "Intelligent-Tiering monitoring fee"
  - "S3 Intelligent-Tiering vs lifecycle"
  - "S3 archive tier configuration"
  - "S3 Deep Archive Access tier"
  - "S3 access pattern analysis"
  - "should I use Intelligent-Tiering"
  - "IntelligentTieringConfiguration"
  - "put-bucket-intelligent-tiering-configuration"
  - "S3 small object fee aggregation"
  - "S3 storage cost optimization"
  - "reduce S3 bill with Intelligent-Tiering"
routes_to: s3-intelligent-tiering-optimizer
---

# /aws:optimize-s3-intelligent-tiering

Activate the `s3-intelligent-tiering-optimizer` skill and optimise an S3
bucket for Intelligent-Tiering eligibility, archive-tier tuning, and net
dollar savings after the monitoring-fee gate.

## What it does

Reads a bucket configuration (existing IntelligentTieringConfiguration,
Storage Lens metrics summary, object-size distribution, access-pattern
trend) and applies the priority-ordered dimension analysis:

1. Pre-flight bucket metadata gate — short-circuit directory buckets
   (no Intelligent-Tiering support), S3 Tables prefixes (managed via
   table APIs), Object Lock conflicts (archive tiers defeat retrieval
   SLA), and malformed input.
2. Eligibility gate (Step 1) — resolve directory buckets, predictable
   access patterns, and compliance workloads before further analysis.
3. Monitoring-fee gate (Step 2) — the $0.0025/1,000-objects fee must
   not exceed the transition saving. Mandatory for small/many-object
   buckets.
4. Archive-tier tuning (Step 3) — most under-configured Intelligent-
   Tiering setups use defaults only; Archive Access at 90d and Deep
   Archive Access at 180d are tunable.
5. Intelligent-Tiering-vs-lifecycle trade-off (Step 4) — for predictable
   access patterns a fixed lifecycle rule is cheaper (no monitoring fee).
6. Aggregation (Step 5) — emit the highest-leverage recommendation.

Emits a deterministic VERDICT per bucket:

```text
BUCKET: <bucket-name>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences citing the highest-leverage dimension and step number>
RECOMMENDATION: <IntelligentTieringConfiguration JSON or "No changes required">
SAVINGS:
  CURRENT_MONTHLY: $<X.XX>
  PROJECTED_MONTHLY: $<Y.YY>
  MONTHLY_SAVING: $<X.XX - Y.YY>
  ANNUAL_SAVING: $<12 × monthly>
  CAVEATS: <monitoring-fee math, archive-tier minimums, retrieval fees>
IMPLEMENTATION: <exact put-bucket-intelligent-tiering-configuration CLI + verification>
```

## When to invoke

Paste a bucket configuration (or just a bucket name) and ask any of:

- "should I enable Intelligent-Tiering on this bucket?"
- "how much would I save with Intelligent-Tiering?"
- "is the monitoring fee worth it for my bucket?"
- "configure Archive Access and Deep Archive Access tiers"
- "my access pattern is mixed — what's the right tier?"
- "is Intelligent-Tiering or a lifecycle policy cheaper?"
- "this bucket has predictable daily access — Intelligent-Tiering?"

A bare bucket name + any Intelligent-Tiering verb ("enable Intelligent-
Tiering", "optimise with Intelligent-Tiering") also routes here via the
orchestrator.

## Inputs

- Bucket configuration: existing IntelligentTieringConfiguration
  (`list-bucket-intelligent-tiering-configurations`), lifecycle
  (`get-bucket-lifecycle-configuration`), Object Lock
  (`get-object-lock-configuration`).
- S3 Storage Lens summary (last 30+ days): object-size distribution,
  tier distribution, access-pattern trend, average object age.
- For savings estimates: total current GB, current storage-class mix,
  object count (for the monitoring-fee gate), intended access pattern.
- For directory buckets (S3 Express One Zone): bucket name suffix
  `--x-s3` signals no Intelligent-Tiering support; verdict is
  ALREADY_OPTIMAL for ML/AI.

## Outputs

- One VERDICT block per bucket.
- A full `put-bucket-intelligent-tiering-configuration` payload with
  Tierings (Archive Access and/or Deep Archive Access with the correct
  Days values).
- A dollar savings estimate with explicit caveats: monitoring-fee math,
  archive-tier minimum-duration charges, retrieval fees.
- Implementation steps including optional S3 Batch Operations backfill
  for immediate migration of existing objects.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 3 Optimize specialist for S3 Intelligent-Tiering).
- `/aws:optimize-s3-lifecycle` for the sibling lifecycle optimiser —
  use when the access pattern is predictable (no monitoring fee) or
  when expiration / noncurrent-version cleanup is needed
  (Intelligent-Tiering does not handle either).
