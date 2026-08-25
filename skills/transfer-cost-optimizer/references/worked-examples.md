# Worked Examples — Transfer Family Cost Optimizer

Full worked examples covering each optimization dimension. Each example
shows the input, the decision walkthrough, and the emitted output block.

## Example 1: VPC to PUBLIC endpoint migration + workflow + logs

**Input:** VPC server with NAT Gateway overhead; near-idle sessions;
5-step workflow on 2M files/month; 300 GB CloudWatch Logs/month.

**Decision walkthrough:**
1. Step 1 (endpoint): VPC with all clients on public internet → migrate
   to PUBLIC. Eliminates NAT Gateway ($67.50/month) + VPC endpoint
   hourly ($73/month).
2. Step 6 (workflow): 5-step workflow, archival+audit combinable →
   simplify to 3 steps.
3. Step 7 (logs): 300 GB at INFO → reduce to ~50 GB at WARNING.
4. Steps 2, 3, 4, 5, 8: No finding (sessions are low but non-zero;
   protocol is SFTP; concurrency is adequate; session duration is
   normal; no custom IdP).

**Emitted block:**
```text
TARGET: s-vpc-to-public-endpoint-migration
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: VPC endpoint server with outbound traffic via NAT Gateway
  processes 1,500 GB/month outbound ($67.50/month NAT data processing
  alone). All clients connect from the public internet — PUBLIC is
  viable. 5-step managed workflow on 2M files/month generates $250/month
  in Step Functions charges; simplifiable to 3 steps ($150/month).
  CloudWatch Logs at 300 GB/month ($150/month ingest); reducible to
  ~50 GB ($25/month) at WARNING level.
RECOMMENDATION:
  Current: VPC, concurrency 10, 1 server, 5-step workflow, 300 GB logs/month
  Proposed: PUBLIC, concurrency 5, 1 server, 3-step workflow, 50 GB logs/month
  Dimensions changed: endpoint (Step 1) + workflow (Step 6) + logs (Step 7)
  Dimensions checked: endpoint → (VPC to PUBLIC)  idle ✓ (avg 0.5 is low but not zero)
    protocol ✓ (SFTP)  concurrency → (10 to 5)  session ✓ (no idle hold)
    workflow → (5-step to 3-step)  logs → (300 GB to 50 GB)  idp ✓ (service-managed)
  Confidence: HIGH — server config cited; Cost Explorer cross-check agrees
ESTIMATED_SAVINGS:
  Current monthly: $819.50
    server hourly: $219.00
    data transfer: $60.00
    workflow: $250.00
    CloudWatch Logs: $150.00
    NAT Gateway: $67.50
    VPC endpoint: $73.00
  Projected monthly: $422.00
    server hourly: $219.00
    data transfer: $60.00
    workflow: $150.00
    CloudWatch Logs: $25.00
    NAT Gateway: $0.00 (PUBLIC)
    VPC endpoint: $0.00 (PUBLIC)
  Monthly saving: $397.50
  Annual saving: $4,770.00
MIGRATION_STEPS:
  1. Verify all clients can connect over the public internet
  2. Create a new PUBLIC server with the same configuration
  3. Migrate users to the new server (SSH keys, home directories)
  4. Simplify the managed workflow from 5 steps to 3
  5. Reduce CloudWatch Logs verbosity to WARNING
  6. Delete the old VPC server once migration is confirmed
  7. Monitor Cost Explorer for 7 days post-change
CONFIRM: About to migrate s-vpc-to-public-endpoint-migration from VPC
  to PUBLIC, simplify workflow, and reduce logs. Monthly saving $397.50
  (48.5%). Proceed? (yes/no)
```

## Example 2: Idle server consolidation

**Input:** 3 PUBLIC servers, combined peak 9 sessions vs per-server
concurrency limit of 10. All SERVICE_MANAGED identity, no workflows.

**Decision walkthrough:**
1. Step 4 (concurrency/server count): Combined peak (9) fits within a
   single server's limit (10). Consolidate 3 → 1.

