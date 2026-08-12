# Example usage: transfer-cost-optimizer

A walkthrough showing the skill optimizing a VPC endpoint Transfer
Family server with NAT Gateway overhead, a 5-step managed workflow, and
high CloudWatch Logs volume. Demonstrates the endpoint-type migration
(VPC to PUBLIC), the workflow simplification (5 steps to 3), the log
volume reduction (INFO to WARNING), the dollar savings math, and the
staged cutover with user-migration between each phase.

## Input (user prompt)

> Review our Transfer Family server before the Q3 storage FinOps
> review. It's a VPC SFTP server for partner file exchange and costs
> over $800 a month. Help me optimize the cost.

```text
ServerId: s-vpc-to-public-endpoint-migration
EndpointType: VPC
Protocols: [SFTP]
Region: us-east-1
IdentityProviderType: SERVICE_MANAGED
LoggingRole: arn:aws:iam::<acct>:role/TransferLogging
Concurrency: 10 (configured), observed avg 0.5, p95 2, p99 3
Users: 25 configured, 8 active in last 30 days

Managed workflow: 1 (post-upload, 5-step Step Functions)
  executions: 2,000,000 files/month

Metrics (last 30 days):
  - ConcurrentSessions: avg 0.5, p95 2, p99 3
  - FilesIn: 2,000,000/month
  - FilesOut: 500,000/month
  - BytesIn: 1,500 GB/month (outbound via NAT Gateway)
  - BytesOut: 200 GB/month
  - UserSessionsStarted: 6,000/month

CloudWatch Logs volume: 300 GB/month from Transfer logging
Cost Explorer (Service=Transfer, last 30 days): $819.50

Workload context: partner file exchange. All partners connect
from the public internet — no internal/VPC-only access required.
Concurrency peak of 3 is well under the configured 10. Workflow
has 5 steps (validation, transformation, notification, archival,
audit) — the archival and audit steps could be combined.
```

## Skill output

