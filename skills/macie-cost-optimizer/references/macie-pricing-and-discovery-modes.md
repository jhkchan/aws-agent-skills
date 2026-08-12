# Macie Pricing and Discovery Modes Reference

Supplementary reference for the Macie Cost Optimizer skill. Loaded on-
demand when detailed pricing math, discovery-mode comparison, managed
identifier category lists, custom identifier regex audit guidance, or
multi-account delegation matrices are needed.

## Macie pricing (us-east-1, 2026, USD)

### S3 sensitive data discovery pricing

| Component | Rate | Notes |
|---|---|---|
| Per-GB assessed (sensitive data discovery) | $0.10/GB for the first 1 TB, tiered downward above | Applies to both automated discovery and targeted classification jobs; the rate is per GB of objects assessed per run |
| Per-bucket monthly fee (bucket inventory + metadata) | $0.50/bucket/month for buckets beyond free tier | Charged on all monitored buckets regardless of scan activity |
| Finding storage | included | Findings retained for 90 days; export to S3 for long-term |
| Automated data discovery (account-level) | account-level monthly fee + per-GB on new/changed objects | Incremental assessment — service manages scope and cadence |
| Free tier | First 30 days free for new accounts; bucket inventory for a limited number of S3 buckets | Does not apply to targeted classification jobs |

### Tiered per-GB assessment rates (illustrative)

| Monthly GB assessed | Rate tier |
|---|---|
| 0 – 1 TB | $0.10/GB |
| 1 – 10 TB | $0.08/GB (incremental) |
| 10 – 50 TB | $0.05/GB (incremental) |
| 50 TB+ | $0.03/GB (incremental) |

Always verify the current tiered rates on the Macie pricing page; the
shape is decreasing-tier (lower per-GB rate at higher volume), but the
breakpoints adjust periodically.

### Duration billing precision

Macie bills per GB of objects assessed per run. The `bytesProcessed`
field in `describe-classification-job` is the authoritative input for
cost calculation. Convert bytes to GB using 1 GB = 1,073,741,824 bytes
(binary) or 1,000,000,000 bytes (decimal) — verify which convention the
job reports by inspecting a known-bucket run.

## Automated discovery vs targeted classification jobs

| Dimension | Automated discovery | Targeted classification job |
|---|---|---|
| Scope management | Service-managed (new + changed objects) | User-defined (`bucketCriteria`, full included scope per run) |
| Cadence | Service-defined (typically daily incremental) | User-defined schedule (daily, weekly, monthly, one-time) |
| Per-run cost | Incremental (only new/changed objects) | Full included scope every run |
| Managed identifiers | Full set, configurable via classification scope | User-selected via `managedDataIdentifierSelector` |
| Custom identifiers | Supported | Supported |
| Best for | Recurring sensitive-data coverage of a stable data lake | Ad-hoc investigation, one-time audits, specific compliance scans |
| Cost trap | None (incremental by design) | Recurring scheduled jobs on stable data — full-scan cost × runs |

### When automated discovery is the cost-efficient choice

- The data lake is stable (low monthly churn).
- Recurring sensitive-data coverage is required (not a one-time audit).
- The compliance regime does not mandate full-scan evidence per run.
- The set of buckets in scope is well-defined and changes infrequently.

### When targeted jobs are the correct choice

- A one-time investigation of a specific bucket or object set.
- A compliance scan that requires documented full-scan evidence per run.
- A scan that needs custom identifiers or scoping not supported by
  automated discovery.
- A scan of buckets outside the automated discovery classification scope.

## Managed data identifier categories

Macie provides a set of managed data identifiers grouped by category.
Use `managedDataIdentifierSelector: INCLUDE` with specific IDs to narrow
scope.

### Common managed identifier categories