**Emitted block (abbreviated):**
```text
TARGET: transfer-idle-server-consolidation
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Three PUBLIC servers with a combined peak of 9 concurrent
  sessions fit within a single server's concurrency limit of 10.
  Consolidating 3 → 1 eliminates 2 servers × $219/month = $438/month.
  All servers use SERVICE_MANAGED identity (no IdP migration needed).
RECOMMENDATION:
  Current: 3 PUBLIC servers, concurrency 10 each, no workflow
  Proposed: 1 PUBLIC server, concurrency 10, no workflow
  Dimensions changed: concurrency/server-count (Step 4)
  Dimensions checked: endpoint ✓ (all PUBLIC)  idle ✓ (low but non-zero)
    protocol ✓ (SFTP)  concurrency → (3 servers to 1)  session ✓ (normal)
    workflow ✓ (none)  logs ✓ (80 GB reasonable)  idp ✓ (service-managed)
  Confidence: HIGH — combined peak cited; concurrency limit cited
ESTIMATED_SAVINGS:
  Current monthly: $727.00
    server hourly: 3 × $219 = $657.00
    data transfer: 700 GB × $0.04 = $28.00
    CloudWatch Logs: 80 GB × $0.50 = $40.00
    other: $2.00
  Projected monthly: $289.00
    server hourly: 1 × $219 = $219.00
    data transfer: 700 GB × $0.04 = $28.00
    CloudWatch Logs: 80 GB × $0.50 = $40.00
    other: $2.00
  Monthly saving: $438.00
  Annual saving: $5,256.00
MIGRATION_STEPS:
  1. Select s-partner-exchange-a as the consolidation target
  2. Migrate users from s-partner-exchange-b and s-internal-reports:
     aws transfer create-user --server-id s-partner-exchange-a ...
  3. Update DNS/partner configurations to point to the consolidated server
  4. Monitor for 7 days to confirm no session rejection at peak
  5. Delete the two decommissioned servers:
     aws transfer delete-server --server-id s-partner-exchange-b
     aws transfer delete-server --server-id s-internal-reports
CONFIRM: About to consolidate 3 Transfer servers to 1. Monthly saving
  $438.00 (60% reduction). Proceed? (yes/no)
```

## Example 3: Workflow simplification + log reduction

**Input:** PUBLIC server with 7-step workflow on 5M small files/month;
500 GB CloudWatch Logs at INFO level; audit compliance requires only
authentication + error logging.

**Decision walkthrough:**
1. Step 6 (workflow): 7 steps, archival+audit combinable, virus-scan
   +validation parallelizable → simplify to 5 effective steps (combine
   archival+audit; parallel branch counts as transitions, but the
   combine reduces total by 2).
2. Step 7 (logs): 500 GB at INFO, audit only needs auth+errors → reduce
   to ~100 GB at WARNING (80% reduction).

**Emitted block (abbreviated):**
```text
TARGET: s-workflow-and-log-cost-reduction
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: 7-step managed workflow on 5M files/month generates $875/month
  in Step Functions charges (5M × 7 × $0.025/1000). Combining archival
  +audit and running virus-scan+validation in parallel reduces to 5
  effective steps ($625/month). CloudWatch Logs at 500 GB/month
  ($250/month ingest); reducing to WARNING level cuts volume to ~100 GB
  ($50/month). Audit compliance requires only authentication + error
  logging per the compliance officer's sign-off.
RECOMMENDATION:
  Current: PUBLIC, 7-step workflow, 500 GB logs/month (INFO)
  Proposed: PUBLIC, 5-step workflow, 100 GB logs/month (WARNING)
  Dimensions changed: workflow (Step 6) + logs (Step 7)
  Dimensions checked: endpoint ✓ (already PUBLIC)  idle ✓ (active)
    protocol ✓ (SFTP)  concurrency ✓ (right-sized)  session ✓ (normal)
    workflow → (7-step to 5-step)  logs → (500 GB to 100 GB)  idp ✓ (service-managed)
  Confidence: HIGH — workflow step audit cited; compliance sign-off cited
ESTIMATED_SAVINGS:
  Current monthly: $1,768.50
    server hourly: $219.00
    data transfer: 250 GB × $0.04 = $10.00
    workflow: 5M × 7 × $0.025/1000 = $875.00
    CloudWatch Logs: 500 GB × $0.50 = $250.00
    S3 storage: $414.50 (5M files × 50 KB × S3 rates)
  Projected monthly: $1,068.50
    server hourly: $219.00
    data transfer: $10.00
    workflow: 5M × 5 × $0.025/1000 = $625.00
    CloudWatch Logs: 100 GB × $0.50 = $50.00
    S3 storage: $164.50
  Monthly saving: $700.00
  Annual saving: $8,400.00
MIGRATION_STEPS:
  1. Audit each workflow step for combinability
  2. Create the simplified workflow (combine archival+audit, parallel validation+virus-scan):
     aws transfer create-workflow --steps <simplified-steps-json>
  3. Attach the new workflow to the server
  4. Reduce CloudWatch Logs level to WARNING (log config update)
  5. Monitor for 7 days to confirm workflow + logging changes
CONFIRM: About to simplify workflow from 7 to 5 steps and reduce log
  level from INFO to WARNING. Monthly saving $700.00 (40%). Proceed?
  (yes/no)
```

