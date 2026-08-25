# S3 Pricing and Storage Classes Reference

Supplementary reference for the S3 Storage Class Optimizer skill. Loaded
on-demand when detailed pricing math, minimum-days matrices, Intelligent-
Tiering configuration, or Batch Operations steps are needed.

## S3 storage class pricing (us-east-1, 2026, USD)

### Storage pricing ($/TB-month)

| Storage class | $/TB-month | $/GB-month | Min duration | Retrieval latency |
|---|---|---|---|---|
| Standard | $23.00 | $0.023 | None | ms |
| Standard-IA | $12.50 | $0.0125 | 30 days | ms |
| One Zone-IA | $10.10 | $0.01 | 30 days | ms (single AZ) |
| Glacier Instant Retrieval | $4.00 | $0.004 | 90 days | ms |
| Glacier Flexible Retrieval | $3.60 | $0.0036 | 90 days | 1-5 min (std), 5-12h (bulk) |
| Deep Archive | $0.99 | $0.00099 | 180 days | 12h (std), 48h (bulk) |
| Intelligent-Tiering (Frequent) | $23.00 | $0.023 | None | ms |
| Intelligent-Tiering (Infrequent) | $12.50 | $0.0125 | None | ms |
| Intelligent-Tiering (Archive) | $1.25 | $0.00125 | 90 days | 1-5 min |
| Intelligent-Tiering (Deep Archive) | $0.30 | $0.0003 | 180 days | 12h |

### Retrieval pricing ($/GB)

| Class | Standard retrieval | Bulk retrieval | Expedited retrieval |
|---|---|---|---|
| Standard-IA | $0.01 | — | — |
| One Zone-IA | $0.01 | — | — |
| Glacier IR | $0.03 | — | — |
| Glacier Flexible | $0.03 | $0.025 | $0.10 |
| Deep Archive | $0.02 | $0.0025 | N/A |

### Request pricing ($/1,000 requests)

| Request type | Standard | IA | Glacier IR | Glacier Flexible | Deep Archive |
|---|---|---|---|---|---|
| PUT/COPY/POST/LIST | $0.005 | $0.01 | $0.02 | $0.03 | $0.05 |
| GET/SELECT/other | $0.0004 | $0.001 | $0.001 | $0.0004 | $0.0004 |
| Lifecycle transition | $0.01 | $0.01 | $0.01 | $0.03 | $0.05 |

### Intelligent-Tiering monitoring fee

- **Flat rate:** $2.50/TB-month for objects > 128 KB.
- **Objects < 128 KB:** Charged at Standard rate (small objects stay in
  Frequent Access tier permanently; monitoring fee does not apply).
- **Break-even:** Monitoring fee pays off when storage savings from
  auto-tiering exceed $2.50/TB-month. Typically requires > 5 TB with
  > 40% of objects qualifying for Archive tier.

### Early delete charges

| Class | Minimum storage duration | Early delete charge |
|---|---|---|
| Standard-IA | 30 days | Prorated for remaining days |
| One Zone-IA | 30 days | Prorated |
| Glacier IR | 90 days | Prorated |
| Glacier Flexible | 90 days | Prorated |
| Deep Archive | 180 days | Prorated |

## Minimum-days transition matrix

| From | To | Min days in From | Min cumulative days in Standard |
|---|---|---|---|
| Standard | Standard-IA | 30 | 30 |
| Standard | One Zone-IA | 30 | 30 |
| Standard | Glacier IR | 0 | 0 |
| Standard | Glacier Flexible | 1 | 1 |
| Standard | Deep Archive | 1 | 1 |
| Standard-IA | Glacier IR | 30 | 60 |
| Standard-IA | Glacier Flexible | 30 | 60 |
| Glacier IR | Glacier Flexible | 0 | 90 |
| Glacier Flexible | Deep Archive | 90 | 90 |

## Regional pricing multipliers

Approximate multiplier vs us-east-1 for S3 storage rates.

| Region | Multiplier | Notes |
|---|---|---|
| us-east-1, us-east-2, us-west-2 | 1.00x | Baseline |
| us-west-1 | 1.05x | Slight premium |
| eu-west-1, eu-west-2, eu-central-1 | 1.10-1.15x | EU premium |
| ap-southeast-1, ap-southeast-2 | 1.12-1.18x | APAC premium |
| ap-northeast-1 (Tokyo) | 1.10-1.15x | |
| ap-south-1 (Mumbai) | 1.15-1.25x | |
| sa-east-1 (Sao Paulo) | 1.35-1.50x | Highest premium |

## Cost calculation worked examples

