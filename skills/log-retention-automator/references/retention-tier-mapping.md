# Retention Tier Mapping Reference

Supplementary reference for the Log Retention Automator skill. Use
when mapping a desired retention period to one of the 22 allowed
CloudWatch Logs retention values, or when validating a tag-to-tier
policy before deployment.

## The 22 allowed retentionInDays values

CloudWatch Logs `put-retention-policy` accepts ONLY these integer
values. Any value outside this set produces
`InvalidParameterException`.

```
1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180,
365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653
```

## Tier-to-human-readable mapping

| retentionInDays | Approximate period | Common compliance use case |
|---|---|---|
| 1 | 1 day | Debug/sandbox — minimal cost |
| 3 | 3 days | Short-lived dev environments |
| 5 | 5 days | Workday-aligned dev |
| 7 | 1 week | Standard dev |
| 14 | 2 weeks | Standard staging |
| 30 | 1 month | Short-term production |
| 60 | 2 months | Production with debug window |
| 90 | 3 months | Standard production (default) |
| 120 | 4 months | Extended production |
| 150 | 5 months | Compliance-adjacent |
| 180 | 6 months | Half-year compliance |
| 365 | 1 year | Annual compliance (SOX-lite) |
| 400 | ~13 months | Extended annual |
| 545 | ~18 months | 1.5-year compliance |
| 731 | ~2 years | 2-year compliance |
| 1096 | ~3 years | 3-year compliance (PCI-DSS) |
| 1827 | ~5 years | 5-year compliance (SOX, HIPAA) |
| 2192 | ~6 years | 6-year compliance |
| 2557 | ~7 years | 7-year compliance (tax, FINRA) |
| 2922 | ~8 years | 8-year compliance |
| 3288 | ~9 years | 9-year compliance |
| 3653 | ~10 years | 10-year compliance (financial) |

## Round-UP mapping table

When a desired retention is not in the allowed set, round UP to the
next allowed tier. NEVER round down — rounding down deletes more data
than the operator requested.

| Desired days | Round UP to | Reason |
|---|---|---|
| 2 | 3 | 1 is too short for most use cases |
| 4 | 5 | 3 is too short |
| 6 | 7 | 5 is too short |
| 8-13 | 14 | 7 is too short |
| 15-29 | 30 | 14 is too short |
| 31-59 | 60 | 30 is too short |
| 61-89 | 90 | 60 is too short |
| 91-119 | 120 | 90 is too short |
| 121-149 | 150 | 120 is too short |
| 151-179 | 180 | 150 is too short |
| 181-364 | 365 | 180 is too short |
| 366-399 | 400 | 365 is too short |
| 401-544 | 545 | 400 is too short |
| 546-730 | 731 | 545 is too short |
| 732-1095 | 1096 | 731 is too short |
| 1097-1826 | 1827 | 1096 is too short |
| 1828-2191 | 2192 | 1827 is too short |
| 2193-2556 | 2557 | 2192 is too short |
| 2558-2921 | 2922 | 2557 is too short |
| 2923-3287 | 3288 | 2922 is too short |
| 3289-3652 | 3653 | 3288 is too short |
| > 3653 | Not supported | Use S3 archival via Firehose |

## Standard tag-to-retention policy templates

### Production environment policy

| Tag value | Retention | Tier value | Notes |
|---|---|---|---|
| prod | 90 days | 90 | Hot query window for debugging |
| prod-compliance | 2557 days | 2557 | 7-year compliance retention |
| prod-audit | 3653 days | 3653 | 10-year financial audit |

### Development environment policy

| Tag value | Retention | Tier value | Notes |
|---|---|---|---|
| dev | 7 days | 7 | Standard dev iteration window |
| dev-long | 30 days | 30 | Extended debugging |
| sandbox | 1 day | 1 | Cost minimization |

### Untagged fallback

| Scenario | Default | Notes |
|---|---|---|
| Account with mixed workloads | 14 | Conservative default |
| Account with dev-only workloads | 7 | Matches dev tier |
| Account with compliance workloads | 90 | Conservative — prefer over-retention |

## API validation

```bash
# Validate a retention value before batch deployment
python3 -c "
allowed = [1,3,5,7,14,30,60,90,120,150,180,365,400,545,731,1096,1827,2192,2557,2922,3288,3653]
test_val = 45
if test_val in allowed:
    print(f'{test_val}d: VALID')
else:
    rounded_up = next(v for v in allowed if v > test_val)
    print(f'{test_val}d: INVALID — round UP to {rounded_up}d')
"
```

## Common tier-selection mistakes

| Mistake | Consequence | Correct approach |
|---|---|---|
| Using 45 instead of 60 | `InvalidParameterException` on put-retention-policy | Round UP to nearest allowed value |
| Setting 3653 when S3 archival is configured | Overpaying for CloudWatch storage ($0.03/GB vs $0.0036/GB Glacier) | Set 90d CloudWatch + S3 archival for long-term |
| Using 0 or null | `delete-retention-policy` behavior — resets to Never Expire | Always specify a positive integer from the allowed set |
| Setting different tiers per log stream | Not possible — retention is per-log-GROUP, not per-stream | Use separate log groups for different retention needs |
| Rounding down from 45 to 30 | Deletes 15 days more data than intended | Always round UP |