## Example 4: Already-optimized (OPTIMIZED)

**Input:** PUBLIC endpoint; concurrency right-sized; no workflow;
logs at WARNING with 7-day retention + S3 archive; service-managed
IdP.

**Decision walkthrough:** All eight dimensions pass. No savings-
bearing recommendation.

**Emitted block:**
```text
TARGET: s-already-optimized-transfer
VERDICT: OPTIMIZED
REASON: All dimensions verified. PUBLIC endpoint (cheapest); concurrency
  right-sized (p99 7 vs limit 10); no managed workflow; logs at WARNING
  with 7-day retention + S3 archive; service-managed identity (no Lambda
  IdP cost). Monthly spend ($237) is proportional to usage.
RECOMMENDATION:
  Current: PUBLIC, concurrency 10, 1 server, no workflow, 20 GB logs/month
  Proposed: no change
  Dimensions changed: none
  Dimensions checked: endpoint ✓ (PUBLIC)  idle ✓ (active)
    protocol ✓ (SFTP)  concurrency ✓ (right-sized)  session ✓ (normal)
    workflow ✓ (none)  logs ✓ (controlled)  idp ✓ (service-managed)
  Confidence: HIGH — all dimensions verified
ESTIMATED_SAVINGS:
  Current monthly: $237.00
  Projected monthly: $237.00
  Monthly saving: $0.00
  Annual saving: $0.00
MIGRATION_STEPS:
  1. No action required. Continue monitoring Cost Explorer monthly.
CONFIRM: N/A — no state-changing operation proposed.
```

## Example 5: Custom IdP + session optimization

**Input:** PUBLIC server with custom API_GATEWAY Lambda IdP; 80,000
session starts/month with no auth caching; 45-min avg session with 0.6
files per session.

**Decision walkthrough:**
1. Step 8 (custom IdP): 80,000 Lambda invocations/month with no caching
   → enable auth caching (short-lived cache for repeated logins).
   Estimated 60-80% invocation reduction for partner-portal pattern
   (repeated logins within minutes).
2. Step 5 (session duration): 45-min avg with 0.6 files per session →
   investigate idle session hold. Partners may be keeping sessions
   open while polling for files.

**Emitted block (abbreviated):**
```text
TARGET: s-custom-idp-and-session-optimization
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Custom API_GATEWAY Lambda IdP processes 80,000 session
  starts/month with no auth caching. Enabling short-lived caching
  (5-10 min TTL) projects 60-80% invocation reduction for the partner-
  portal pattern (repeated logins within minutes). Average session
  duration is 45 min with 0.6 files per session — partners are keeping
  sessions open while polling, tying up concurrency slots.
RECOMMENDATION:
  Current: PUBLIC, API_GATEWAY IdP, no caching, 80K sessions/month
  Proposed: PUBLIC, API_GATEWAY IdP with caching, 32K sessions/month
  Dimensions changed: idp (Step 8) + session (Step 5)
  Dimensions checked: endpoint ✓ (already PUBLIC)  idle ✓ (active)
    protocol ✓ (SFTP)  concurrency ✓ (right-sized)
    session → (45 min avg, investigate polling pattern)
    workflow ✓ (none)  logs ✓ (30 GB reasonable)
    idp → (no caching → enable caching)
  Confidence: MEDIUM — caching reduction is estimated; session pattern
    requires partner-side investigation
ESTIMATED_SAVINGS:
  Current monthly: $312.00
    server hourly: $219.00
    data transfer: 40 GB × $0.04 = $1.60
    Lambda IdP: 80K × ($0.0000002 + 250ms compute) = ~$8.33
    API Gateway: 80K × $3/M = $0.24
    CloudWatch Logs: 30 GB × $0.50 = $15.00
    other: $67.83 (S3 storage, indirect)
  Projected monthly: $298.00
    server hourly: $219.00
    data transfer: $1.60
    Lambda IdP: 32K × ($0.0000002 + 250ms compute) = ~$3.33
    API Gateway: 32K × $3/M = $0.10
    CloudWatch Logs: $15.00
    other: $58.97
  Monthly saving: $14.00
  Annual saving: $168.00
  Note: Direct IdP saving is modest ($5.14/month). The larger value is
    reducing session-start load on the IdP Lambda (cold-start reduction,
    API Gateway throttling headroom) and surfacing the polling pattern
    for partner-side optimization.
MIGRATION_STEPS:
  1. Update the IdP Lambda to cache authentication results (5-10 min TTL):
     # Add in-memory cache or ElastiCache for cross-invocation caching
  2. Investigate the 45-min session pattern:
     aws cloudwatch get-metric-statistics --namespace AWS/Transfer \
       --metric-name UserSessionsStarted \
       --dimensions Name=ServerId,Value=<id> \
       --start-time $(date -d '-30 days' +%FT%TZ) --period 3600
  3. Audit partner scripts for session-reuse vs re-connect patterns
  4. Monitor Lambda invocations for 7 days post-caching
CONFIRM: About to enable auth caching on the custom IdP Lambda and
  investigate the session polling pattern. Direct monthly saving $14.00
  (IdP only); operational improvement in cold-start + throttling
  headroom. Proceed? (yes/no)
```