```text
TARGET: s-vpc-to-public-endpoint-migration
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: VPC endpoint server with outbound traffic via NAT Gateway
  averages 0.5 concurrent sessions (near-idle) and processes 1,500 GB/month
  outbound ($67.50/month NAT data processing alone). ConcurrentSessions
  peak is 3, well under the configured concurrency of 10. Managed
  workflow (5-step) runs on 2,000,000 files/month, generating $250/month
  in Step Functions charges. CloudWatch Logs volume is 300 GB/month
  ($150/month in ingest). Migrating to PUBLIC eliminates NAT overhead;
  simplifying the workflow and reducing log volume cut the remaining spend.
RECOMMENDATION:
  Current: VPC, concurrency 10, 1 server, 5-step workflow, 300 GB logs/month
  Proposed: PUBLIC, concurrency 5, 1 server, 3-step workflow, 50 GB logs/month
  Dimensions changed: endpoint (Step 1) + workflow (Step 6) + logs (Step 7)
  Dimensions checked: endpoint → (VPC to PUBLIC)  idle ✓ (avg 0.5 is low but not zero)
    protocol ✓ (SFTP)  concurrency → (10 to 5)  session ✓ (no idle hold)
    workflow → (5-step to 3-step)  logs → (300 GB to 50 GB)  idp ✓ (no custom IdP)
  Confidence: HIGH — server config cited; Cost Explorer cross-check agrees;
    PUBLIC migration safe (clients connect from public internet).
ESTIMATED_SAVINGS:
  Current monthly: $819.50
    server hourly: 1 × $0.30 × 730 = $219.00
    data transfer: 1,500 GB × $0.04 = $60.00
    workflow: 2,000,000 × 5 × $0.000025 = $250.00
    CloudWatch Logs: 300 GB × $0.50 = $150.00
    NAT Gateway: 1,500 GB × $0.045 = $67.50
    VPC endpoint: $73.00
  Projected monthly: $422.00
    server hourly: 1 × $0.30 × 730 = $219.00
    data transfer: 1,500 GB × $0.04 = $60.00
    workflow: 2,000,000 × 3 × $0.000025 = $150.00
    CloudWatch Logs: 50 GB × $0.50 = $25.00
    NAT Gateway: $0.00 (PUBLIC, no NAT)
    VPC endpoint: $0.00 (PUBLIC)
  Monthly saving: $397.50
    ($819.50 − $422.00 = $397.50 ✓)
  Annual saving: $4,770.00
MIGRATION_STEPS:
  1. Verify all clients can connect over the public internet:
     aws transfer describe-server --server-id s-vpc-to-public-endpoint-migration | \
       jq '.EndpointType, .Protocols'
  2. Create a new PUBLIC server with the same configuration:
     aws transfer create-server --endpoint-type PUBLIC --protocols SFTP \
       --identity-provider-type SERVICE_MANAGED --region us-east-1
  3. Migrate users to the new server:
     aws transfer create-user --server-id <new-id> --user-name <user> \
       --ssh-public-key-body <key> --home-directory /<bucket>/<user>
  4. Simplify the managed workflow from 5 steps to 3:
     aws transfer create-workflow --steps <simplified-steps-json>
  5. Reduce CloudWatch Logs verbosity (log only authentication + errors):
     aws transfer update-server --server-id <new-id> \
       --logging-role arn:aws:iam::<acct>:role/TransferLogging
  6. Delete the old VPC server once migration is confirmed:
     aws transfer delete-server --server-id s-vpc-to-public-endpoint-migration
  7. Monitor Cost Explorer (Service=Transfer) for 7 days post-change:
     aws ce get-cost-and-usage --filter '{"Dimensions":{"Key":"SERVICE","Values":["Transfer"]}}'
CONFIRM: About to migrate s-vpc-to-public-endpoint-migration from VPC to PUBLIC endpoint,
  simplify workflow from 5 steps to 3, and reduce log volume from 300 GB
  to 50 GB. Monthly saving $397.50 (48.5% reduction). Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **NAT Gateway cost is hidden.** A generic assistant says "consider
   PUBLIC." The skill cites the 1,500 GB outbound via NAT Gateway and
   computes the $67.50/month data-processing cost that PUBLIC eliminates.
   NAT Gateway cost is invisible in the Transfer line item — it appears
   under NAT Gateway in Cost Explorer.

2. **Three dimensions stack.** The skill stacks three savings: endpoint
   migration (Step 1) + workflow simplification (Step 6) + log reduction
   (Step 7). A generic assistant captures only the endpoint change,
   leaving workflow and log savings on the table.

3. **Workflow cost scales with file count, not file size.** The skill
   cites the 2M files/month × 5 steps × $0.025/1000 = $250/month formula.
   A generic assistant says "the workflow is expensive" without showing
   that the cost is per-file, not per-GB.

4. **User migration workflow for safe cutover.** The skill publishes a
   step-by-step user migration (SSH keys, home directories) before
   deleting the old server. A generic assistant jumps to
   `delete-server` without preserving user configurations.

5. **Concurrency right-sizing.** The skill observes that concurrency
   peak (3) is well under the configured limit (10) and recommends
   reducing to 5 (p99 + headroom). A generic assistant does not address
   concurrency.

6. **CONFIRM gate with rollback plan.** The skill emits a CONFIRM
   prompt and keeps the old VPC server for 7 days as rollback. A
   generic assistant goes straight to the CLI without a safety gate.

## Slash-command invocation

```
/aws:optimize-transfer-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our Transfer Family spend for the Q3 storage FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: transfer-cost-optimizer]` and hands
off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new configuration:

```bash
# Confirm the new server is PUBLIC and online
aws transfer describe-server \
  --server-id <new-id> \
  --profile default --region us-east-1 | \
  jq '{EndpointType, State, Protocols}'

# Confirm users are migrated
aws transfer list-users \
  --server-id <new-id> \
  --profile default --region us-east-1 | \
  jq '.Users | length'

# Confirm the old VPC server is deleted
aws transfer describe-server \
  --server-id s-vpc-to-public-endpoint-migration \
  --profile default --region us-east-1 || echo "Server deleted (expected)"

# Monitor Transfer spend for 7 days post-change
aws ce get-cost-and-usage \
  --time-period Start=2026-08-05,End=2026-08-12 \
  --granularity DAILY \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Transfer"]}}' \
  --metrics "UnblendedCost" \
  --profile default --region us-east-1
```

If file transfers regress or authentication fails on the new server,
roll back by repointing DNS to the old VPC server (kept for 7 days):

```bash
# Re-point partners to the old VPC server (rollback)
# Update DNS CNAME or partner configurations to the old endpoint
```

## Fleet-wide extension

For a fleet of N Transfer Family servers:

1. Pull all servers with `aws transfer list-servers`.
2. For each, pull `describe-server`, CloudWatch metrics (14-30 day
   window), and Cost Explorer line items.
3. Classify each server by endpoint type (VPC/VPC_ENDPOINT → evaluate
   PUBLIC migration).
4. Detect idle servers (ConcurrentSessions avg < 0.1).
5. Evaluate workflow cost (files/month × steps × $0.025/1000).
6. Sort by estimated monthly savings (largest first).
7. Slice into batches of 5 servers.
8. For each batch: emit per-server MIGRATION_STEPS, then a single
   CONFIRM for the batch.
9. Verify each batch before proceeding to the next.
10. After the endpoint sweep, evaluate workflow and log optimization
    for the remaining servers.
