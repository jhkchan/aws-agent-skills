# S3 Intelligent-Tiering Cost Model (us-east-1, 2026)

Load this reference before producing dollar estimates for any
Intelligent-Tiering recommendation. Prices are published us-east-1 rates;
multiply by the regional multiplier for other regions. Re-state the
regional rate from the AWS Pricing API when the operator's region differs.

## Intelligent-Tiering tier pricing (USD per GB-month)

| Tier | $/GB-mo | Trigger | Min duration | Monitoring | Retrieval $/GB |
|---|---|---|---|---|---|
| Frequent Access | 0.023 | Default (hot) | none (per-day) | $0.0025/1K obj (whole config scope) | free |
| Infrequent Access | 0.0125 | 30 consecutive days no access | none (per-day) | included | 0.01 |
| Archive Access | 0.0036 | 90 consecutive days no access (configurable >= 90) | 90 days | included | 0.03 (Std), 0.0025 (Bulk) |
| Deep Archive Access | 0.00099 | 180 consecutive days no access (configurable >= 180) | 180 days | included | 0.02-10 (tiered) |

## Key cost-model distinctions vs S3 Lifecycle tiers

- **No minimum-duration on Frequent/Infrequent.** Intelligent-Tiering is
  unique among S3 IA-style tiers: Frequent and Infrequent bill per-day
  with no minimum. Standard-IA, One-Zone-IA, and Glacier IR all carry
  30/90-day minimums. This makes Intelligent-Tiering cheaper for
  short-lived unknown-pattern workloads.
- **Archive tiers DO have minimums.** Archive Access carries a 90-day
  minimum; Deep Archive Access carries a 180-day minimum. These match
  Glacier IR and Glacier Deep Archive respectively.
- **Monitoring fee is the gating cost.** $0.0025 per 1,000 objects per
  month, billed on ALL objects in the configuration's filter scope
  regardless of whether they tier. For high-object-count buckets, this
  fee can exceed the transition saving.

## Request pricing (USD per 1,000 requests)

| Tier | PUT/COPY/POST/LIST | GET/SELECT/OTHER |
|---|---|---|
| Frequent Access | 0.0045 | 0.00038 |
| Infrequent Access | 0.01 | 0.001 |
| Archive Access | 0.02 | 0.001 (restore+GET) |
| Deep Archive Access | 0.05 | 0.001 (restore+GET) |

## Monitoring-fee gate math

```
monitoring_fee_monthly = (object_count / 1000) × 0.0025
projected_transition_saving = bytes_that_will_tier_GB × (0.023 - 0.0125)

# For small objects (< 128 KB):
#   bytes_that_will_tier is effectively 0 (128 KB minimum billable size
#   on Infrequent prevents real savings)
#   → monitoring_fee > 0 = pure overhead → REJECT Intelligent-Tiering

# Threshold: Intelligent-Tiering wins when
#   avg_object_size > 128 KB
#   AND monitoring_fee < projected_transition_saving
```

### Worked monitoring-fee examples

| Object count | Avg size | Monitoring fee/mo | Transition saving/mo | Verdict |
|---|---|---|---|---|
| 30M | 1.8 MB | $75.00 | ~$600 (24 TB tiering at $0.0105/GB delta) | Intelligent-Tiering WINS |
| 8.2M | 4.2 KB | $20.50 | $0 (128 KB min prevents saving) | REJECT — Standard cheaper |
| 10M | 500 KB | $25.00 | ~$50 (5 TB at $0.0105/GB delta) | Intelligent-Tiering WINS (fee < saving) |
| 50M | 1 KB | $125.00 | $0 | REJECT — monitoring fee is pure overhead |

## Regional multipliers (storage rates)

Approximate multiplier vs us-east-1; monitoring fee is flat across regions.

| Region | Multiplier | Standard $/GB-mo |
|---|---|---|
| us-east-1, us-west-2, us-east-2 | 1.00x | 0.023 |
| eu-west-1 (Ireland) | 1.04x | 0.024 |
| eu-central-1 (Frankfurt) | 1.07x | 0.0245 |
| ap-southeast-1 (Singapore) | 1.09x | 0.025 |
| ap-northeast-1 (Tokyo) | 1.09x | 0.025 |
| ap-southeast-2 (Sydney) | 1.09x | 0.025 |
| ap-south-1 (Mumbai) | 1.13x | 0.0259 |
| sa-east-1 (Sao Paulo) | 1.35x | 0.0309 |
| af-south-1 (Cape Town) | 1.32x | 0.0304 |

## Retrieval fee tiers (Archive + Deep Archive)

Archive Access:
- Standard: 1-5 min (via restore), $0.03/GB + $0.10/1K req
- Bulk: 5-12h, $0.0025/GB + $0.025/1K req

Deep Archive Access:
- Standard: 12h, $0.02/GB + $0.10/1K req
- Bulk: 48h, $0.0025/GB + $0.025/1K req

## Small-object fee aggregation (2025-2026 feature)

For buckets with very large counts of small objects, AWS aggregates the
per-object monitoring and small-object fees into bulk billing lines for
cost-allocation visibility. This does NOT remove the monitoring fee —
it changes how the fee is presented in the bill. The monitoring fee
still scales with object count; the Step 2 gate still applies.

Aggregation helps operators who need to allocate Intelligent-Tiering
costs across teams or budgets but does not change the cost math.

## Decision rules

1. **Avg object size < 128 KB:** prefer Standard. Intelligent-Tiering
   monitoring fee exceeds transition saving.
2. **Unknown / mixed access, avg object > 128 KB:** Intelligent-Tiering.
   Monitoring fee is the cost of access-pattern discovery.
3. **Predictable access pattern:** fixed lifecycle rule is cheaper (no
   monitoring fee). See the lifecycle-optimizer skill.
4. **Known-cold data, 12h-retrieve OK:** configure Deep Archive Access
   at the minimum allowed days for faster savings capture.
5. **Compliance workload with retrieval SLA:** Frequent Access only.
   Archive tiers defeat the retrieval SLA.
6. **Directory bucket (S3 Express One Zone):** Intelligent-Tiering NOT
   supported. Verdict: ALREADY_OPTIMAL for ML/AI.