### Example 1: Lifecycle deployment on 50 TB data lake

```
Bucket: data-lake-prod
Before: 50 TB all in Standard
  Monthly cost: 50 × $23 = $1,150

After lifecycle (30d→IA, 90d→GIR, 180d→DA):
  Standard (0-30d): 10 TB × $23 = $230
  Standard-IA (30-90d): 10 TB × $12.50 = $125
  Glacier IR (90-180d): 15 TB × $4.00 = $60
  Deep Archive (180d+): 15 TB × $0.99 = $14.85
  Total: $429.85

Monthly saving: $1,150 - $429.85 = $720.15 (62.6%)
```

### Example 2: Versioning bloat reclamation

```
Bucket: versioned-app-data
Current: 40 TB (current versions: 25 TB, noncurrent: 15 TB)
Before: all 40 TB in Standard = $920/month

After noncurrent lifecycle (3 versions kept, rest expired):
  Current: 25 TB × $23 = $575
  Noncurrent (3 versions, ~3 TB): 3 TB × $23 = $69
  Total: $644

Monthly saving: $920 - $644 = $276 (30%)
Plus reclaimed 12 TB of storage growth.
```

### Example 3: Retrieval cost surprise check

```
Bucket: compliance-archive
10 TB in Deep Archive. Monthly retrieval: 1 TB (10% rate).

Storage cost: 10 × $0.99 = $9.90/month
Retrieval cost: 1,024 GB × $0.02 (standard) = $20.48/month
Total: $30.38/month

If moved to Standard-IA:
  Storage: 10 × $12.50 = $125/month
  Retrieval: 1,024 GB × $0.01 = $10.24/month
  Total: $135.24/month

Deep Archive is still cheaper ($30.38 vs $135.24) even with 10%
retrieval rate. Keep Deep Archive.

But at 25% retrieval (2.5 TB):
  Deep Archive: $9.90 + (2,560 GB × $0.02) = $9.90 + $51.20 = $61.10
  Glacier IR: 10 × $4.00 + (2,560 × $0.03) = $40 + $76.80 = $116.80
  Standard-IA: 10 × $12.50 + (2,560 × $0.01) = $125 + $25.60 = $150.60

At 25%, Deep Archive ($61.10) < Glacier IR ($116.80). Still cheaper.

At 50% retrieval (5 TB):
  Deep Archive: $9.90 + (5,120 × $0.02) = $9.90 + $102.40 = $112.30
  Glacier IR: $40 + (5,120 × $0.03) = $40 + $153.60 = $193.60

Deep Archive still wins on pure cost, but retrieval latency (12h) may
be unacceptable. Consider Glacier IR for latency reasons, not cost.
```

## Extended NEVER list (supplementary anti-patterns)

- NEVER assume lifecycle transitions are instant. S3 processes
  transitions asynchronously (typically within 12 hours, up to 24h
  for large batches).
- NEVER transition objects to Standard-IA that are accessed more than
  twice per month. IA charges $0.01/GB retrieval — above 2 accesses,
  Standard is cheaper.
- NEVER deploy lifecycle without checking Object Lock. Objects under
  retention cannot be expired or transitioned.
- NEVER use One Zone-IA for compliance data. Single-AZ storage risks
  total data loss if the AZ fails.
- NEVER estimate savings without factoring transition request fees.
  For buckets with millions of small objects, per-request fees ($0.01/
  1,000) can exceed first-month savings.
- NEVER delete all noncurrent versions via lifecycle without keeping a
  minimum (NewerNoncurrentVersions). Application rollback may need
  prior versions.
- NEVER trust Storage Lens data older than 7 days. Object distribution
  changes as lifecycle policies execute.

---

## Archive tier comparison (moved from SKILL.md Step 5)

**Archive tier comparison:**

| Tier | Storage $/TB-mo | Retrieval $/GB | Retrieval latency | Min storage duration | Use case |
|---|---|---|---|---|---|
| Standard-IA | $12.50 | $0.01 | ms | 30 days | Infrequent access, ms latency needed |
| One Zone-IA | $10.10 | $0.01 | ms | 30 days | Infrequent, reproducible data |
| Glacier IR | $4.00 | $0.03 | ms | 90 days | Quarterly access, ms latency |
| Glacier Flexible | $3.60 | $0.03 (std), $0.025 (bulk), $0.10 (exp) | 1-5 min (std), 5-12h (bulk) | 90 days | Annual access, minutes ok |
| Deep Archive | $0.99 | $0.02 (std), $0.0025 (bulk) | 12h (std), 48h (bulk) | 180 days | Compliance archive, hours ok |
