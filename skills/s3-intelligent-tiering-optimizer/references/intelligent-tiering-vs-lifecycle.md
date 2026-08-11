# Intelligent-Tiering vs S3 Lifecycle — Decision Reference

Load this reference when Step 4 (Intelligent-Tiering-vs-lifecycle
trade-off) needs a definitive pick. The two systems are separate, use
different APIs, and optimise on different signals.

## System comparison

| Dimension | Intelligent-Tiering | S3 Lifecycle |
|---|---|---|
| **API** | `put-bucket-intelligent-tiering-configuration` | `put-bucket-lifecycle-configuration` |
| **Optimisation signal** | Access pattern (consecutive days of no access) | Object age (days since creation) |
| **Tier movement** | Per-object, automatic, based on actual access | Bulk, rule-based, based on age |
| **Minimum-duration (Frequent/Infrequent)** | NONE (per-day billing) | 30 days (Standard-IA, One-Zone-IA) |
| **Minimum-duration (Archive)** | 90 days Archive Access, 180 days Deep Archive | 90 days Glacier IR, 180 days Deep Archive |
| **Monitoring fee** | $0.0025/1,000 objects/month | None |
| **Configurable timing** | Archive Access >= 90d, Deep Archive >= 180d | Any `Days` value >= 1 |
| **Filter scope** | Prefix and/or Tag | Prefix, Tag, or AND of multiple |
| **Object-Lock interaction** | Tier transitions honoured; archive defeats retrieval SLA | Expiration blocked by retention period |
| **Coexistence** | Can coexist with lifecycle on the same bucket | Can coexist with Intelligent-Tiering |

## When to pick Intelligent-Tiering

- **Access pattern is unknown or mixed.** Intelligent-Tiering discovers
  the pattern automatically; lifecycle requires you to know it.
- **Objects are short-lived but pattern is unpredictable.** Intelligent-
  Tiering's per-day billing (no minimum on Frequent/Infrequent) avoids
  the 30-day minimum-duration charge that lifecycle-driven IA incurs.
- **You want per-object optimisation.** Lifecycle transitions ALL
  matching objects at the same age; Intelligent-Tiering transitions each
  object based on its individual access pattern.

## When to pick Lifecycle

- **Access pattern is predictable.** If you know objects are accessed
  daily, monthly, or quarterly, a fixed lifecycle rule is cheaper (no
  monitoring fee).
- **You need expiration (deletion).** Intelligent-Tiering does NOT
  delete objects; lifecycle `Expiration` does. For log rotation or
  retention compliance, lifecycle is required.
- **You need noncurrent-version cleanup.** Intelligent-Tiering does
  NOT manage noncurrent versions; lifecycle
  `NoncurrentVersionExpiration` does.
- **Object count is very high and objects are small.** The monitoring
  fee makes Intelligent-Tiering more expensive than a fixed lifecycle
  rule for small-object buckets.

## Coexistence rules

- **Pick ONE system per prefix.** A lifecycle rule transitioning
  `app/logs/` to Standard-IA at 30d AND an Intelligent-Tiering
  configuration scoped to `app/logs/` will produce unpredictable tier
  movement. The two systems do not coordinate.
- **Lifecycle handles what Intelligent-Tiering cannot.** Use lifecycle
  for expiration, noncurrent-version cleanup, and multipart-upload
  abort. Use Intelligent-Tiering for access-pattern-driven tiering.
- **Configuration scope MUST NOT overlap.** If Intelligent-Tiering is
  scoped to `app/data/`, lifecycle rules for the same bucket should
  target different prefixes (`app/logs/`, `app/tmp/`).

## Cost comparison worked example

1 TB of application data, 1M objects averaging 1 MB each, mixed access
(20% daily, 40% monthly, 20% quarterly, 20% yearly):

| Approach | Monthly cost | Notes |
|---|---|---|
| Standard only | $23.00 | No optimisation |
| Lifecycle: Standard -> IA at 30d | $17.50 (blended) | 30-day minimum on IA; no monitoring fee |
| Intelligent-Tiering | $16.25 + $2.50 monitoring = $18.75 | Per-day billing on Infrequent; monitoring fee $2.50 |
| Lifecycle: Standard -> IA 30d -> Glacier IR 90d | $11.50 (blended) | Cheapest for predictable patterns; no monitoring fee |
| Intelligent-Tiering + Archive tiers | $9.80 + $2.50 = $12.30 | Archive tiers auto-trigger; monitoring fee $2.50 |

**Breakdown:** lifecycle wins on cost when the pattern is predictable
(no monitoring fee). Intelligent-Tiering wins on simplicity when the
pattern is unknown. For this example, the lifecycle + Glacier IR
approach is cheapest ($11.50) — but only if the access pattern is
known. If the pattern is unknown, Intelligent-Tiering ($12.30) is the
safest pick.

## Monitoring-fee break-even

For a bucket with N objects and projected transition saving S per month:

- Intelligent-Tiering total cost = S + (N/1000) × $0.0025
- Lifecycle total cost = S (no monitoring fee)
- Break-even: when the monitoring fee equals the per-object optimisation
  gain over lifecycle. For large objects with genuinely mixed patterns,
  Intelligent-Tiering's per-object optimisation can exceed the
  monitoring fee. For small objects or predictable patterns, it cannot.

## Recommendation algorithm

```
IF access_pattern == UNKNOWN or MIXED:
    IF avg_object_size >= 128 KB:
        IF monitoring_fee < projected_transition_saving:
            → Intelligent-Tiering (with archive tiers if applicable)
        ELSE:
            → Standard (monitoring fee defeats the saving)
    ELSE:
        → Standard (small objects; IA minimum billable size prevents saving)
ELSE (predictable pattern):
    → Lifecycle rule (no monitoring fee; same or cheaper $/GB)
```
