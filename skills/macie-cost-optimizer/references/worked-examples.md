# Worked Examples — Macie Cost Optimizer

Full worked examples covering each optimization dimension. Each example
shows the input, the decision walkthrough, and the emitted output block.

## Example 1: Recurring-to-automated discovery migration

**Input:** Daily recurring targeted job on a 12.4 TB data lake;
automated discovery enabled but underutilised; 4 log/archive buckets in
scope; `managedDataIdentifierSelector: ALL`; PCI compliance scope.

**Decision walkthrough:**
1. Step 1 (discovery mode): Recurring scheduled job on a stable data
   lake → migrate to automated discovery. Automated discovery covers
   new/changed objects only (~5% monthly churn) vs full 12.4 TB per
   run.
2. Step 3 (bucket selection): 4 log/archive buckets in scope → exclude
   via `update-classification-scope`.
3. Step 5 (identifier scope): `ALL` for PCI-only compliance → narrow to
   `INCLUDE` with financial + credentials identifiers.
4. Steps 2, 4, 6, 7, 8: No finding (sampling default, no suppression
   needed, already delegated, no export pipeline gap).

**Emitted block:**
```text
TARGET: macie-targeted-pci-scan-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Recurring daily targeted job covers a stable data lake that
  automated discovery could manage incrementally. At 12.4 TB per run ×
  30 runs/month, the recurring job is the dominant Macie line item.
  Migrating coverage to automated discovery (5% monthly churn) projects
  ~95% reduction in assessment spend. Additionally, 4 log/archive
  buckets are in scope and should be excluded; managedDataIdentifier-
  Selector: ALL is overbroad for a PCI-only compliance scope.
RECOMMENDATION:
  Current: targeted SCHEDULED job, daily, 18 buckets, ALL identifiers, delegated admin
  Proposed: automated discovery, service cadence, 14 buckets, INCLUDE (PCI), delegated admin
  Dimensions changed: mode (Step 1) + buckets (Step 3) + identifiers (Step 5)
  Dimensions checked: mode → (targeted to automated)  frequency → (daily to service)
    buckets → (18 to 14)  sampling ✓ (default retained)
    identifiers → (ALL to INCLUDE PCI)  suppression ✓ (none needed)
    delegation ✓ (already delegated)  export ✓ (Athena pipeline in place)
  Confidence: HIGH — job configuration cited; Cost Explorer cross-check agrees
ESTIMATED_SAVINGS:
  Current monthly: $37,210.00
    assessment: 12,400 GB × 30 runs × $0.10 = $37,200.00
    per-bucket fees: 18 × $0.50 = $9.00
    finding storage: $1.00
  Projected monthly: $629.00
    assessment: 620 GB (5% churn) × $0.10 = $62.00
    per-bucket fees: 14 × $0.50 = $7.00
    automated discovery overhead: $560.00
  Monthly saving: $36,581.00
  Annual saving: $438,972.00
MIGRATION_STEPS:
  1. Verify automated discovery covers the data lake buckets:
     aws macie2 get-automated-discovery-configuration
     aws macie2 get-classification-scope --name <scope>
  2. Exclude log/archive buckets:
     aws macie2 update-classification-scope --name <scope> \
       --s3 '{"excludes":{"bucketNames":["access-logs-prod","cloudtrail-archive","public-assets","backup-tier-1"]}}'
  3. Narrow managed identifier scope on remaining targeted jobs:
     aws macie2 update-classification-job --job-id <id> \
       --managed-data-identifier-selector INCLUDE \
       --managed-data-identifier-ids "AWSManagedFinancialUS,AWSManagedCredentialsKeywords"
  4. Disable the recurring targeted job once automated discovery is confirmed:
     aws macie2 update-classification-job --job-id <id> --status DISABLED
  5. Monitor Cost Explorer (Service=Macie) for 7 days post-change
CONFIRM: About to migrate macie-targeted-pci-scan-prod from recurring
  daily targeted job to automated discovery, exclude 4 log/archive
  buckets, narrow identifier scope to PCI. Monthly saving $36,581.00
  (98.3% reduction). Proceed? (yes/no)
```

## Example 2: Scan frequency reduction (weekly to monthly)

**Input:** Weekly recurring targeted job on 3 high-risk regulated
buckets (8 TB cumulative over 4 runs/month); quarterly compliance
window; targeted jobs required by compliance policy; compliance officer
signed off on monthly cadence.

**Decision walkthrough:**
1. Step 1 (discovery mode): Targeted jobs required by compliance policy
   → cannot migrate to automated discovery. Keep targeted.
2. Step 2 (frequency): Weekly (4 runs/month) with quarterly compliance
   window → reduce to monthly (1 run/month). 75% reduction in runs.

