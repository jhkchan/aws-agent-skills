# Restore Tiers and Provisioned Capacity Reference

Load this reference when planning or executing any Glacier restore.
The procedures below are the canonical tier-selection matrix,
capacity-provisioning workflow, and known failure modes.

## Tier SLA matrix

| Source class | Tier | SLA | Cost marker | Capacity required |
|---|---|---|---|---|
| Glacier Instant Retrieval (GIR) | (none) | ms latency | free retrieval (pay per-GB retrieved) | n/a |
| Glacier Flexible Retrieval | Expedited | 1-5 min | highest | on-demand or provisioned |
| Glacier Flexible Retrieval | Standard | 3-5 hr | medium | on-demand |
| Glacier Flexible Retrieval | Bulk | 5-12 hr | lowest | on-demand |
| Glacier Deep Archive | Standard | 12 hr | medium | on-demand |
| Glacier Deep Archive | Bulk | 48 hr | lowest | on-demand |

## Provisioned capacity

### When to provision

- DR drills with Expedited SLA requirements.
- Production workflows that depend on Expedited retrievals.
- Demand-peak seasons (year-end audit, regulatory pulls).
- Multi-team environments where on-demand Expedited is contested.

### Capacity unit semantics

- 1 capacity unit = 3 Expedited retrievals per minute OR 150 MB/min,
  whichever comes first.
- Provisioned per region. A unit in us-east-1 does not help restores
  in eu-west-1.
- Charged monthly (~$100/unit/month, varies by region) — provisioned
  whether used or not.
- Capacity is NOT shared across accounts in the same region.

### Provisioning workflow

Provisioned capacity is purchased via the AWS console (S3 →
Glacier → Provisioned capacity) or via the AWS Support API. There is
no direct CLI for capacity purchase — use the console or open a
support case.

Verify capacity exists:
- Console: S3 → Glacier → Provisioned capacity (shows units
  provisioned per region).
- Billing: filter by `AWSServiceUsage` for
  `GlacierProvisionedCapacityUnit-Usage` per region.

### On-demand vs provisioned Expedited

- **On-demand Expedited:** best-effort. May be queued or rejected
  during demand peaks. No commitment, pay-per-use. Suitable for
  ad-hoc single-object restores.
- **Provisioned Expedited:** guaranteed. SLA holds regardless of
  regional demand. Use for any workflow with a hard RTO.

## Tier selection procedure

1. Determine the source storage class (`head-object StorageClass`).
2. Determine the RTO budget.
3. Pick the fastest available tier for the source class that fits
   the RTO. If none fits, BLOCK and renegotiate.
4. For Expedited, check provisioned capacity. If none, decide
   whether on-demand is acceptable (best-effort) or provision.
5. For Deep Archive, never promise Expedited — the minimum is
   12 hours (Standard tier).

## Tier compatibility matrix

| Tier | Flexible Retrieval | Deep Archive | GIR |
|---|---|---|---|
| Expedited | YES (1-5 min) | NO | NO (no restore needed) |
| Standard | YES (3-5 hr) | YES (12 hr) | NO |
| Bulk | YES (5-12 hr) | YES (48 hr) | NO |

## Restore-object JSON shapes

### Flexible Retrieval — Expedited

```json
{"Days": 7, "GlacierJobParameters": {"Tier": "Expedited"}}
```

### Flexible Retrieval — Standard

```json
{"Days": 7, "GlacierJobParameters": {"Tier": "Standard"}}
```

### Flexible Retrieval — Bulk

```json
{"Days": 30, "GlacierJobParameters": {"Tier": "Bulk"}}
```

### Deep Archive — Standard

```json
{"Days": 30, "GlacierJobParameters": {"Tier": "Standard"}}
```

### Deep Archive — Bulk

```json
{"Days": 30, "GlacierJobParameters": {"Tier": "Bulk"}}
```

## Select output shape (for use with select-reader)

For SQL-filtered restores (instead of restoring the full object),
use `SelectParameters`:

```json
{
  "Days": 7,
  "GlacierJobParameters": {"Tier": "Standard"},
  "SelectParameters": {
    "InputSerialization": {"CSV": {"FileHeaderInfo": "USE"}},
    "ExpressionType": "SQL",
    "Expression": "SELECT * FROM s3object s WHERE s.region = 'us-east-1'",
    "OutputSerialization": {"CSV": {}}
  },
  "OutputLocation": {
    "S3": {"BucketName": "select-output-bucket", "Prefix": "filtered/"}
  }
}
```

This retrieves only filtered rows, not the full object — useful for
parquet/csv analytics where the full object is too large.

## Cost estimation

| Operation | Rough cost (us-east-1) |
|---|---|
| Expedited retrieval (Flexible) | $0.03 per GB |
| Standard retrieval (Flexible) | $0.01 per GB |
| Standard retrieval (Deep Archive) | $0.02 per GB |
| Bulk retrieval (Flexible) | $0.0025 per GB |
| Bulk retrieval (Deep Archive) | $0.0025 per GB |
| Provisioned capacity | ~$100 per unit per month |
| Batch Operations | $0.25 per million tasks |
| Restore-object API call | $0 (no per-call fee; retrieval is per-GB) |

Always emit a cost estimate before CONFIRM gate. Multiplied by data
volume (TB-scale), Expedited costs add up fast.