## End-to-end walkthrough — VPC-to-PUBLIC + workflow + logs

This walkthrough shows all three dimensions applied in sequence on the
same server, with intermediate verification between each step.

### Phase 1: Endpoint migration (highest savings)

1. Verify all clients can connect over the public internet (confirm no
   internal-only partners).
2. Create a new PUBLIC server with the same SFTP/protocol configuration.
3. Migrate users (SSH keys, home directory mappings) to the new server.
4. Test connectivity from a sample partner.
5. Cut over DNS/partner configurations to the new server endpoint.

### Phase 2: Workflow simplification

1. Audit each workflow step for combinability and parallelization.
2. Create the simplified workflow.
3. Attach the new workflow to the PUBLIC server.
4. Test on a sample file upload; verify all transformations execute.
5. Monitor for 24 hours; confirm no step failures.

### Phase 3: Log reduction

1. Confirm audit compliance requirements (authentication + errors only).
2. Update the logging configuration to WARNING level.
3. Set log retention to 7-30 days; configure S3 export for long-term.
4. Monitor CloudWatch Logs volume for 7 days; confirm reduction.

If at any phase file transfers or authentication regresses, roll back:
- Phase 1 rollback: repoint DNS to the VPC server (kept for 7 days).
- Phase 2 rollback: reattach the original workflow.
- Phase 3 rollback: revert log level to INFO.

## Extended from SKILL.md

## Step 1 — VPC-to-PUBLIC savings math

**VPC-to-PUBLIC savings math:**
```
vpc_monthly_cost = server_hourly × 730 + NAT_GB × $0.045 + VPC_endpoint_hourly
public_monthly_cost = server_hourly × 730
saving = vpc_monthly_cost − public_monthly_cost
```

Example: VPC server with 500 GB/month outbound via NAT Gateway:
- VPC: $219 (server) + $22.50 (NAT data processing) + $7.30 (VPC endpoint) = $248.80/month
- PUBLIC: $219 (server only) = $219/month
- Saving: $29.80/month per server (13% reduction)

## Step 4 — Consolidation math

**Consolidation math:**
```
current_cost = N_servers × server_hourly × 730
consolidated_cost = M_servers × server_hourly × 730    (where M < N)
saving = (N − M) × server_hourly × 730
```

Example: 3 servers at $0.30/hour, each averaging 2 concurrent sessions
(configured limit 10 each = 30 total). Combined peak is 6 sessions.
Consolidate to 1 server with concurrency limit 10:
- Before: 3 × $0.30 × 730 = $657/month
- After: 1 × $0.30 × 730 = $219/month
- Saving: $438/month (67% reduction)

## Step 6 — Workflow cost example

Example: 2,000,000 files/month, 5-step workflow:
- 2,000,000 × 5 × $0.000025 = $250/month in Step Functions charges

**Workflow optimization:**
| Signal | Recommendation |
|---|---|
| Multi-step workflow (5+ steps) on every file | Simplify the workflow; combine steps where possible |
| File count > 100,000/month AND workflow is validation-only | Move validation to S3 Event Notifications + Lambda (per-invocation, no state machine) |
| Workflow triggers on every small file | Batch files before triggering the workflow (reduce execution count) |
| Workflow has retry logic that re-executes on failure | Ensure idempotency; reduce retry count |
