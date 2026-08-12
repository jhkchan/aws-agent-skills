# Example usage: cloudtrail-cost-optimizer

A walkthrough showing the skill optimizing an organization's CloudTrail
configuration, demonstrating the org-trail consolidation (member-trail
removal), the S3 data event curation, the S3 lifecycle rollout, and the
dollar savings math.

## Input (user prompt)

> Review our CloudTrail setup before our Q3 FinOps review. We have an
> org trail plus a bunch of member trails that I think are duplicating
> events, and our data event bill is way higher than expected.

```text
TrailName: aws-organizational-trail-primary
IsOrganizationTrail: true
IsMultiRegionTrail: true
IncludeManagementEvents: true
Status: RUNNING

Organization:
  ManagementAccount: 111111111111
  MemberAccounts: 12

Trail inventory (organization):
  - aws-organizational-trail-primary (org trail, RUNNING)
  - member-trail-acct-2 through member-trail-acct-13

Event selectors:
  - ManagementEvents: true
  - S3 data events: All Buckets (ReadWriteType: All)

S3 log bucket: org-cloudtrail-logs-us-east-1
S3 lifecycle policy: NONE

Metrics (last 90 days):
  - Org trail log files/month: 1,400,000
  - Member trail log files/month (each): 116,667
  - Total S3 data events/month: 142,500,000 (83% low-value)
  - S3 storage: 850 GB in Standard
  - KMS keys: 13 (one per trail)
  - SNS topics: 13 (one per trail)
  - Monthly CloudTrail spend: $1,847.32

Region: us-east-1
```

## Skill output

```text
TARGET: aws-organizational-trail-primary
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Organization trail captures all member-account events but 12
  redundant member trails duplicate management-event storage, KMS, and
  SNS overhead. Separately, S3 data events on All Buckets includes
  118M events/month (83%) from low-audit-value log/CDN buckets, and the
  log bucket has no lifecycle policy — 850 GB sits in Standard at
  $19.55/month when Glacier IR would cost $1.13/month for the same
  data. Three-dimension optimization drops monthly spend ~62%.
RECOMMENDATION:
  Current: 1 org trail + 12 member trails + All-Buckets data events + Standard storage
  Proposed: 1 org trail only + 3-bucket curated data events + Glacier IR lifecycle
  Dimensions changed: consolidation (Step 1) + data_events (Step 2) + lifecycle (Step 3)
  Dimensions checked: consolidation → (remove 12 member)  data_events → (curate All-Buckets)
    lifecycle → (no policy)  lake ✓ (not configured)  logs ✓ (S3-only)
    kms_sns_insights → (consolidate CMKs)  athena ✓ (partition projection in place)
  Confidence: HIGH — org trail RUNNING multi-region confirmed; S3 access
    logs identify low-value buckets; storage math is deterministic.
ESTIMATED_SAVINGS:
  Current monthly: $1,847.32
    Consolidation overhead: $160.09 (from worked example)
    Data events: 142,500,000 / 100,000 × $0.10 = $142.50
    S3 storage: 850 GB × $0.023 = $19.55
    Athena scans: $1,500 (estimated)
    Other (KMS, SNS, base CloudTrail): $25.18
  Projected monthly: $703.42
    Consolidation overhead: $14.51 (org trail only)
    Data events: 24,700,000 / 100,000 × $0.10 = $24.70
    S3 storage: $3.78 (Glacier IR lifecycle)
    Athena scans: $640 (partition projection reduces ~57%)
    Other: $20.43
  Monthly saving: $1,143.90
    ($1,847.32 − $703.42 = $1,143.90 ✓)
  Annual saving: $13,726.80
MIGRATION_STEPS:
  1. Verify org trail covers all member accounts (24h lookup-events test):
     for acct in 222222222222 333333333333 ... 131313131313; do
       aws cloudtrail lookup-events --start-time $(date -u -d '-24 hours' +%FT%TZ) \
         --end-time $(date -u +%FT%TZ) \
         --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole \
         --query 'Events[?userIdentity.sessionContext.sessionIssuer.accountId==`'$acct'`]'
     done
  2. Snapshot member trail configurations:
     aws cloudtrail describe-trails > member-trail-snapshot.json
  3. Delete member trails in batches of 5:
     aws cloudtrail delete-trail --name member-trail-acct-2
     # ... through member-trail-acct-13
  4. Snapshot current event selectors, then apply curated S3 selectors:
     aws cloudtrail get-event-selectors --trail-name aws-organizational-trail-primary \
       > event-selectors-backup.json
     aws cloudtrail put-event-selectors \
       --trail-name aws-organizational-trail-primary \
       --advanced-event-selectors file://curated-selectors.json
  5. Apply S3 lifecycle to the log bucket:
     aws s3api put-bucket-lifecycle-configuration \
       --bucket org-cloudtrail-logs-us-east-1 \
       --lifecycle-configuration file://cloudtrail-lifecycle.json
  6. After 7 days, re-query Cost Explorer to confirm savings landed:
     aws ce get-cost-and-usage \
       --time-period Start=$(date -d '-7 days' +%F),End=$(date +%F) \
       --granularity DAILY --metrics BlendedCost \
       --filter '{"Dimensions":{"Key":"SERVICE","Values":["AWS CloudTrail"]}}'
CONFIRM: Before executing, emit and await:
  "CONFIRM: About to (1) delete 12 member trails, (2) curate S3 data events
   to 3 high-value buckets, (3) apply Glacier IR lifecycle to
   org-cloudtrail-logs-us-east-1. Monthly saving $1,143.90 (62%).
   Proceed? (yes/no)"
  Do NOT run any CLI until the operator confirms.
```

