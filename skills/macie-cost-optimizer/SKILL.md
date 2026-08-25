---
name: macie-cost-optimizer
description: 'Optimises Amazon Macie cost across seven dimensions: discovery mode selection (automated data discovery vs one-off targeted classification jobs — automated manages scope and is cheaper for recurring coverage), scan frequency tuning (daily vs weekly for large data lakes, balancing detection latency against per-GB assessment cost), bucket selection (excluding infrequently accessed, known-safe, and log/archive buckets from sensitive-data scans), S3 object sampling vs full scan (Macie samples S3 objects per bucket — understanding the sampling depth vs full classification trade-off), custom data identifier cost (regex evaluation runs per evaluated object — over-broad custom identifiers multiply assessment cost), managed data identifier scope reduction (selecting only relevant managed identifiers instead of all), finding suppression rules (suppress known-safe prefixes to prevent re-evaluation cost and reduce noise), multi-account Macie administrator delegation (single delegated Macie administrator vs per-accoun...'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted Macie job configs, bucket statistics, and Cost Explorer Macie line items. Live-account optimization uses aws macie2 get-classification-scope, aws macie2 get-sensitive-data-discovery-jobs, aws macie2 describe-job-creation, aws macie2 get-findings, aws macie2 get-bac (bucket statistics), aws macie2 list-membership-accounts (Macie administrator), aws...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising Amazon Macie cost, migrating from targeted classification jobs to automated data discovery, tuning scan frequency for a large S3 data lake, excluding known-safe or infrequently accessed buckets from Macie scans, reducing custom data identifier evaluation overhead, narrowing managed data identifier scope, configuring finding suppression rules to reduce re-evaluation, consolidating Macie onto a single delegated administrator account, or piping Macie classification exports to Athena for batch analysis.
  when_not_to_use: GuardDuty cost (use guardduty-cost-optimizer), general S3 storage cost (use s3-lifecycle-optimizer), Security Hub finding remediation (use securityhub-finding-remediator), or Macie finding triage/identification work (use macie-finding-triage). This skill focuses on cost-driven optimization decisions for Macie assessment spend, not on classifying the contents of a specific finding.
  activation_triggers: optimise Macie cost, Macie spend too high, Macie classification job cost, Macie automated discovery, Macie targeted classification, Macie scan frequency, Macie daily scan cost, Macie bucket selection, Macie exclude buckets, Macie object sampling, Macie full scan cost, Macie custom data identifier, Macie managed data identifier, Macie suppression rules, Macie finding suppression, Macie delegated administrator, Macie multi-account, Macie classification export, Macie Athena export, Macie data lake cost, Macie FinOps, reduce Macie bill, security cost review
  invocation_schema: 'Input: either (a) a Macie-enabled account or org context with job configurations and bucket statistics, (b) a Cost Explorer Macie cost line-item document, OR (c) Macie job configurations (jobType, scoping, managedDataIdentifierSelector, sampling) with at least 14 days of observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/MIGRATION_STEPS block per Macie scope, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE, NEED_MORE_INFO.'
  invocation_example: "# Minimal valid input (offline job classification):\nMacie administrator: delegated (org-management)\nRegion: us-east-1\nClassification jobs (last 30 days):\n  - jobId: job-targeted-pci-scan\n    jobType: ONE_TIME\n    initialRun: daily schedule (recurring created as one-time)\n    buckets: [data-lake-raw, data-lake-curated, access-logs]\n    managedDataIdentifierSelector: ALL\n    sampling: s3Scope with includes '*'\n    jobsRun: 30, objectsEvaluated: 480,000,000, GBassessed: 12,400\nAutomated discovery: ENABLED but scope excludes access-logs\nCost Explorer (Service=Macie, last 30 days): $1,240\nBucket statistics: 18 buckets, 4 are log/archive, 2 are known-safe\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Macie, Amazon Macie, data discovery, sensitive data, PII detection, cost optimization, automated discovery, targeted classification, classification job, scan frequency, bucket selection, object sampling, custom data identifier, managed data identifier, suppression rules, finding suppression, multi-account, delegated administrator, classification export, Athena analysis, data lake security, security FinOps
  tags: macie, security, data-protection, cost-optimization, finops, sensitive-data, data-discovery
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

> The five Mindset principles moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — incremental automated discovery, sampling as cost control, identifier scope as multiplier, suppression, delegation.
> Load them when framing a recommendation.

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
> The eight required data-source CLI listings moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md); full sequences are in references/macie-pricing-and-discovery-modes.md.
> Load it before pulling signals for a recommendation.

### Data-quality short-circuits

