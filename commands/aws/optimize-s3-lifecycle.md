---
description: Optimise S3 storage cost through lifecycle-policy design, storage-class selection, and access-pattern analysis. Emits a deterministic VERDICT, lifecycle JSON, and dollar savings estimate per bucket.
nl_triggers:
  - "optimise S3 storage cost"
  - "design S3 lifecycle policy"
  - "S3 storage class analysis"
  - "move S3 data to Glacier"
  - "S3 Intelligent-Tiering vs Standard-IA"
  - "prune noncurrent S3 versions"
  - "abort stale S3 multipart uploads"
  - "S3 Object Lock retention"
  - "S3 lifecycle transition rules"
  - "S3 cost optimization review"
  - "Glacier Deep Archive lifecycle"
  - "S3 Batch Operations storage class"
  - "reduce S3 bill"
  - "S3 versioning cleanup"
routes_to: s3-lifecycle-optimizer
---

# /aws:optimize-s3-lifecycle

Activate the `s3-lifecycle-optimizer` skill and design a cost-optimised
lifecycle policy for one or more S3 buckets, with a dollar savings estimate
and the exact `put-bucket-lifecycle-configuration` payload.

## What it does

Reads a bucket configuration (versioning status, current lifecycle, Storage
Lens metrics summary, multipart-upload inventory, Object Lock posture) and
applies the priority-ordered dimension analysis:

1. Pre-flight bucket metadata gate — short-circuit directory buckets (no
   lifecycle support), S3 Tables prefixes (managed via table APIs), Object
   Lock conflicts (retention beats expiration), and malformed input.
2. Noncurrent-version cleanup (versioned buckets) — typically the largest
   hidden line on long-lived buckets.
3. Multipart-upload cleanup — silent cost leak, free to fix.
4. Storage-class transitions for current objects — the headline saving,
   archetype-matched (logs, compliance archive, application data, backup/DR,
   ML/AI corpus).
5. Expiration for compliance or log workloads — stops the bleed at source.
6. Object Lock / retention posture — compliance control alongside lifecycle.
7. Aggregation — emit the highest-leverage recommendation across all
   applicable dimensions.

Emits a deterministic VERDICT per bucket:

```text
BUCKET: <bucket-name>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences citing the highest-leverage dimension and step number>
RECOMMENDATION: <lifecycle configuration JSON or "No changes required">
SAVINGS:
  CURRENT_MONTHLY: $<X.XX>
  PROJECTED_MONTHLY: $<Y.YY>
  MONTHLY_SAVING: $<X.XX - Y.YY>
  ANNUAL_SAVING: $<12 × monthly>
  CAVEATS: <minimum-duration charges, retrieval fee warnings, monitoring fees>
IMPLEMENTATION: <exact put-bucket-lifecycle-configuration CLI + verification>
```

## When to invoke

Paste a bucket configuration (or just a bucket name) and ask any of:

- "design a lifecycle policy for this bucket"
- "how much would I save moving to Glacier?"
- "should I use Intelligent-Tiering or Standard-IA?"
- "why is my S3 bill so high?"
- "clean up noncurrent versions"
- "abort stale multipart uploads"
- "is this bucket already optimal?"

A bare bucket name + any optimise verb ("optimise this bucket", "reduce S3
cost") also routes here via the orchestrator.

## Inputs

- Bucket configuration: versioning status (`get-bucket-versioning`),
  current lifecycle (`get-bucket-lifecycle-configuration`), Object Lock
  (`get-object-lock-configuration`), multipart-upload inventory
  (`list-multipart-uploads`).
- S3 Storage Lens summary (last 30+ days): noncurrent-byte %, storage-class
  distribution, object-age histogram, access-pattern trend.
- For savings estimates: total current GB, current storage-class mix,
  intended access pattern (daily, monthly, quarterly, archive).
- For directory buckets (S3 Express One Zone): bucket name suffix `--x-s3`
  signals no-lifecycle support; verdict is ALREADY_OPTIMAL for ML/AI.

## Outputs

- One VERDICT block per bucket.
- A full `put-bucket-lifecycle-configuration` payload combining all
  applicable rules (noncurrent cleanup, multipart abort, transitions,
  expiration).
- A dollar savings estimate with explicit caveats: minimum-duration
  charges, Intelligent-Tiering monitoring fees, Glacier retrieval fees.
- Implementation steps including optional S3 Batch Operations backfill for
  immediate migration of existing objects.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for S3 storage cost optimisation).
- `/aws:audit-ebs-volume` for the block-storage cost-optimisation sibling
  — EBS and S3 are typically the two largest storage lines in an AWS bill.
- `/aws:audit-dlm-lifecycle-policy` for the EBS-snapshot lifecycle side,
  which pairs with S3 lifecycle for full storage-tier governance.