## What the skill caught that a generic assistant misses

1. **Member trails duplicate org-trail events 1:1.** A generic
   assistant says "you have a lot of trails." The skill quantifies the
   duplication (12 × 1.4M files = 16.8M duplicate files/month) and the
   exact per-trail overhead (KMS, SNS, PUT fees = $13.34/trail/month).

2. **Data event curation by audit value, not just by volume.** The
   skill classifies buckets by audit value (financial/PII/transaction
   = HIGH; CDN/ELB/CloudTrail-logs = LOW), not just by event count.
   A generic assistant says "remove some buckets" without the audit-
   value classification.

3. **Lifecycle math is deterministic.** The skill computes the steady-
   state cost across all four storage classes (Standard, Intelligent-
   Tiering, Glacier IR, Deep Archive) and shows the 81% storage
   reduction. A generic assistant says "add a lifecycle policy" without
   the dollar math.

4. **Snapshot before delete.** The skill mandates `describe-trails`
   output saved as a rollback document before any deletion. A generic
   assistant goes straight to `delete-trail` with no safety net.

5. **Verification sequence post-change.** The skill specifies a 24-hour
   `lookup-events` test (org-trail coverage), a 7-day Cost Explorer
   re-query (savings landed), and a 30-day S3 storage metrics check
   (lifecycle transitions). A generic assistant never specifies
   verification cadence.

6. **Three dimensions stacked.** The skill stacks consolidation (Step
   1) + data-event curation (Step 2) + lifecycle (Step 3) into a
   single recommendation. A generic assistant addresses one at a time,
   leaving 50%+ of the savings on the table.

## Slash-command invocation

```
/aws:optimize-cloudtrail-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit our CloudTrail spend ahead of the FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: cloudtrail-cost-optimizer]` and hands
off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new configuration:

```bash
# Confirm member trails are deleted
aws cloudtrail describe-trails --query 'trailList[*].Name' --output table

# Confirm event selectors were applied
aws cloudtrail get-event-selectors --trail-name aws-organizational-trail-primary

# Confirm lifecycle policy
aws s3api get-bucket-lifecycle-configuration \
  --bucket org-cloudtrail-logs-us-east-1

# 7-day Cost Explorer check
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '-7 days' +%F),End=$(date +%F) \
  --granularity DAILY --metrics BlendedCost \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["AWS CloudTrail"]}}'
```

If CloudTrail cost does not drop as projected, investigate:
- Member trails may have been recreated by automation (CloudFormation
  drift, Terraform re-apply).
- Event selectors may not have taken effect (verify `get-event-selectors`
  output matches the curated list).
- Lifecycle policy may not have been applied (verify S3 metrics show
  Glacier IR object count > 0 after 90 days).

Roll back by re-applying the snapshot:

```bash
aws cloudtrail create-trail --name member-trail-acct-2 ...  # from snapshot
aws cloudtrail put-event-selectors --trail-name <trail> \
  --event-selectors file://event-selectors-backup.json
```

## Fleet-wide extension

For an AWS Organization with N member accounts:

1. Use AWS Organizations `list-accounts` to enumerate member accounts.
2. Assume a role in each member account; run `describe-trails`.
3. Aggregate trail inventory into a single optimization pass.
4. Group findings by dimension (consolidation, data events, lifecycle).
5. Apply changes in batches of 5 member accounts, verifying org-trail
   coverage after each batch.
6. After all batches, re-query Cost Explorer at 30 days for the
   cumulative savings report.
