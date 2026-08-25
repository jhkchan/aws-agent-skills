# Advanced patterns - S3 Intelligent-Tiering Optimizer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Expert knowledge - Step 0 detail

### Step 0: Expert knowledge — non-obvious Intelligent-Tiering behaviors

These behaviors are easy to misjudge without operational S3 experience.
Each changes a recommendation if ignored:

- **The monitoring fee bills ALL objects in the configuration's filter
  scope, not just the ones that tier.** A configuration with
  `Filter: {Prefix: "data/"}` bills $0.0025/1,000 for every object under
  `data/`, even those that never leave the Frequent tier. The fee is the
  cost of access-pattern monitoring — it bills whether or not a tiering
  event occurs.

- **Archive-tier transitions are configurable.** Default: Archive Access
  after 90 consecutive days of no access, Deep Archive Access after 180.
  Override via `Tierings[{AccessTier: ARCHIVE_ACCESS, Days: N}]` where
  N >= 90, and `Tierings[{AccessTier: DEEP_ARCHIVE_ACCESS, Days: N}]`
  where N >= 180. For known-cold data, shorter windows capture savings
  faster.

- **Intelligent-Tiering does not have a minimum-duration charge on
  Frequent/Infrequent tiers.** This is unique among S3 IA-style tiers.
  Standard-IA, One-Zone-IA, and Glacier IR all carry 30/90-day
  minimums. For short-lived unknown-pattern workloads, Intelligent-
  Tiering is cheaper than a lifecycle-driven IA transition that incurs
  the minimum-duration charge.

- **Archive Access and Deep Archive Access tiers DO carry 90/180-day
  minimums.** The Frequent/Infrequent tiers being minimum-free does NOT
  extend to the archive tiers. Always surface the minimum-duration
  caveat on archive-tier recommendations.

- **The Infrequent tier has a 128 KB minimum billable size.** A 4 KB
  object that tiers to Infrequent is billed as 128 KB — a 32x storage-
  cost inflation. This is why the monitoring-fee gate is critical for
  small-object buckets.

- **Intelligent-Tiering tier transitions are not instantaneous.** S3
  evaluates access patterns once daily; tiering transitions occur over
  hours, not minutes. Do not alarm on a 24-hour lag between access
  pattern change and tier movement.

- **A configuration with a filter that matches no objects is silently a
  no-op.** `Filter: {Prefix: "logs/2024/"}` on a bucket where keys live
  under `2025/logs/` matches nothing. Cross-check the prefix against
  the actual key layout before declaring ALREADY_OPTIMAL.

- **Small object fee aggregation (2025-2026 feature).** For buckets
  with very large counts of small objects, AWS can aggregate the
  Intelligent-Tiering monitoring and small-object fees to reduce per-
  object billing overhead. This does NOT remove the monitoring fee —
  it aggregates how the fee is calculated for cost-allocation purposes.
  The monitoring fee still scales with object count; aggregation
  changes the billing presentation, not the cost.

- **Intelligent-Tiering and S3 Lifecycle can coexist on the same bucket
  but should not target the same prefix.** A lifecycle rule that
  transitions `app/logs/` to Standard-IA at 30 days AND an Intelligent-
  Tiering configuration scoped to `app/logs/` will produce unpredictable
  tier movement. Pick one system per prefix.

- **S3 Batch Operations complements Intelligent-Tiering for one-time
  migrations.** To immediately move existing Standard objects INTO
  Intelligent-Tiering (rather than waiting for the configuration to
  apply going forward), use `create-job` with `S3CopyObject` and
  `TargetStorageClass: INTELLIGENT_TIERING`.

- **Storage Lens provides the access-pattern evidence the
  configuration depends on.** Always pull Storage Lens metrics covering
  at least 30 days before recommending Intelligent-Tiering. A 1-day
  snapshot can misclassify a daily-access bucket as cold.

## Edge-case handling

These are buckets where the standard pattern produces wrong
recommendations without explicit handling:

| Pattern | Detection | Fix |
|---|---|---|
| **Small objects + frequent access** (50M objects < 128 KB, daily access) | `ObjectSizeDistribution` from Storage Lens: `<128KB` > 20% by count AND access > 1x/day | Verdict `ALREADY_OPTIMAL` (Standard cheapest). Monitoring fee would be pure overhead; Infrequent 128 KB minimum prevents saving. Surface small-object fee aggregation as a cost-allocation finding only. |
| **Compliance archive with periodic retrieval** (Object Lock COMPLIANCE, quarterly audit) | `get-object-lock-configuration`: COMPLIANCE mode with known retrieval cadence | Restrict to Frequent Access only. Verdict `ALREADY_OPTIMAL` for Intelligent-Tiering (archive tiers defeat retrieval SLA). A fixed lifecycle to Glacier IR for ms-retrieve is the correct pick. |
| **Mixed hot + cold prefix** (`app/hot/` daily, `app/archive/` yearly) | Storage Lens shows divergent access by prefix | Scope the configuration with `Filter: {Prefix: "app/archive/"}` to limit the monitoring fee to the cold prefix. Leaves the hot prefix on Standard (no wasted monitoring). |

## Cross-region cost variance detail

S3 pricing varies by region. Always re-state the regional rate in the
SAVINGS block when the bucket is not in us-east-1. Monitoring fee is
flat ($0.0025/1K) across all regions.

| Region | Standard / IT-Frequent $/GB-mo | Notes |
|---|---|---|
| us-east-1, us-west-2 | 0.023 | Baseline |
| eu-west-1 (Ireland) | 0.024 | ~4% premium |
| ap-southeast-1 (Singapore) | 0.025 | ~9% premium |
| sa-east-1 (Sao Paulo) | 0.0309 | ~35% premium |

**Decision impact:** in high-premium regions, the gap between Frequent
and Archive tiers is wider, so Intelligent-Tiering captures MORE savings.
Be more aggressive on archive-tier timing in high-premium regions.

## Recent AWS features (2024-2026)

- **S3 Intelligent-Tiering small object fee aggregation (2025-2026):**
  For buckets with very large counts of small objects, AWS aggregates
  the per-object monitoring and small-object fees into bulk billing
  lines for cost-allocation visibility. This does NOT remove the
  monitoring fee — it changes how the fee is presented. The gate (Step 2)
  still applies.

- **Configurable Archive tier timing (2024-2025):** Archive Access
  (default 90 days) and Deep Archive Access (default 180 days) are now
  configurable via `Tierings[].Days`. Shorter windows capture savings
  faster on known-cold data.

- **Intelligent-Tiering filter scopes (2024):** Configurations support
  `Filter: {Prefix: "...", Tag: {...}}` to scope Intelligent-Tiering
  to specific object cohorts. Use to limit the monitoring fee to cold
  prefixes only.

- **S3 Storage Lens expanded (2024-2026):** 29+ metrics including
  object-size distribution, tier distribution, access-pattern trend.
  Always pull Storage Lens before recommending Intelligent-Tiering.

- **S3 Batch Operations expanded (2024-2025):** Supports `S3CopyObject`
  with `TargetStorageClass: INTELLIGENT_TIERING` for one-time backfill.

- **S3 Express One Zone directory buckets (2023-2025):** Single-AZ
  directory buckets with ms-latency. Do NOT support Intelligent-Tiering.
  Verdict: ALREADY_OPTIMAL for ML/AI workloads.

- **S3 Tables (managed Apache Iceberg, 2025):** Tables manage their
  own lifecycle; do NOT propose Intelligent-Tiering on table-data
  prefixes.

