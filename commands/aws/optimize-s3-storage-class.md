---
description: Optimises S3 storage cost across six dimensions — lifecycle policy deployment (Standard to Standard-IA to Glacier Instant Retrieval to Glacier Flexible to Deep Archive with minimum-days constraints), Intelligent-Tiering activation with Archive Access and Deep Archive Access tiers, Storage Lens analysis for object-age distribution and prefix-level cost allocation, versioning cost impact (noncurrent object churn and delete marker accumulation), retrieval-pattern matching (Glacier Instant vs Flexible vs Deep Archive trade-offs), and S3 Batch Operations for bulk storage-class migration. Emits FURTHER_OPTIMIZATION_AVAILABLE, OPTIMIZED, or ALREADY_OPTIMAL per bucket with per-TB savings.
nl_triggers:
  - "optimise S3 storage cost"
  - "S3 lifecycle policy"
  - "S3 Intelligent-Tiering"
  - "S3 Glacier migration"
  - "S3 Deep Archive"
  - "S3 Storage Lens analysis"
  - "S3 versioning cost"
  - "S3 noncurrent objects"
  - "S3 Batch Operations"
  - "S3 cost per TB"
  - "S3 Standard-IA transition"
  - "S3 delete marker cleanup"
  - "S3 prefix cost allocation"
  - "S3 FinOps review"
  - "reduce S3 bill"
  - "S3 storage class review"
  - "Glacier Instant Retrieval vs Deep Archive"
routes_to: s3-storage-class-optimizer
---

# /aws:optimize-s3-storage-class

Activate the `s3-storage-class-optimizer` skill and optimise S3 bucket
storage cost across the six-dimension analysis framework.

## What it does

Reads a bucket's storage-class distribution, object-age profile, and
versioning configuration (Storage Lens, Cost Explorer S3 usage types,
lifecycle config, Intelligent-Tiering config, versioning status) then
applies the ordered optimisation logic:

1. **Pre-flight** — data sufficiency gate. If Storage Lens data absent
   or observation window < 30 days, emit NEED_MORE_INFO.
2. **Lifecycle policy** — no policy with >20% of objects >30 days in
   Standard → deploy lifecycle (Standard→IA 30d, GIR 90d, DA 180d).
3. **Intelligent-Tiering** — unpredictable access patterns with no IT
   → enable IT with Archive Access at 90d and Deep Archive Access at
   180d. Verify monitoring fee break-even (>1 TB).
4. **Versioning bloat** — versioned bucket with noncurrent versions
   >10% of total → add noncurrent-version transitions + expirations.
5. **Retrieval-pattern matching** — archive tier retrieval >10% of
   archive per month → retrieval mismatch; move to warmer tier.
6. **IA mismatch** — Standard-IA objects accessed >2x/month → move
   back to Standard (retrieval fee exceeds storage delta).
7. **S3 Batch Operations** — existing aged objects in Standard →
   immediate bulk migration to correct tier via Batch Ops COPY.
8. **Verdict** — FURTHER_OPTIMIZATION_AVAILABLE (any dimension has a
   recommendation), OPTIMIZED (applied and verified), or
   ALREADY_OPTIMAL (no change needed).

Emits a deterministic optimisation block per bucket:

```text
TARGET: <bucket-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <TB by class>, <versioning>, <lifecycle>, <IT config>
  Proposed: <TB by class>, <new lifecycle>, <new IT config>
  Confidence: <HIGH/MEDIUM/LOW>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a bucket configuration and ask any of:

- "should I deploy lifecycle policies?"
- "is Intelligent-Tiering worth it for this bucket?"
- "why is our S3 bill so high?"
- "are my versioning rules leaking storage?"
- "is Deep Archive the right tier for this data?"
- "should I use Glacier Instant or Deep Archive?"
- "can I batch-migrate objects to a cheaper class?"
- "S3 FinOps review"

A bare bucket name + any optimise verb ("optimise this bucket",
"reduce S3 storage cost") also routes here via the orchestrator.

## Inputs

- Bucket metadata: bucket name/ARN, region, storage-class distribution,
  versioning status, lifecycle config, Intelligent-Tiering config.
- Storage Lens (last 30-90 days): object-age distribution by band,
  noncurrent version storage, incomplete multipart uploads, delete
  marker count, retrieval activity by class.
- Cost Explorer (optional but HIGH confidence requires it): S3 usage
  type breakdown (StorageUsage, RequestUsage, DataTransferOut, etc.).
- Workload context: predictable vs unpredictable access, compliance
  retention, retrieval SLA.

## Outputs

- One optimisation block per bucket.
- Confidence level with rationale (HIGH requires Storage Lens + CE).
- Estimated monthly and annual savings, per-TB breakdown.
- Specific migration steps with CLI commands (put-bucket-lifecycle-
  configuration, put-bucket-intelligent-tiering-configuration,
  create-job for Batch Operations).
- Retrieval-cost risk assessment if recommending any archive tier.
- A CONFIRM gate before any state-changing CLI.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 3 Optimize specialist for S3 storage cost).
- `/aws:optimize-rds-cost` for database cost optimisation (sibling
  optimize skill).
- `/aws:troubleshoot-s3-access` for S3 access troubleshooting (this
  skill is cost-focused, not access-focused).
