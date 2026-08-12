# Example usage: macie-cost-optimizer

A walkthrough showing the skill optimizing a Macie deployment running a
daily recurring targeted job on a stable data lake, demonstrating the
discovery-mode migration (targeted to automated), the bucket exclusion
(removing log/archive buckets from scope), the identifier scope
narrowing (ALL to PCI categories), the dollar savings math, and the
staged cutover with coverage-verification between each phase.

## Input (user prompt)

> Review our Macie setup before the Q3 security FinOps review. We have
> a daily PCI scan that costs over $37,000 a month. Help me optimize
> the cost.

```text
DeploymentId: macie-targeted-pci-scan-prod
Macie administrator: delegated (org-management)
Region: us-east-1

Classification jobs (last 30 days):
  - jobId: job-targeted-pci-scan
    jobType: SCHEDULED (daily, 30 runs/month)
    buckets: [data-lake-raw, data-lake-curated, data-lake-enriched,
              access-logs-prod, cloudtrail-archive, public-assets,
              backup-tier-1, backup-tier-2, ml-feature-store,
              user-uploads, pii-quarantine, finance-reports,
              hr-records, app-configs, system-buckets, temp-staging,
              analytics-output, report-snapshots]
    managedDataIdentifierSelector: ALL
    sampling: default (per-bucket ceiling)
    jobsRun: 30
    bytesProcessed: 37,200,000,000,000 (37.2 TB cumulative)
    objectsProcessed: 480,000,000

Automated discovery: ENABLED but scope excludes access-logs

Cost Explorer (Service=Macie, last 30 days): $37,210.00

Bucket statistics: 18 buckets total, 4 are log/archive
(access-logs-prod, cloudtrail-archive, public-assets,
backup-tier-1), 2 are known-safe validated clean.

Workload context: stable S3 data lake with ~5% monthly churn.
PCI compliance scope; only financial and credentials identifiers
are required. No daily compliance mandate; monthly cadence
acceptable.
```

## Skill output

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
    automated discovery overhead + data processing: $560.00
  Monthly saving: $36,581.00
    ($37,210.00 − $629.00 = $36,581.00 ✓)
  Annual saving: $438,972.00
MIGRATION_STEPS:
  1. Verify automated discovery covers the data lake buckets:
     aws macie2 get-automated-discovery-configuration
     aws macie2 get-classification-scope --name <scope>
  2. Exclude log/archive buckets from the classification scope:
     aws macie2 update-classification-scope --name <scope> \
       --s3 '{"excludes":{"bucketNames":["access-logs-prod","cloudtrail-archive","public-assets","backup-tier-1"]}}'
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

## What the skill caught that a generic assistant misses

1. **Automated discovery is incremental; recurring targeted jobs
   multiply.** A generic assistant says "consider automated discovery."
   The skill cites the job configuration (SCHEDULED, daily, 30 runs)
   and projects the incremental ratio (~5% monthly churn → ~95%
   assessment reduction) with dollar math.

2. **Three dimensions stack.** The skill stacks three savings: discovery
   mode migration (Step 1) + bucket exclusion (Step 3) + identifier
   narrowing (Step 5). A generic assistant captures only the mode change
   and leaves bucket and identifier savings on the table.

3. **Coverage-verification before disabling.** The skill requires
   confirming automated discovery covers the same buckets BEFORE
   disabling the targeted job. A generic assistant disables the job
   without verifying coverage, creating a potential compliance gap.

4. **Compliance scope drives identifier narrowing.** The skill cites the
   PCI compliance regime to justify narrowing from ALL to financial +
   credentials identifiers. A generic assistant says "consider narrowing
   identifiers" without checking what the compliance regime requires.

5. **Cost arithmetic is shown explicitly.** The skill shows the formula
   (`12,400 GB × 30 runs × $0.10`) so the operator can verify. A generic
   assistant says "this should save money" without showing the math.

6. **CONFIRM gate with rollback plan.** The skill emits a CONFIRM prompt
   and the migration steps include a verification step before disabling
   the job. A generic assistant jumps straight to the CLI without a
   safety gate.

## Slash-command invocation

```
/aws:optimize-macie-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our Macie spend for the Q3 security FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: macie-cost-optimizer]` and hands off
to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new configuration:

```bash
# Confirm automated discovery is covering the expected buckets
aws macie2 get-automated-discovery-configuration \
  --profile default --region us-east-1

# Confirm the classification scope excludes the log/archive buckets
aws macie2 get-classification-scope --name <scope> \
  --profile default --region us-east-1 | \
  jq '.s3.excludes.bucketNames'

# Confirm the targeted job is disabled
aws macie2 describe-classification-job --job-id <id> \
  --profile default --region us-east-1 | \
  jq '.jobStatus'

# Monitor Macie spend for 7 days post-change
aws ce get-cost-and-usage \
  --time-period Start=2026-08-05,End=2026-08-12 \
  --granularity DAILY \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Macie"]}}' \
  --metrics "UnblendedCost" \
  --profile default --region us-east-1
```

If finding coverage regresses (previously-detected findings no longer
appear in the automated discovery results), roll back by re-enabling the
targeted job:

```bash
aws macie2 update-classification-job \
  --job-id <id> --status ENABLED \
  --profile default --region us-east-1
```

## Fleet-wide extension

For an org with multiple Macie deployments across member accounts:

1. Verify the delegated administrator covers all member accounts via
   `aws organizations list-delegated-administrators --service-principal
   macie.amazonaws.com`.
2. Pull all classification jobs across member accounts via the
   delegated administrator's Macie membership.
3. Filter to recurring SCHEDULED jobs (the cost-multiplier pattern).
4. For each, evaluate the automated-discovery migration opportunity
   (Step 1).
5. Sort by estimated monthly savings (largest first).
6. Slice into batches of 5 jobs.
7. For each batch: emit per-job MIGRATION_STEPS, then a single CONFIRM
   for the batch.
8. Verify each batch before proceeding to the next.
9. After the mode sweep, evaluate bucket exclusion (Step 3) and
   identifier narrowing (Step 5) for the remaining targeted jobs.