| Category | Example identifiers | Typical compliance regime |
|---|---|---|
| Personal (US) | `AWSManagedPersonalUS` (SSN, driver's license, passport) | US PII compliance |
| Personal (EU) | `AWSManagedPersonalEU` (national ID, tax ID by country) | GDPR |
| Financial | `AWSManagedFinancialUS`, `AWSManagedFinancialEU` (credit card, bank account, routing) | PCI-DSS, SOX |
| Credentials | `AWSManagedCredentialsKeywords` (AWS secret keys, API tokens) | Security operations |
| Healthcare | `AWSManagedHealthUS` (HIPAA identifiers) | HIPAA |
| Multiple | `ALL` selects every category | Initial discovery (not recommended for steady-state) |

### Selector values

| Selector | Behaviour |
|---|---|
| `ALL` | Evaluate every managed identifier per sampled object — highest per-object cost |
| `INCLUDE` | Evaluate only the listed `managedDataIdentifierIds` — recommended for steady-state |
| `EXCLUDE` | Evaluate all except the listed IDs — useful for excluding a noisy category |
| `RECOMMENDED` (where available) | Macie-recommended set based on bucket content sampling |

## Custom data identifier regex audit guidance

Custom data identifiers run a user-defined regex (and optional keywords)
against every sampled object. Per-object evaluation cost scales with:
1. Number of custom identifiers configured.
2. Regex complexity (catastrophic backtracking multiplies per-object time).
3. Keyword match rate (keywords short-circuit regex; without keywords,
   the regex runs on every object).

### Regex audit checklist

| Symptom | Audit action |
|---|---|
| Nested quantifiers (e.g., `(a+)+`, `(a*)*`) | Rewrite to linear-time pattern or add anchoring keywords |
| Unbounded repetition (e.g., `.*`, `.+` without anchor) | Add `^`/`$` anchors or a required keyword |
| Overlapping with another custom identifier | Consolidate into one canonical identifier |
| Zero matches in 90 days | Remove the identifier (use `delete-custom-data-identifier`) |
| Regex compiles but times out on representative objects | Profile on a sample object set; simplify or split |

### Custom identifier cost estimation

```
per_object_custom_cost ≈ (number_of_custom_identifiers × avg_regex_eval_time_per_object)
monthly_custom_cost = per_object_custom_cost × objects_sampled_per_month
```

Consolidating 3 overlapping SSN variants into 1 reduces per-object
custom cost by ~67% for that identifier family.

## Sampling depth defaults

Macie samples S3 objects per bucket per run. The default sampling depth
balances coverage and cost.

| Bucket object count | Default sample ceiling (illustrative) |
|---|---|
| < 100,000 objects | All objects |
| 100,000 – 1,000,000 | Up to ~100,000 objects per bucket per run |
| > 1,000,000 | Up to ~100,000 objects per bucket per run (service-managed cap) |

Forcing deep/full evaluation (where supported) multiplies per-object
identifier cost. Only justified for high-risk buckets with explicit
compliance mandates.

## Multi-account delegation matrix

In a Macie-enabled organization, a single delegated administrator
account manages Macie across all member accounts.

| Topology | Cost shape | When to use |
|---|---|---|
| Delegated administrator (org-wide) | One administrator account + per-member bucket fees | Recommended for orgs; centralises config, deduplicates coverage |
| Per-account standalone | Per-account Macie enablement + per-account bucket fees | Only for standalone accounts not in a Macie-enabled org |
| Mixed (delegated + standalone in member accounts) | Double-assessment of shared data — avoid | Anti-pattern; consolidate to delegated only |

### Delegation setup

```bash
# Verify delegation status
aws organizations list-delegated-administrators \
  --service-principal macie.amazonaws.com

# Enable Macie in the delegated administrator account
aws macie2 enable-macie

# Invite member accounts (delegated administrator runs this)
aws macie2 create-invitations --account-ids "[\"111111111111\",\"222222222222\"]"

# Members accept
aws macie2 accept-invitation --administrator-account-id <admin-account-id>
```

### Region-specific delegation

Macie delegation is region-specific. For multi-region deployments, the
delegated administrator must be enabled in each region where member
accounts have S3 buckets to monitor.

## Classification export to S3 + Athena

### Export configuration

```bash
aws macie2 put-classification-export-configuration \
  --configuration '{"s3Destination":{"bucketName":"macie-export-prod","prefix":"classification/","kmsKeyArn":"arn:aws:kms:us-east-1:<acct>:key/<id>"}}'
```

### Athena query pattern

Once exported, partition findings by date and bucket; query via Athena
at ~$5/TB scanned. This is the cost-efficient way to do recurring
analysis vs re-invoking Macie or paginating the findings API.

```sql
-- Create a Glue table over the export prefix
CREATE EXTERNAL TABLE IF NOT EXISTS macie_classification (
  schema_version STRING,
  `timestamp` STRING,
  bucket STRING,
  key STRING,
  finding_id STRING,
  severity STRING,
  data_identifiers ARRAY<STRUCT<name:STRING, occurrences:INT>>
)
PARTITIONED BY (dt STRING)
STORED AS JSON
LOCATION 's3://macie-export-prod/classification/';

-- Query: top buckets by finding count, last 30 days
SELECT bucket, COUNT(*) AS finding_count
FROM macie_classification
WHERE dt BETWEEN '2026-07-11' AND '2026-08-11'
GROUP BY bucket
ORDER BY finding_count DESC;
```

## Regional pricing multipliers

| Region | Multiplier vs us-east-1 |
|---|---|
| us-east-1, us-west-2, eu-west-1 | 1.0x (baseline) |
| ap-southeast-1, ap-northeast-1 | ~1.1x |
| sa-east-1 | ~1.2x |
| us-gov-west-1 | ~1.5x (verify on pricing page) |

Always re-state the regional rate from the Macie pricing page for
regions outside us-east-1; the multipliers adjust periodically.

## CLI command reference

### Inspect Macie configuration

```bash
# Macie account status
aws macie2 get-macie-account

# Automated discovery configuration
aws macie2 get-automated-discovery-configuration

# Classification scope (includes/excludes)
aws macie2 get-classification-scope --name <scope-name>

# List all classification jobs
aws macie2 list-classification-jobs

# Describe a specific job
aws macie2 describe-classification-job --job-id <id>

# Bucket statistics
aws macie2 get-bucket-statistics

# List findings (sample for noise assessment)
aws macie2 list-findings --max-results 50
```

### Apply changes

```bash
# Update classification scope (exclude buckets)
aws macie2 update-classification-scope \
  --name <scope-name> \
  --s3 '{"excludes":{"bucketNames":["bucket1","bucket2"]}}'

# Update a classification job (narrow identifiers, change schedule)
aws macie2 update-classification-job \
  --job-id <id> \
  --managed-data-identifier-selector INCLUDE \
  --managed-data-identifier-ids "AWSManagedFinancialUS,AWSManagedCredentialsKeywords"

# Disable a recurring job
aws macie2 update-classification-job --job-id <id> --status DISABLED

# Create a suppression (findings filter)
aws macie2 create-findings-filter \
  --name "suppress-known-safe-prefix" \
  --action ARCHIVE \
  --finding-criteria '{"criterion":{"s3Object.path":{"contains":["data-lake/public-assets/"]}}}'

# Configure classification export
aws macie2 put-classification-export-configuration \
  --configuration '{"s3Destination":{"bucketName":"macie-export-prod","prefix":"classification/"}}'
```

### Cost Explorer Macie spend

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-07-11,End=2026-08-11 \
  --granularity MONTHLY \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Macie"]}}' \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE
```

## Extended anti-patterns

1. **NEVER exclude a bucket based on name pattern alone.** Verify via a
   prior clean Macie run or a documented data classification review.
2. **NEVER narrow managed identifier scope below the compliance regime's
   requirements.** Removing financial identifiers from a PCI scope
   creates a compliance gap.
3. **NEVER add a suppression rule without a human-in-the-loop review of
   the objects being suppressed.** Suppression hides findings; only
   suppress validated-known-safe objects.
4. **NEVER disable automated discovery without confirming targeted jobs
   cover the same buckets.** Coverage gaps create security exposure.
5. **NEVER assume per-GB rates are flat across volumes.** The tiered
   rate structure means marginal savings calculations must use the
   correct tier for the projected GB.
6. **NEVER migrate a member account off standalone Macie without
   confirming the delegated administrator covers the member's regions.**
   Macie delegation is region-specific.

## Memory decision tree (identifier scope)

```
Is the compliance regime defined?
├── NO → Run with ALL initially to discover what is present, then narrow
└── YES → Which categories does the regime require?
    ├── PII only → INCLUDE personal identifiers (US/EU as applicable)
    ├── PCI/financial → INCLUDE financial identifiers
    ├── Credentials → INCLUDE credentials identifiers
    ├── HIPAA → INCLUDE healthcare identifiers
    └── Multi-regime → INCLUDE all required categories; EXCLUDE nothing
        further unless noise is confirmed
```
