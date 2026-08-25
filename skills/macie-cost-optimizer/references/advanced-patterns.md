# Advanced patterns — macie-cost-optimizer

Expert-knowledge deep dives, optional-lever detail, and edge cases moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Mindset — five principles

Macie cost optimization is a coverage-vs-cost decision, not a pure
classification-completeness exercise. The goal is the smallest set of
high-signal assessments that maintains the security/compliance posture
— not the maximum scan depth on every bucket.

Five principles guide every recommendation:

- **Automated discovery manages scope; targeted jobs multiply it.**
  Automated discovery increments only new/changed objects per run;
  a recurring targeted job re-scans the full included scope each run.
- **Sampling is the default cost control.** Macie samples up to a
  per-bucket ceiling; forcing deep evaluation multiplies per-object
  identifier cost.
- **Identifier scope is a per-object cost multiplier.** Every managed
  and custom identifier selected is evaluated against every sampled
  object. Halving the identifier scope roughly halves per-object cost.
- **Suppression rules cut re-evaluation.** Suppressing known-safe
  prefixes prevents Macie from re-emitting findings and re-evaluating
  the same known-good objects on subsequent runs.
- **Multi-account delegation centralises and deduplicates.** A single
  Macie delegated administrator across the org avoids per-account
  standalone assessment of the same shared data.

## Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **Automated discovery is incremental.** It classifies new and changed
  objects only, on a cadence managed by the service. Recurring
  targeted jobs re-scan the entire included scope every run — this is
  the #1 hidden Macie cost multiplier.
- **`managedDataIdentifierSelector: ALL` is expensive.** Every managed
  identifier runs against every sampled object. Selecting `INCLUDE`
  with only the relevant categories (e.g., PII, financial) cuts per-
  object cost proportionally.
- **Sampling is per-bucket and configurable.** Macie samples up to a
  ceiling of objects per bucket per run by default. Forcing full scan
  multiplies per-object identifier cost — only justified for high-
  risk buckets with explicit compliance mandates.
- **Custom identifiers run regex per evaluated object.** A poorly-
  written regex (catastrophic backtracking) can blow up per-object
  evaluation time. Audit custom identifiers for regex performance.
- **Suppression rules apply at the finding level.** Suppressing a
  known-safe prefix prevents Macie from re-emitting findings for that
  prefix on subsequent runs, which also reduces re-evaluation cost
  for re-processed objects.
- **Per-account standalone Macie duplicates coverage.** In a Macie-
  enabled org, a single delegated administrator covers all member
  accounts. Running standalone Macie in member accounts on the same
  data doubles assessment cost.
- **Classification export is a one-way valve.** Once exported to S3,
  findings can be queried via Athena repeatedly without re-invoking
  Macie. This is the cost-efficient way to do recurring analysis.
- **`bucketCriteria` is the scope, not just a hint.** Every bucket in
  `bucketCriteria.matches` is in scope. Mis-classifying a log bucket
  as "data" puts it in the assessment set.
- **Log/archive buckets charged at the full per-GB rate.** S3
  Standard-IA and Glacier objects are still assessed by Macie at the
  full per-GB rate; the storage class is irrelevant to Macie cost.
- **The free tier covers a fixed number of buckets.** Macie's free
  tier includes bucket-level monitoring for a limited number of S3
  buckets per account. Beyond that, per-bucket monthly fees apply.

## Step 2: Scan frequency tuning

For targeted jobs that must stay targeted (e.g., specific compliance
scan), frequency is the second lever.

**Decision gate:**
| Current frequency | Compliance requirement | Recommended frequency |
|---|---|---|
| Daily | Monthly compliance window | Weekly or monthly |
| Daily | Quarterly compliance window | Monthly |
| Weekly | Annual compliance window | Monthly or quarterly |
| On each upload | None (operational habit) | Weekly batch |

Reducing daily → weekly cuts runs_per_month from ~30 to ~4, a 7.5x
reduction in per-GB assessment cost for that job.

## Step 4: Sampling vs full scan

Macie samples S3 objects per bucket per run. The default sampling depth
balances coverage and cost. Forcing deep evaluation multiplies per-
object identifier cost.