> The data-quality short-circuit table and the Cost-Explorer-vs-job-stats disagreement rule moved verbatim to [references/error-handling.md](references/error-handling.md).
> Load it when the data gate fails or numbers disagree.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

> Step 0 deep-dive moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — incremental discovery, identifier-selector cost, per-bucket sampling, regex backtracking, suppression mechanics, delegation duplication, export one-way valve, bucketCriteria scope, storage-class irrelevance, free-tier limits.
> Load it before classifying a deployment.

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

> The recurring-to-automated savings math and the 12 TB worked numbers moved verbatim to [references/worked-examples.md](references/worked-examples.md).
> Load it when quantifying a discovery-mode migration.

### Step 2: Scan frequency tuning

> The frequency decision gate and the daily-to-weekly 7.5x reduction moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load it when a targeted job must stay targeted.

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

> The update-classification-scope exclusion CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
> Load it when applying an exclusion.

### Step 4: Sampling vs full scan

> The sampling decision gate moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load it when sampling depth is questioned.

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

> The four-step custom identifier audit moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load it when identifier-heavy.

### Step 6: Suppression rules — cut re-evaluation

> The create-findings-filter pattern and when-to-suppress list moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load it for noisy-finding deployments.

### Step 7: Multi-account Macie administrator delegation

> The delegation check CLI and delegation savings math moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load it for org-wide deployments.

### Step 8: Classification export to S3 for batch analysis

> The export setup CLI and Athena query pattern moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load it for recurring query workloads.

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

> The annotated Output-format template moved verbatim to [references/worked-examples.md](references/worked-examples.md); the STRICT output contract below is the enforced shape.
> Load it when emitting the result block.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Required output structure

Every response MUST be a single block using these literal labels, in this
order. Do NOT substitute markdown headings, camelCase, or bold variants.
The CHECKLIST rows surface the current scan config vs recommended for
every optimization dimension so the operator can see the full posture
in one read.

```text
MACIE_JOB: <macie-deployment-or-job-id>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE | NEED_MORE_INFO | BLOCKED
REASON: <1-2 sentences naming the recommendation and the supporting data>
CHECKLIST:
  [→|✓]  Discovery mode        current: <targeted SCHEDULED | ONE_TIME | automated>   recommended: <...>
  [→|✓]  Scan frequency        current: <daily | weekly | monthly>                    recommended: <...>
  [→|✓]  Bucket selection      current: <N buckets in scope>                          recommended: <M buckets (exclude <names>)>
  [→|✓]  Object sampling       current: <default | deep/full>                         recommended: <...>
  [→|✓]  Managed identifiers   current: <ALL | INCLUDE [...] >                        recommended: <...>
  [→|✓]  Custom identifiers    current: <N configured, regex audited>                 recommended: <...>
  [→|✓]  Suppression rules     current: <0 | N rules>                                 recommended: <...>
  [→|✓]  Multi-account deleg.  current: <standalone | delegated admin (acct)>         recommended: <...>
  [→|✓]  Export pipeline       current: <none | S3+Athena>                            recommended: <...>
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

5. **NEVER omit a dimension from the CHECKLIST.** All nine rows MUST
   appear, each marked `→` (finding, change recommended) or `✓`
   (verified, no change). Inventing a 10th row or collapsing rows
   together is a contract violation.

6. **NEVER present a cost-neutral reconfiguration as "cost savings."**
   Surface the coverage/latency improvement explicitly in REASON and set
   `Monthly saving: $0.00` with verdict `OPTIMIZED` (or
   `FURTHER_OPTIMIZATION_AVAILABLE` ONLY if a different dimension has
   positive saving).

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

8. **NEVER substitute markdown headings, bold, or camelCase variants
   for the literal labels** (`## Verdict`, `**VERDICT:**`, `verdict =`
   are all invalid). The labels are parser-anchored.

9. **NEVER emit a `→` row in CHECKLIST without a corresponding
   MIGRATION_STEPS entry.** Every finding dimension MUST have a CLI
   action that resolves it.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent and shows concrete monthly
USD figures. Copy this shape exactly.