**Emitted block (abbreviated):**
```text
TARGET: macie-weekly-compliance-scan
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Weekly recurring targeted job on a quarterly compliance window
  is 4x over-scheduled. Reducing to monthly (1 run/month) cuts per-GB
  assessment cost by 75%. Targeted jobs are retained per compliance
  policy; only frequency is changed.
RECOMMENDATION:
  Current: targeted SCHEDULED job, weekly (4 runs/month), 3 buckets
  Proposed: targeted SCHEDULED job, monthly (1 run/month), 3 buckets
  Dimensions changed: frequency (Step 2)
  Dimensions checked: mode ✓ (targeted required)  frequency → (weekly to monthly)
    buckets ✓ (all high-risk, no exclusions)  sampling ✓ (default)
    identifiers ✓ (already narrowed)  suppression ✓ (none needed)
    delegation ✓ (already delegated)  export ✓ (in place)
  Confidence: HIGH — compliance officer sign-off cited
ESTIMATED_SAVINGS:
  Current monthly: $800.00
    assessment: 2,000 GB × 4 runs × $0.10 = $800.00
  Projected monthly: $200.00
    assessment: 2,000 GB × 1 run × $0.10 = $200.00
  Monthly saving: $600.00
  Annual saving: $7,200.00
MIGRATION_STEPS:
  1. Update the job schedule frequency to monthly:
     aws macie2 update-classification-job --job-id job-weekly-compliance-scan \
       --schedule-frequency '{"monthly":{"dayOfMonth":"1"}}'
  2. Monitor the next monthly run for completion and finding coverage
CONFIRM: About to reduce macie-weekly-compliance-scan from weekly to
  monthly. Monthly saving $600.00 (75% reduction). Proceed? (yes/no)
```

## Example 3: Bucket exclusion + identifier narrowing

**Input:** 20 buckets in scope (6 are log/archive/system);
`managedDataIdentifierSelector: ALL`; GDPR PII-only compliance regime;
6 log/archive buckets validated clean by data governance team.

**Decision walkthrough:**
1. Step 3 (bucket selection): 6 log/archive/system buckets with zero
   prior findings and governance validation → exclude.
2. Step 5 (identifier scope): `ALL` for GDPR PII-only → narrow to
   `INCLUDE` with EU personal data identifiers.

**Emitted block (abbreviated):**
```text
TARGET: macie-automated-discovery-weekly
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: 6 of 20 buckets in scope are log/archive/system buckets with
  zero prior findings, adding per-GB assessment cost with no security
  value. managedDataIdentifierSelector: ALL evaluates every category
  per object for a GDPR PII-only compliance regime — narrowing to EU
  personal data identifiers reduces per-object evaluation cost
  proportionally.
RECOMMENDATION:
  Current: automated discovery, weekly, 20 buckets, ALL identifiers
  Proposed: automated discovery, weekly, 14 buckets, INCLUDE (GDPR PII)
  Dimensions changed: buckets (Step 3) + identifiers (Step 5)
  Dimensions checked: mode ✓ (already automated)  frequency ✓ (weekly)
    buckets → (20 to 14)  sampling ✓ (default)
    identifiers → (ALL to INCLUDE GDPR PII)  suppression ✓ (none needed)
    delegation ✓ (already delegated)  export ✓ (in place)
  Confidence: HIGH — governance team validation cited
ESTIMATED_SAVINGS:
  Current monthly: $480.00
    assessment: 1,200 GB × 4 runs × $0.10 = $480.00
  Projected monthly: $168.00
    assessment: 840 GB (14/20 buckets) × 4 runs × $0.05 (narrower identifiers)
    = $168.00
  Monthly saving: $312.00
  Annual saving: $3,744.00
MIGRATION_STEPS:
  1. Exclude the 6 log/archive/system buckets:
     aws macie2 update-classification-scope --name <scope> \
       --s3 '{"excludes":{"bucketNames":["access-logs-prod","cloudtrail-archive","alb-logs","s3-server-access","system-buckets-aws","temp-staging-ephemeral"]}}'
  2. Narrow managed identifier selector to GDPR PII:
     aws macie2 update-classification-job --job-id <id> \
       --managed-data-identifier-selector INCLUDE \
       --managed-data-identifier-ids "AWSManagedPersonalEU"
  3. Monitor Cost Explorer for 7 days post-change
CONFIRM: About to exclude 6 log/archive/system buckets and narrow
  identifier scope to GDPR PII on macie-automated-discovery-weekly.
  Monthly saving $312.00 (65% reduction). Proceed? (yes/no)
```

