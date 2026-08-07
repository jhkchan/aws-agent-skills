# S3 Storage Class Pricing Matrix (us-east-1, 2026)

Load this reference before producing dollar estimates for any S3 lifecycle
recommendation. Prices are published us-east-1 rates; multiply by the regional
multiplier for other regions. Re-state the regional rate from the AWS Pricing
API when the operator's region differs.

## Storage class pricing (USD per GB-month)

| Storage class | $/GB-mo | Min size | Min duration | Monitoring | Retrieval $/GB | Retrieval latency |
|---|---|---|---|---|---|---|
| Standard | 0.023 | — | — | — | free | ms |
| Standard-IA | 0.0125 | 128 KB | 30 days | — | 0.01 | ms |
| One-Zone-IA | 0.01 | 128 KB | 30 days | — | 0.01 | ms (single AZ) |
| Intelligent-Tiering (Frequent) | 0.023 | — | 30 days | 0.0025/1K obj | free | ms |
| Intelligent-Tiering (Infrequent) | 0.0125 | 128 KB | 30 days | included | 0.01 | ms |
| Intelligent-Tiering (Archive) | 0.0036 | — | 90 days | included | 0.03 (Std) | ms-sec |
| Intelligent-Tiering (Deep Archive) | 0.00099 | — | 180 days | included | 0.02-10 (tiered) | 12h |
| Glacier Instant Retrieval (GLACIER_IR) | 0.004 | 128 KB | 90 days | — | 0.03 + 0.0005/req | ms |
| Glacier Flexible Retrieval (GLACIER) | 0.0036 | — | 90 days | — | 0.0025-10 (tiered) | 1-5 min (Exp), 3-5h (Std), 5-12h (Bulk) |
| Glacier Deep Archive (DEEP_ARCHIVE) | 0.00099 | — | 180 days | — | 0.02-10 (tiered) | 12h (Std), 48h (Bulk) |
| S3 Express One Zone (directory) | 0.16 | — | — | — | free | sub-ms |
| Reduced Redundancy (RRS) | 0.024 | — | — | — | free | ms — legacy, do not use |

## Request pricing (USD per 1,000 requests)

| Storage class | PUT/COPY/POST/LIST | GET/SELECT/OTHER |
|---|---|---|
| Standard | 0.0045 | 0.00038 |
| Standard-IA | 0.01 | 0.001 |
| One-Zone-IA | 0.01 | 0.001 |
| Intelligent-Tiering (Frequent) | 0.0045 | 0.00038 |
| Intelligent-Tiering (Infrequent) | 0.01 | 0.001 |
| Intelligent-Tiering (Archive/Deep) | 0.02 | 0.001 |
| Glacier IR | 0.02 | 0.001 |
| Glacier Flexible | 0.03 | 0.0004 (select), 0.0004 (restore+GET) |
| Glacier Deep Archive | 0.05 | 0.001 (restore+GET) |
| S3 Express One Zone | 0.008 | 0.0004 |

## Regional multipliers (storage class rates)

Approximate multiplier vs us-east-1; always re-check via the AWS Pricing API
for production estimates.

| Region | Multiplier |
|---|---|
| us-east-1, us-west-2 | 1.00x |
| us-east-2 | 1.00x |
| eu-west-1 (Ireland) | 1.09x |
| eu-central-1 (Frankfurt) | 1.16x |
| ap-southeast-1 (Singapore) | 1.18x |
| ap-northeast-1 (Tokyo) | 1.15x |
| ap-southeast-2 (Sydney) | 1.21x |
| ap-south-1 (Mumbai) | 1.21x |
| sa-east-1 (Sao Paulo) | 1.51x |
| af-south-1 (Cape Town) | 1.51x |

## Retrieval fee tiers (Glacier Flexible + Deep Archive)

Glacier Flexible Retrieval:
- Expedited: 1-5 min, $10/GB + $0.03/1K req (excludes data transfer)
- Standard: 3-5h, $0.01/GB + $0.05/1K req
- Bulk: 5-12h, $0.0025/GB

Glacier Deep Archive:
- Standard: 12h, $0.02/GB + $0.10/1K req
- Bulk: 48h, $0.0025/GB + $0.025/1K req

## Minimum-duration charge math

If an object is deleted BEFORE the storage class's minimum duration:

- **Standard-IA / One-Zone-IA (30-day min):** billed for the prorated remaining
  days. A 5-day-old Standard-IA object deleted on day 5 bills 25 additional days.
- **Glacier IR / Glacier Flexible (90-day min):** same prorated remainder.
- **Glacier Deep Archive (180-day min):** same prorated remainder.
- **Intelligent-Tiering:** minimum-duration applies PER tier, not overall.
  Moving to Frequent Access on day 5 does not reset the Archive minimum.

## Decision rules

1. **Avg object size < 128 KB:** prefer Standard over any IA tier. IA minimum
   billable size is 128 KB — small objects cost MORE in IA than Standard.
2. **Access frequency >= 1x/month:** prefer Standard or Intelligent-Tiering.
3. **Access frequency < 1x/quarter, needs ms retrieval:** Glacier Instant
   Retrieval at $0.004/GB.
4. **Access frequency < 1x/year, hours-to-retrieve OK:** Glacier Flexible
   Retrieval at $0.0036/GB.
5. **Access frequency < 1x/year, 12h-to-retrieve OK:** Glacier Deep Archive at
   $0.00099/GB (3.6x cheaper than Flexible, 23x cheaper than Standard).
6. **ML/AI training, ms latency critical:** S3 Express One Zone directory
   bucket at $0.16/GB. Use only for the active training corpus.
7. **Unknown / mixed access patterns, avg object > 128 KB:** Intelligent-Tiering
   at $0.023/GB + $0.0025/1K monitoring. Monitor the tier distribution monthly.

## Cross-tier transition chain (typical savings trajectory)

For a 1 TB log workload over 12 months:

| Month | Tier | $/mo |
|---|---|---|
| 1 | Standard | $23.00 |
| 2 | Standard (Standard-IA transition at 30d) | $12.50 |
| 4 | Standard-IA (Glacier IR transition at 90d) | $4.00 |
| 7 | Glacier IR (Glacier Flexible at 180d) | $3.60 |
| 13 | Expire at 365d | $0.00 |

Annual: ~$170 vs $276 for Standard-only — **38% saving** on a single TB.

For 1 TB compliance archive (write-once, 7-year retention):

| Month | Tier | $/mo |
|---|---|---|
| 1-3 | Standard | $23.00 |
| 4+ | Glacier Deep Archive (90d transition) | $0.99 |

7-year total: ~$90 vs $1,932 for Standard-only — **95% saving**.

## Common cost-modeling pitfalls

- **Forgetting request fees on bulk transitions.** A 100M-object bucket
  transitioning to Glacier via lifecycle generates 100M PUT requests on the
  destination tier at $0.02-0.05/1K — a $2,000-5,000 one-time request charge
  that must be in the model.
- **Underestimating Intelligent-Tiering monitoring fees.** 50M small objects ×
  $0.0025/1K = $125/month in monitoring, which can exceed the transition saving.
- **Ignoring retrieval fees in the projection.** A "savings" estimate that
  ignores a likely quarterly retrieval misrepresents the value. Always include
  a retrieval-fee caveat for any Glacier-tier recommendation.
- **Minimum-duration charge on early-delete.** Lifecycle transitions to IA
  followed by a short retention `Expiration` rule produce minimum-duration
  charges that can net MORE expensive than Standard. Always model the
  minimum-duration cost if the workload deletes objects sooner than the tier
  minimum.