**Sampling decision gate:**
| Bucket risk | Sampling recommendation |
|---|---|
| Low-risk (logs, archives, public assets) | Default sampling; consider full exclusion (Step 3) |
| Standard business data | Default sampling |
| High-risk (regulated, customer PII repository) | Default sampling + targeted one-time full scan quarterly |
| Compliance-mandated full scan | Document the mandate; keep full scan but narrow identifier scope (Step 5) |

## Step 5: custom identifier audit

**Custom identifier audit:**
1. List custom identifiers: `aws macie2 list-custom-data-identifiers`
2. For each, evaluate regex performance on a representative object set.
3. Consolidate overlapping identifiers (e.g., three variants of the
   same pattern → one canonical identifier).
4. Remove identifiers that have not matched in 90 days.

## Step 6: Suppression rules — cut re-evaluation

Suppression rules prevent Macie from re-emitting findings on known-safe
objects, which reduces both finding noise and re-evaluation cost on
subsequent runs that re-process those objects.

**Suppression rule pattern:**
```bash
aws macie2 create-findings-filter \
  --name "suppress-known-safe-logs" \
  --action ARCHIVE \
  --finding-criteria '{"criterion":{"s3Bucket.name":{"eq":["access-logs-prod","cloudtrail-archive"]}}}'
```

**When to add suppression:**
- Findings recur on the same known-safe objects run-over-run.
- A bucket has been validated as clean but cannot be excluded (e.g.,
  ownership boundary).
- A specific object prefix is known-safe (e.g., `public/images/`).

## Step 7: Multi-account Macie administrator delegation

In a Macie-enabled organization, a single delegated administrator
account manages Macie across all member accounts. Running standalone
Macie in member accounts duplicates assessment.

**Delegation check:**
```bash
aws organizations list-delegated-administrators \
  --service-principal macie.amazonaws.com
```

**Delegation savings:**
```
per_account_standalone_cost × N_member_accounts = current_spend
delegated_admin_cost          = (one administrator + member-account bucket fees)
saving                        = current_spend − delegated_admin_cost
```

A single delegated administrator centralises configuration, reduces
per-account management overhead, and avoids double-assessment of shared
data.

## Step 8: Classification export to S3 for batch analysis

For recurring findings analysis (e.g., monthly compliance reporting),
exporting classification results to S3 and querying via Athena is
cheaper than re-invoking Macie or paginating findings via the API.

**Export setup:**
```bash
aws macie2 put-classification-export-configuration \
  --configuration '{"s3Destination":{"bucketName":"macie-export-prod","prefix":"classification/","kmsKeyArn":"arn:aws:kms:us-east-1:<acct>:key/<id>"}}'
```

**Athena query pattern:** Once exported, partition findings by date and
bucket; query via Athena at $5/TB scanned. This is the cost-efficient
way to do recurring analysis vs re-running Macie jobs.

## Recent AWS features (2024-2026)

- **Automated data discovery GA (2024-2025):** Service-managed,
  incremental discovery that classifies new and changed S3 objects on
  a service-defined cadence. The cost-efficient default for recurring
  sensitive-data coverage.
- **Improved managed data identifiers:** Expanded coverage for financial,
  healthcare, and credentials categories. Selectable via
  `managedDataIdentifierSelector: INCLUDE` with specific IDs.
- **Scalable custom data identifiers:** Performance improvements to
  regex evaluation, but catastrophic backtracking patterns still cause
  per-object evaluation spikes. Audit custom identifiers regularly.
- **Multi-account delegation enhancements (2024):** Delegated
  administrator supports all member accounts in the org; region-by-
  region delegation required for multi-region deployments.
- **Classification export to S3 + Athena:** Native export of
  classification results to S3 for batch Athena analysis. Reduces
  recurring query cost vs paginating the findings API.
- **Macie integration with Security Hub:** Findings flow to Security
  Hub; suppression rules in Macie propagate as `ARCHIVED` in Hub.
- **S3 data scanning performance (2024-2025):** Improved sampling
  efficiency for large buckets; reduces per-run overhead.