## Example 4: Already-optimized (OPTIMIZED)

**Input:** Automated discovery enabled; narrowed identifiers; default
sampling; 3 suppression rules; delegated administrator; Athena export
pipeline; 0 log/archive buckets in scope; $84/month spend.

**Decision walkthrough:** All eight dimensions pass. No savings-
bearing recommendation.

**Emitted block:**
```text
TARGET: macie-already-optimized-macie
VERDICT: OPTIMIZED
REASON: All dimensions verified. Automated discovery covers 12 business-
  data buckets incrementally; identifiers narrowed to PII + financial;
  3 suppression rules prevent known-safe re-evaluation; delegated
  administrator centralises config; Athena export pipeline handles
  recurring analysis. Monthly spend ($84) is proportional to data churn.
RECOMMENDATION:
  Current: automated discovery, service cadence, 12 buckets, INCLUDE (PII+financial), delegated
  Proposed: no change
  Dimensions changed: none
  Dimensions checked: mode ✓ (automated)  frequency ✓ (service cadence)
    buckets ✓ (no log/archive in scope)  sampling ✓ (default)
    identifiers ✓ (narrowed)  suppression ✓ (3 rules active)
    delegation ✓ (delegated)  export ✓ (Athena pipeline)
  Confidence: HIGH — all dimensions verified
ESTIMATED_SAVINGS:
  Current monthly: $84.00
  Projected monthly: $84.00
  Monthly saving: $0.00
  Annual saving: $0.00
MIGRATION_STEPS:
  1. No action required. Continue monitoring Cost Explorer monthly.
CONFIRM: N/A — no state-changing operation proposed.
```

## Example 5: NEED_MORE_INFO (data gate failure)

**Input:** Macie cost line item requested but Cost Explorer returns no
data for Service=Macie in the last 7 days.

**Decision walkthrough:** Data gate fails — Cost Explorer window < 14
days and no job stats provided.

**Emitted block:**
```text
TARGET: macie-deployment-unknown
VERDICT: NEED_MORE_INFO
REASON: Cost Explorer Macie line items absent for the requested window.
  Macie may not be enabled, the filter may be wrong, or the observation
  window is < 14 days. Cannot produce a savings estimate without
  baseline spend data.
RECOMMENDATION:
  Current: unknown
  Proposed: pending data
  Dimensions checked: (all pending — data gate failed)
  Confidence: LOW — data insufficient
ESTIMATED_SAVINGS:
  Current monthly: unknown
  Projected monthly: unknown
  Monthly saving: unknown
MIGRATION_STEPS:
  1. Verify Macie is enabled:
     aws macie2 get-macie-account
  2. Pull 30-day Cost Explorer data:
     aws ce get-cost-and-usage \
       --time-period Start=2026-07-11,End=2026-08-11 \
       --filter '{"Dimensions":{"Key":"SERVICE","Values":["Macie"]}}' \
       --metrics "UnblendedCost"
  3. Pull job stats:
     aws macie2 list-classification-jobs
  4. Re-run the optimization once data is available
CONFIRM: N/A — data gate failed, no state-changing operation proposed.
```

## End-to-end walkthrough — recurring-to-automated + bucket exclusion + identifier narrowing

This walkthrough shows all three dimensions applied in sequence on the
same deployment, with intermediate verification between each step.

### Phase 1: Bucket exclusion (lowest-risk, highest-immediacy)

1. Verify the 4 log/archive buckets have zero HIGH-severity findings in
   the last 90 days via `list-findings`.
2. Apply the exclusion via `update-classification-scope`.
3. Wait for the next scheduled run; confirm the 4 buckets are no longer
   in `bytesProcessed`.

### Phase 2: Identifier narrowing

1. Confirm the compliance regime (PCI) permits narrowing to financial +
   credentials categories.
2. Update the job's `managedDataIdentifierSelector` to `INCLUDE` with
   specific IDs.
3. Wait for the next run; confirm per-object evaluation time drops.

### Phase 3: Discovery mode migration

1. Verify automated discovery covers all 14 remaining business-data
   buckets.
2. Run a parallel automated discovery cycle alongside the targeted job
   for one cycle to confirm coverage parity.
3. Disable the recurring targeted job.
4. Monitor Cost Explorer for 7 days; confirm spend drops to projected
   level.

If at any phase the finding coverage regresses (previously-detected
findings no longer appear), roll back the change:
- Phase 1 rollback: `update-classification-scope` with the buckets
  removed from `excludes`.
- Phase 2 rollback: `update-classification-job` with
  `--managed-data-identifier-selector ALL`.
- Phase 3 rollback: `update-classification-job --status ENABLED` on the
  disabled job.