```text
MACIE_JOB: macie-targeted-pci-scan-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Recurring daily targeted job covers a stable 12.4 TB data lake
  that automated discovery could manage incrementally. 4 log/archive
  buckets are in scope and add per-GB cost with no security value.
  managedDataIdentifierSelector: ALL is overbroad for a PCI-only
  compliance scope. Cost Explorer cross-check agrees with job stats.
CHECKLIST:
  [→] Discovery mode        current: targeted SCHEDULED job (nightly)           recommended: automated data discovery (incremental)
  [→] Scan frequency        current: daily (30 runs/month)                      recommended: service-managed cadence
  [→] Bucket selection      current: 18 buckets in scope (4 logs/archive)       recommended: 14 buckets (exclude access-logs-prod, cloudtrail-archive, alb-logs, public-assets)
  [✓] Object sampling       current: default sampling                           recommended: default (no change)
  [→] Managed identifiers   current: ALL (every managed ID per object)          recommended: INCLUDE [AWSManagedFinancialUS, AWSManagedCredentialsKeywords]
  [✓] Custom identifiers    current: 3 configured, regex audited                recommended: keep (no change)
  [→] Suppression rules     current: 0 rules                                    recommended: add 1 rule (ARCHIVE known-safe log prefixes)
  [✓] Multi-account deleg.  current: delegated admin (org-management)           recommended: keep (no change)
  [✓] Export pipeline       current: S3 + Athena                                recommended: keep (no change)
ESTIMATED_SAVINGS:
  Current monthly: $37,210.00
    assessment: 12,400 GB × 30 runs × $0.10/GB = $37,200.00
    per-bucket fees: 18 buckets × $0.50 = $9.00
    finding storage: $1.00
  Projected monthly: $629.00
    assessment: 620 GB (5% monthly churn) × $0.10 = $62.00
    per-bucket fees: 14 buckets × $0.50 = $7.00
    automated discovery overhead + finding storage: $560.00
  Monthly saving: $36,581.00    ($37,210.00 − $629.00 = $36,581.00 ✓)
  Annual saving: $438,972.00    ($36,581.00 × 12 = $438,972.00 ✓)
  Assumptions: 12,400 GB in scope per run, 30 runs/month, us-east-1 pricing,
    5% monthly object churn for automated discovery, PCI-only identifier scope
MIGRATION_STEPS:
  1. Verify automated discovery coverage includes the data lake buckets:
     aws macie2 get-automated-discovery-configuration
     aws macie2 get-classification-scope --name default-scope
  2. Exclude log/archive buckets from the classification scope:
     aws macie2 update-classification-scope --name default-scope \
       --s3 '{"excludes":{"bucketNames":["access-logs-prod","cloudtrail-archive","alb-logs","public-assets"]}}'
  3. Narrow managed identifier scope on any remaining targeted jobs:
     aws macie2 update-classification-job --job-id job-targeted-pci-scan \
       --managed-data-identifier-selector INCLUDE \
       --managed-data-identifier-ids "AWSManagedFinancialUS,AWSManagedCredentialsKeywords"
  4. Add a suppression rule for known-safe log prefixes:
     aws macie2 create-findings-filter --name suppress-known-safe-logs \
       --action ARCHIVE \
       --finding-criteria '{"criterion":{"s3Bucket.name":{"eq":["access-logs-prod","cloudtrail-archive"]}}}'
  5. Disable the recurring targeted job once automated discovery is
     confirmed covering the same buckets:
     aws macie2 update-classification-job --job-id job-targeted-pci-scan --status DISABLED
  6. Monitor Cost Explorer (Service=Macie) for 7 days post-change:
     aws ce get-cost-and-usage --filter '{"Dimensions":{"Key":"SERVICE","Values":["Macie"]}}'
CONFIRM: About to migrate macie-targeted-pci-scan-prod from recurring
  daily targeted job to automated discovery, exclude 4 log/archive
  buckets, narrow identifier scope to PCI categories, and add 1
  suppression rule. Monthly saving $36,581.00 (98.3% reduction).
  Proceed? (yes/no)
```

### Perfect example output — OPTIMIZED (no change recommended)

> This second perfect example (OPTIMIZED, no change) moved verbatim to [references/worked-examples.md](references/worked-examples.md); the FURTHER_OPTIMIZATION_AVAILABLE example above stays canonical.
> Load it when the deployment is already optimized.

**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All nine dimensions listed in CHECKLIST with `→` or `✓`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] No scratch/recompute text in the block?
- [ ] All labels are literal all-caps (no markdown, bold, or camelCase)?

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

> The 2024-2026 feature notes moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load on demand when checking recent feature availability.

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

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — pre-existing worked-example set, now also holding the discovery-mode savings math, the annotated Output-format template, and the OPTIMIZED perfect example.
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 non-obvious behaviours, the five Mindset principles, optional-lever deep dives (scan frequency, sampling, suppression, delegation, export), the custom identifier audit, and 2024-2026 feature notes.
- [references/error-handling.md](references/error-handling.md) — data-quality short-circuits for the pre-flight gate and the Cost-Explorer-vs-job-stats disagreement rule.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — required data-source CLI list for the data gate and the bucket-exclusion apply CLI.
- [references/macie-pricing-and-discovery-modes.md](references/macie-pricing-and-discovery-modes.md) — pre-existing pricing tables, automated-vs-targeted comparison, and full CLI sequences.

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
