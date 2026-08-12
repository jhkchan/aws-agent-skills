---
name: macie-cost-optimizer
description: 'Optimises Amazon Macie cost across seven dimensions: discovery mode selection (automated data discovery vs one-off
  targeted classification jobs — automated manages scope and is cheaper for recurring coverage), scan frequency tuning (daily
  vs weekly for large data lakes, balancing detection latency against per-GB assessment cost), bucket selection (excluding
  infrequently accessed, known-safe, and log/archive buckets from sensitive-data scans), S3 object sampling vs full scan (Macie
  samples S3 objects per bucket — understanding the sampling depth vs full classification trade-off), custom data identifier
  cost (regex evaluation runs per evaluated object — over-broad custom identifiers multiply assessment cost), managed data
  identifier scope reduction (selecting only relevant managed identifiers instead of all), finding suppression rules (suppress
  known-safe prefixes to prevent re-evaluation cost and reduce noise), multi-account Macie administrator delegation (single
  delegated Macie administrator vs per-accoun...'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification
  works from pasted Macie job configs, bucket statistics, and Cost Explorer Macie line items. Live-account optimization uses
  aws macie2 get-classification-scope, aws macie2 get-sensitive-data-discovery-jobs, aws macie2 describe-job-creation, aws
  macie2 get-findings, aws macie2 get-bac (bucket statistics), aws macie2 list-membership-accounts (Macie administrator),
  aws organizations list-delegated-administrators (delegation status), aws ce get-cost-and-usage (filter Service=Macie), aws
  s3api list-buckets (bucket inventory), and aws ce get-cost-and-usage-with-resources (resource-level Macie spend). Pricing
  references us-east-1 published rates as of 2026; re-state regional rates from the reference matrix for other regions.
keywords:
- Macie
- Amazon Macie
- data discovery
- sensitive data
- PII detection
- cost optimization
- automated discovery
- targeted classification
- classification job
- scan frequency
- bucket selection
- object sampling
- custom data identifier
- managed data identifier
- suppression rules
- finding suppression
- multi-account
- delegated administrator
- classification export
- Athena analysis
- data lake security
- security FinOps
tags:
- macie
- security
- data-protection
- cost-optimization
- finops
- sensitive-data
- data-discovery
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Security
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising Amazon Macie cost, migrating from targeted classification jobs to automated data discovery, tuning
    scan frequency for a large S3 data lake, excluding known-safe or infrequently accessed buckets from Macie scans, reducing
    custom data identifier evaluation overhead, narrowing managed data identifier scope, configuring finding suppression rules
    to reduce re-evaluation, consolidating Macie onto a single delegated administrator account, or piping Macie classification
    exports to Athena for batch analysis.
  when_not_to_use: GuardDuty cost (use guardduty-cost-optimizer), general S3 storage cost (use s3-lifecycle-optimizer), Security
    Hub finding remediation (use securityhub-finding-remediator), or Macie finding triage/identification work (use macie-finding-triage).
    This skill focuses on cost-driven optimization decisions for Macie assessment spend, not on classifying the contents of
    a specific finding.
  activation_triggers:
  - optimise Macie cost
  - Macie spend too high
  - Macie classification job cost
  - Macie automated discovery
  - Macie targeted classification
  - Macie scan frequency
  - Macie daily scan cost
  - Macie bucket selection
  - Macie exclude buckets
  - Macie object sampling
  - Macie full scan cost
  - Macie custom data identifier
  - Macie managed data identifier
  - Macie suppression rules
  - Macie finding suppression
  - Macie delegated administrator
  - Macie multi-account
  - Macie classification export
  - Macie Athena export
  - Macie data lake cost
  - Macie FinOps
  - reduce Macie bill
  - security cost review
  invocation_schema: 'Input: either (a) a Macie-enabled account or org context with job configurations and bucket statistics,
    (b) a Cost Explorer Macie cost line-item document, OR (c) Macie job configurations (jobType, scoping, managedDataIdentifierSelector,
    sampling) with at least 14 days of observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/MIGRATION_STEPS
    block per Macie scope, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE, NEED_MORE_INFO.'
  invocation_example: "# Minimal valid input (offline job classification):\nMacie administrator: delegated (org-management)\n\
    Region: us-east-1\nClassification jobs (last 30 days):\n  - jobId: job-targeted-pci-scan\n    jobType: ONE_TIME\n    initialRun:\
    \ daily schedule (recurring created as one-time)\n    buckets: [data-lake-raw, data-lake-curated, access-logs]\n    managedDataIdentifierSelector:\
    \ ALL\n    sampling: s3Scope with includes '*'\n    jobsRun: 30, objectsEvaluated: 480,000,000, GBassessed: 12,400\nAutomated\
    \ discovery: ENABLED but scope excludes access-logs\nCost Explorer (Service=Macie, last 30 days): $1,240\nBucket statistics:\
    \ 18 buckets, 4 are log/archive, 2 are known-safe\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION,\
    \ ESTIMATED_SAVINGS, MIGRATION_STEPS)."
---

# Macie Cost Optimizer

## What this skill does

Translates an Amazon Macie deployment's assessment posture into a concrete
cost-optimization recommendation with a dollar-denominated savings
estimate. The verdict is the highest-leverage action across seven
dimensions — discovery mode, scan frequency, bucket selection, sampling,
custom identifier scope, managed identifier scope, suppression rules,
multi-account delegation, and export pipeline — applied in priority
order. Always pairs the recommendation with exact CLI commands.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Five headline rules and the cost formula | First read |
| Mindset | Why automated discovery beats targeted jobs for recurring coverage | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a deployment |
| Pre-flight data gate | Macie jobs, bucket stats, Cost Explorer | Before any recommendation |
| Step 0 non-obvious behaviours | Sampling, suppression, identifier scope, delegation | Edge cases |
| Step 1 Discovery mode | Automated vs targeted job selection | The headline savings dimension |
| Step 2 Scan frequency | Daily vs weekly for large data lakes | Data lake deployments |
| Step 3 Bucket selection | Exclude known-safe, infrequently accessed, logs | High bucket count |
| Step 4 Sampling vs full scan | Sampling depth and per-object evaluation | Custom identifier cost |
| Step 5 Custom & managed identifiers | Scope reduction, regex evaluation overhead | Identifier-heavy deployments |
| Step 6 Suppression rules | Suppress known-safe prefixes to cut re-evaluation | Noisy finding deployments |
| Step 7 Multi-account delegation | Single admin vs per-account | Org-wide deployments |
| Step 8 Classification export | Pipe to S3 + Athena for batch analysis | Recurring query workloads |
| Step 9 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, dry-run validation | Before any apply CLI |

## Quick start

- **Automated discovery is cheaper than recurring targeted jobs for
  steady coverage.** Macie's automated data discovery manages scope
  per bucket on the service side — a daily-recurring targeted job
  scans the full included scope every run, multiplying per-GB cost.
  Migrate recurring coverage to automated discovery; reserve one-time
  targeted jobs for ad-hoc investigations.
- **Cost formula (memorise this):**
  `monthly_macie_cost = (GB_assessed_per_run × runs_per_month × $/GB)
                        + per_bucket_monthly_fee + finding_storage`
- **Exclude known-safe and infrequently accessed buckets.** Log,
  archive, and known-safe buckets add per-GB assessment cost with no
  security value. Exclude them from the classification scope.
- **Sampling is built in; full scans cost multiples.** Macie samples
  S3 objects per bucket by default. Forcing deep/full evaluation
  multiplies per-object identifier cost — only do this for high-risk
  buckets.
- **Narrow managed identifier scope.** `managedDataIdentifierSelector: ALL`
  evaluates every managed identifier per object. Selecting only the
  relevant categories (e.g., `INCLUDE` for PII-only) reduces per-
  object evaluation cost proportionally.

## Mindset

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

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| Recurring targeted job covers what automated discovery could manage AND projected saving > 0 | **FURTHER_OPTIMIZATION_AVAILABLE** (discovery mode) | Step 1 — migrate to automated discovery |
| Daily recurring job on a data lake with > 1 TB per run AND weekly cadence meets compliance | **FURTHER_OPTIMIZATION_AVAILABLE** (frequency) | Step 2 — reduce to weekly or on-demand |
| Log/archive/known-safe buckets included in job scope | **FURTHER_OPTIMIZATION_AVAILABLE** (bucket selection) | Step 3 — exclude via `s3Excludes` |
| `sampling` forces deep evaluation AND no compliance requirement mandates full scan | **FURTHER_OPTIMIZATION_AVAILABLE** (sampling) | Step 4 — revert to default sampling |
| `managedDataIdentifierSelector: ALL` AND workload only needs PII/financial categories | **FURTHER_OPTIMIZATION_AVAILABLE** (identifier scope) | Step 5 — narrow to relevant categories |
| Custom identifiers run regex over every sampled object AND > 5 custom identifiers configured | **FURTHER_OPTIMIZATION_AVAILABLE** (custom identifiers) | Step 5 — consolidate or narrow custom identifier scope |
| Repeated findings on known-safe prefixes (logs, public assets) with no suppression rule | **FURTHER_OPTIMIZATION_AVAILABLE** (suppression) | Step 6 — add suppression rule for known-safe prefix |
| Per-account standalone Macie on accounts under a Macie-enabled org | **FURTHER_OPTIMIZATION_AVAILABLE** (delegation) | Step 7 — consolidate onto delegated administrator |
| Recurring Macie console query cost for findings analysis | **FURTHER_OPTIMIZATION_AVAILABLE** (export) | Step 8 — pipe classification export to S3 + Athena |
| All dimensions verified AND automated discovery + sampling + suppression + delegation all in place | **OPTIMIZED** | None — continue monitoring |
| Cost Explorer Macie line items absent or window < 14 days | **NEED_MORE_INFO** | Pull 14-30 day Cost Explorer Macie data, re-evaluate |

## Pre-flight: data gate (run before any optimization decision)

Optimization decisions are only as good as the underlying data. Pull
these signals before any recommendation. Full CLI sequences are in
`references/macie-pricing-and-discovery-modes.md`.

**Required data sources** (summarized — see reference for full CLI):
1. Macie membership / delegated administrator status: `aws macie2 get-macie-account` + `aws organizations list-delegated-administrators --service-principal macie.amazonaws.com`
2. Classification jobs: `aws macie2 list-classification-jobs` + `describe-classification-job` for each
3. Automated discovery status: `aws macie2 get-automated-discovery-configuration`
4. Bucket statistics: `aws macie2 get-bucket-statistics` + `aws macie2 list-buckets` (per Macie membership)
5. Classification scope (includes/excludes): `aws macie2 get-classification-scope`
6. Suppression rules: `aws macie2 list-sensitivity-inspection-templates` (filter for suppressions)
7. Cost Explorer Macie spend: `aws ce get-cost-and-usage --filter '{"Dimensions":{"Key":"SERVICE","Values":["Macie"]}}'`
8. Findings volume: `aws macie2 list-findings` + `get-findings` (sample for noise assessment)

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| Cost Explorer Macie line items absent | **NEED_MORE_INFO**. Macie may not be enabled, or filter is wrong. Verify `get-macie-account`. |
| Macie window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| `list-classification-jobs` returns empty AND automated discovery disabled | **NEED_MORE_INFO**. No coverage to optimize. |
| `jobStatus: RUNNING` for > 24 hours on a large bucket | Job is in flight; wait for completion before re-baselining. |
| `lastRunTime` > 30 days ago on a recurring job | Stale config; job may have errored. Verify `lastRunError`. |
| IAM denies `macie2:GetClassificationScope` | Surface as BLOCKED; cannot evaluate excludes without scope access. |

When Cost Explorer and Macie job stats disagree, the Macie job stats
(`bytesProcessed`, `objectsProcessed`) are the ground truth — Cost
Explorer reflects invoiced spend which may lag by up to 24 hours.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

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

### Step 1: Discovery mode — automated vs targeted jobs

The discovery mode is the primary cost lever because recurring targeted
jobs multiply per-GB cost linearly with the schedule frequency.

**Pricing comparison:**
```
Automated discovery:   per-GB fee on NEW/CHANGED objects only, per bucket
                       (incremental — service manages scope and cadence)
Targeted job:          per-GB fee on the ENTIRE included scope, PER RUN
                       (full-scan cost × runs_per_month)
```

**Decision tree:**
```
Is the job recurring (SCHEDULED) on a stable set of buckets?
├── NO (ONE_TIME) → Keep as targeted job; this is the correct use.
└── YES → Is the coverage achievable via automated discovery?
    ├── NO (needs custom identifiers not supported by automated) → Keep targeted.
    └── YES → Is the job effectively providing recurring coverage of
              sensitive-data buckets that automated discovery already covers?
        ├── YES → Migrate to automated discovery; disable the recurring job.
        └── NO  → Keep targeted but reduce frequency (Step 2).
```

**Recurring-to-automated savings math:**
```
recurring_job_cost  = GB_in_scope × runs_per_month × $/GB_assessed
automated_cost      = GB_new_or_changed_per_month × $/GB_assessed
                    ≈ 0.05–0.20 × recurring_job_cost (typical incremental ratio)

monthly_saving      = recurring_job_cost − automated_cost
```

Example: 12 TB data lake, daily recurring job at $0.10/GB assessed:
- Recurring: 12,000 GB × 30 runs × $0.10 = $36,000/month (illustrative)
- Automated (5% churn): 600 GB × $0.10 = $60/month (illustrative)
- Saving: ~$35,940/month — recurring coverage of a stable data lake
  via daily targeted jobs is the dominant Macie cost trap.

### Step 2: Scan frequency tuning

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

### Step 3: Bucket selection — exclude known-safe and infrequently accessed

Bucket selection is the third lever. Log, archive, system, and known-
safe buckets add per-GB cost with no security value.

**Exclusion categories:**
| Bucket type | Why exclude | How to detect |
|---|---|---|
| Access logs (S3 server access, CloudTrail, ALB) | No business data; pure audit log | Name pattern (`*-logs`, `*-cloudtrail`), `cloudtrail` prefix |
| Archive / cold storage | Rarely changes; out of compliance scope | Lifecycle policy transitions to Glacier |
| System buckets | AWS service-managed; no customer data | Name starts with `aws-` or known service prefix |
| Known-safe curated | Validated clean (e.g., public assets, images) | Prior Macie run with zero findings; suppression rule exists |
| Infrequently accessed with no PII history | Per-GB fee not justified by risk | 90-day access pattern; no findings history |

**Applying the exclusion:**
```bash
aws macie2 update-classification-scope \
  --name <scope-name> \
  --s3 '{"excludes":{"bucketNames":["access-logs-prod","cloudtrail-archive","public-assets"]}}'
```

### Step 4: Sampling vs full scan

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

### Step 5: Custom and managed identifier scope reduction

Identifier scope is a per-object cost multiplier. Every selected
identifier runs against every sampled object.

**Managed identifier scope:**
```bash
# Current scope
aws macie2 describe-classification-job --job-id <id> \
  --query 'managedDataIdentifierSelector'

# Narrow from ALL to specific categories
aws macie2 update-classification-job \
  --job-id <id> \
  --managed-data-identifier-selector INCLUDE \
  --managed-data-identifier-ids \
    "AWSManagedCredentialsKeywords,AWSManagedFinancialUS,AWSManagedPersonalUS"
```

**Custom identifier audit:**
1. List custom identifiers: `aws macie2 list-custom-data-identifiers`
2. For each, evaluate regex performance on a representative object set.
3. Consolidate overlapping identifiers (e.g., three variants of the
   same pattern → one canonical identifier).
4. Remove identifiers that have not matched in 90 days.

### Step 6: Suppression rules — cut re-evaluation

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

### Step 7: Multi-account Macie administrator delegation

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

### Step 8: Classification export to S3 for batch analysis

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

### Step 9: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  sum(GB_in_scope_per_job × runs_per_month × $/GB_assessed) +
  (bucket_count × per_bucket_monthly_fee) +
  (finding_storage_GB × $/GB_stored)

projected_monthly_cost =
  sum(GB_new_or_changed_per_job × runs_per_month × $/GB_assessed) +
  (bucket_count_after_exclusion × per_bucket_monthly_fee) +
  (finding_storage_GB_after_suppression × $/GB_stored)

monthly_saving = current_monthly_cost − projected_monthly_cost
```

Always state assumptions: GB assessed per run, runs per month, pricing
region, identifier scope, bucket count before/after exclusion.

### Step 10: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions verified AND automated discovery + sampling + suppression
  + delegation all in place → **OPTIMIZED**.
- Change applied and verified this session → **OPTIMIZED** (post-state).
- Data insufficient (Cost Explorer absent, window < 14 days) →
  **NEED_MORE_INFO**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every `NEED_MORE_INFO`/`BLOCKED` gate.

## Output format

```text
TARGET: <macie-deployment-or-job-id>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <discovery mode>, <frequency>, <bucket count>, <identifier scope>, <delegation>
  Proposed: <discovery mode>, <frequency>, <bucket count>, <identifier scope>, <delegation>
  Dimensions changed: <mode | frequency | buckets | sampling | identifiers | suppression | delegation | export>
  Dimensions checked: <list ALL eight, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>
    assessment: <GB × runs × $/GB>
    per-bucket fees: <bucket_count × $/bucket>
    finding storage: <$amount>
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
  Assumptions: <list (GB assessed, runs/month, pricing region, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <macie-deployment> in <region>.
  Proceed? (yes/no)"
```

Full worked examples (recurring-to-automated, scan frequency reduction,
bucket exclusion, identifier scope narrowing, already-optimized,
NEED_MORE_INFO, and end-to-end walkthrough) are in
`references/worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Required output structure

Every response MUST be a single block using these literal labels, in this
order. Do NOT substitute markdown headings, camelCase, or bold variants.

```text
TARGET: <macie-deployment-or-job-id>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <discovery mode>, <frequency>, <bucket count>, <identifier scope>, <delegation>
  Proposed: <discovery mode>, <frequency>, <bucket count>, <identifier scope>, <delegation>
  Dimensions changed: <mode | frequency | buckets | sampling | identifiers | suppression | delegation | export>
  Dimensions checked: <list ALL eight, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show assessment + per-bucket + finding-storage subtotals
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with
   `Monthly saving: $0.00`.** If every dimension nets zero cost delta,
   the verdict MUST be `OPTIMIZED`.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend a discovery mode change without citing job
   configuration evidence.** The REASON MUST name the job type, run
   frequency, and scope evidence.

5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all eight dimensions, each marked
   ✓ (no finding) or → (finding).

6. **NEVER present a cost-neutral reconfiguration as "cost savings."**
   Surface the coverage/latency improvement explicitly and set
   `Monthly saving: $0.00` with verdict `OPTIMIZED` (or
   `FURTHER_OPTIMIZATION_AVAILABLE` ONLY if a different dimension has
   positive saving).

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent. Copy this shape exactly.

```text
TARGET: macie-targeted-pci-scan-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Recurring daily targeted job covers a stable data lake that
  automated discovery could manage incrementally. At 12.4 TB per run ×
  30 runs/month × $0.10/GB assessed, the recurring job is the dominant
  Macie line item. Migrating coverage to automated discovery (5%
  monthly churn) projects 95% reduction in assessment spend.
  Additionally, 4 log/archive buckets are in scope and should be
  excluded (Step 3), and managedDataIdentifierSelector: ALL is
  overbroad for a PCI-only compliance scope (Step 5).
RECOMMENDATION:
  Current: targeted SCHEDULED job, daily, 18 buckets, ALL identifiers, delegated admin
  Proposed: automated discovery, service cadence, 14 buckets, INCLUDE (PCI categories), delegated admin
  Dimensions changed: mode (Step 1) + buckets (Step 3) + identifiers (Step 5)
  Dimensions checked: mode → (targeted to automated)  frequency → (daily to service)
    buckets → (18 to 14, exclude 4 logs)  sampling ✓ (default sampling retained)
    identifiers → (ALL to INCLUDE PCI)  suppression ✓ (none needed)
    delegation ✓ (already delegated)  export ✓ (Athena pipeline in place)
  Confidence: HIGH — job configuration cited; Cost Explorer cross-check
    agrees; automated discovery already enabled but underutilised.
ESTIMATED_SAVINGS:
  Current monthly: $37,210.00
    assessment: 12,400 GB × 30 runs × $0.10 = $37,200.00
    per-bucket fees: 18 buckets × $0.50 = $9.00
    finding storage: $1.00
  Projected monthly: $629.00
    assessment: 620 GB (5% churn) × $0.10 = $62.00
    per-bucket fees: 14 buckets × $0.50 = $7.00
    automated discovery overhead + finding storage: $560.00 (account-level
      monthly automated discovery + data processing)
    finding storage: $0.00 (suppression applied to known-safe)
  Monthly saving: $36,581.00
    ($37,210.00 − $629.00 = $36,581.00 ✓)
  Annual saving: $438,972.00
MIGRATION_STEPS:
  1. Verify automated discovery coverage includes the data lake buckets:
     aws macie2 get-automated-discovery-configuration
     aws macie2 get-classification-scope --name <scope>
  2. Exclude log/archive buckets from the classification scope:
     aws macie2 update-classification-scope --name <scope> \
       --s3 '{"excludes":{"bucketNames":["access-logs-prod","cloudtrail-archive","alb-logs","public-assets"]}}'
  3. Narrow managed identifier scope on any remaining targeted jobs:
     aws macie2 update-classification-job --job-id <id> \
       --managed-data-identifier-selector INCLUDE \
       --managed-data-identifier-ids "AWSManagedFinancialUS"
  4. Disable the recurring targeted job once automated discovery is
     confirmed covering the same buckets:
     aws macie2 update-classification-job --job-id <id> --status DISABLED
  5. Monitor Cost Explorer (Service=Macie) for 7 days post-change:
     aws ce get-cost-and-usage --filter '{"Dimensions":{"Key":"SERVICE","Values":["Macie"]}}'
CONFIRM: About to migrate macie-targeted-pci-scan-prod from recurring
  daily targeted job to automated discovery, exclude 4 log/archive
  buckets, and narrow identifier scope to PCI categories. Monthly saving
  $36,581.00 (98.3% reduction). Proceed? (yes/no)
```

**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All eight dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, savings-bearing recommendation. |
| `OPTIMIZED` | All dimensions verified (automated discovery + sampling + suppression + delegation + export in place); or a change was applied and verified this session. |
| `NEED_MORE_INFO` | Data gate failed: Cost Explorer Macie line items absent, window < 14 days, or job stats unavailable with no fallback. |
| `BLOCKED` | Hard precondition prevents evaluation: IAM denies `macie2:GetClassificationJob`, Macie not enabled in the account. |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `OPTIMIZED`, never `FURTHER_OPTIMIZATION_AVAILABLE`.
Exception: coverage improvement without cost change is surfaced in
REASON, not as dollar savings.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend disabling a targeted job without confirming
   automated discovery covers the same buckets.** Coverage gaps create
   compliance exposure; verify the automated discovery scope includes
   every bucket the targeted job covered.

2. **NEVER exclude a bucket without verifying it contains no sensitive
   data.** A prior clean Macie run, a documented data classification
   review, or an explicit compliance waiver is required before excluding.

3. **NEVER narrow managed identifier scope without confirming the
   compliance regime.** PCI requires financial identifiers; GDPR
   requires EU personal data identifiers. Verify the compliance scope
   before removing categories.

4. **NEVER add a suppression rule for a prefix that has not been
   validated as known-safe.** Suppression hides findings — only
   suppress after a human-in-the-loop review confirms the objects are
   safe.

5. **NEVER migrate a member account off standalone Macie to delegated
   administrator without confirming the delegation covers the member
   account's regions.** Macie delegation is region-specific; multi-
   region deployments need delegation in each region.

Extended anti-patterns in `references/macie-pricing-and-discovery-modes.md`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Dry-run the exclusion.** Before removing buckets from scope, verify
  via `list-findings` that the bucket has no HIGH-severity findings in
  the last 90 days.
- **Validate compliance scope before narrowing identifiers.** Confirm
  the compliance regime (PCI, HIPAA, GDPR) permits the narrower
  identifier set.
- **Automated discovery scope check.** Before disabling a targeted job,
  run `get-automated-discovery-configuration` and `get-classification-
  scope` to confirm automated discovery covers the same buckets.
- **Suppression rules require human review.** Never auto-suppress; the
  operator must confirm each suppression rule targets known-safe
  objects.
- **Job disablement is reversible.** `update-classification-job --status
  DISABLED` can be reversed with `--status ENABLED`; surface this to
  the operator.
- **Export configuration changes apply to new findings only.** Existing
  exported findings are not re-exported to the new destination.
- **Bulk-operation limit:** Process at most 5 jobs per batch. Sort by
  estimated savings, verify each batch before proceeding. Abort if any
  job shows increased error rate post-change.

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

## References

- `references/macie-pricing-and-discovery-modes.md` — pricing tables,
  automated-vs-targeted comparison, managed identifier category list,
  custom identifier regex audit guidance, sampling depth defaults,
  multi-account delegation matrix, regional pricing multipliers, cost
  calculation worked examples.
- `references/worked-examples.md` — full worked examples (recurring-to-
  automated migration, scan frequency reduction, bucket exclusion,
  identifier scope narrowing, suppression rule creation, already-
  optimized, NEED_MORE_INFO, end-to-end walkthrough).

## Domain

AWS CloudOps / Security Data Discovery Cost Optimization & FinOps.

## AWS documentation

- **Amazon Macie User Guide** — https://docs.aws.amazon.com/macie/latest/user/what-macie-compares.html
- **Amazon Macie pricing** — https://aws.amazon.com/macie/pricing/
- **Macie automated data discovery** — https://docs.aws.amazon.com/macie/latest/user/discovery-jobs.html
- **Macie classification jobs** — https://docs.aws.amazon.com/macie/latest/user/classification-jobs.html
- **Macie managed data identifiers** — https://docs.aws.amazon.com/macie/latest/user/managed-data-identifiers.html
- **Macie custom data identifiers** — https://docs.aws.amazon.com/macie/latest/user/custom-data-identifiers.html
- **Macie findings filters (suppression)** — https://docs.aws.amazon.com/macie/latest/user/findings-filters.html
- **Macie multi-account delegation** — https://docs.aws.amazon.com/macie/latest/user/accounts-macie-delegated-admin.html
- **Macie classification export** — https://docs.aws.amazon.com/macie/latest/user/discovery-results-repository.html
- **AWS Organizations delegated administrators** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_integrate_services.html
- **AWS CLI Macie reference** — https://docs.aws.amazon.com/cli/latest/reference/macie2/
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
