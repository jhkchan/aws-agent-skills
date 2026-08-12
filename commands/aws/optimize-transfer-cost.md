---
description: Optimise AWS Transfer Family cost through server endpoint type selection (PUBLIC vs VPC vs VPC_ENDPOINT), idle server detection and consolidation, concurrency right-sizing, protocol selection, user session duration analysis, managed workflow (Step Functions) cost reduction, CloudWatch Logs volume tuning, and custom identity provider Lambda cost optimization with monthly savings estimates.
nl_triggers:
  - "optimise Transfer Family cost"
  - "Transfer Family spend too high"
  - "SFTP server cost"
  - "Transfer Family idle server"
  - "Transfer Family endpoint type"
  - "Transfer Family PUBLIC vs VPC"
  - "Transfer Family VPC_ENDPOINT"
  - "Transfer Family concurrency"
  - "Transfer Family session duration"
  - "Transfer Family managed workflow"
  - "Transfer Family Step Functions cost"
  - "Transfer Family CloudWatch Logs"
  - "SFTP logging cost"
  - "Transfer Family custom identity provider"
  - "Transfer Family Lambda IdP cost"
  - "Transfer Family sticky session"
  - "Transfer Family data transfer cost"
  - "SFTP FinOps"
  - "reduce Transfer Family bill"
  - "storage cost review"
  - "Transfer Family server consolidation"
routes_to: transfer-cost-optimizer
---

# /aws:optimize-transfer-cost

Activate the `transfer-cost-optimizer` skill and optimize an AWS
Transfer Family server's cost across eight dimensions: endpoint type,
idle server detection, protocol selection, concurrency right-sizing,
session duration, managed workflow cost, CloudWatch Logs volume, and
custom identity provider cost.

## What it does

Reads a server's configuration, CloudWatch metrics (ConcurrentSessions,
FilesIn, FilesOut, UserSessionsStarted), managed workflow definitions,
CloudWatch Logs volume, Cost Explorer Transfer spend, and custom IdP
Lambda invocation data, then applies the ordered optimization logic:

1. **Pre-flight** — data sufficiency gate. If Cost Explorer Transfer
   line items are absent, emits NEED_MORE_INFO. If the server does not
   exist, emits BLOCKED.
2. **Endpoint type** — PUBLIC is cheapest (no VPC/NAT overhead). VPC
   adds NAT Gateway data processing; VPC_ENDPOINT adds per-hour VPC
   endpoint fees. Migrate to PUBLIC wherever the network topology
   permits.
3. **Idle server detection** — servers with near-zero
   ConcurrentSessions still charge per hour. Detect and consolidate or
   decommission.
4. **Protocol selection** — SFTP is the cost-efficient baseline. FTPS
   adds negligible TLS overhead. FTP requires VPC (higher cost).
5. **Concurrency right-sizing** — consolidate multiple underutilized
   servers onto fewer servers when the combined peak fits within a
   single server's concurrency limit.
6. **Session duration analysis** — long sessions with few file
   transfers waste concurrency slots. Investigate idle session hold
   patterns.
7. **Managed workflow cost** — Step Functions charges per state
   transition per file. Simplify multi-step workflows; batch files
   before triggering.
8. **CloudWatch Logs volume** — SFTP logging generates one event per
   file transfer. Reduce log level (INFO → WARNING) and set retention
   to control ingest cost.
9. **Custom identity provider** — Lambda + API Gateway per-auth cost
   compounds at high session-start rates. Enable auth caching or
   switch to Lambda Function URL.
10. **Impact estimation** — monthly + annual savings, assumptions
    documented.
11. **Verdict** — FURTHER_OPTIMIZATION_AVAILABLE (any dimension has a
    recommendation), OPTIMIZED (all dimensions verified), or
    NEED_MORE_INFO.

Emits a deterministic optimization block per server:

```text
TARGET: <server-id>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <endpoint type>, <concurrency>, <servers>, <workflow>, <logs volume>
  Proposed: <endpoint type>, <concurrency>, <servers>, <workflow>, <logs volume>
  Dimensions changed: <endpoint | idle | protocol | concurrency | session | workflow | logs | idp>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a Transfer Family server's configuration and ask any of:

- "optimise this Transfer Family server's cost"
- "should I migrate from VPC to PUBLIC endpoint?"
- "is this SFTP server idle?"
- "should I consolidate these Transfer servers?"
- "why is our Transfer Family bill so high?"
- "is the managed workflow worth the cost?"
- "how do I reduce SFTP logging cost?"
- "is the custom IdP Lambda costing too much?"
- "Transfer Family fleet cost optimization review"

A bare server reference + any optimization verb ("optimize Transfer
spend", "storage cost review") also routes here via the orchestrator.

## Inputs

- Server metadata: ServerId, EndpointType, Protocols, region,
  IdentityProviderType, LoggingRole.
- CloudWatch metrics (last 14-30 days):
  - `ConcurrentSessions` (Average, p95, p99)
  - `FilesIn`, `FilesOut` (Sum)
  - `BytesIn`, `BytesOut` (Sum)
  - `UserSessionsStarted` (Sum)
- Optional: managed workflow definitions (steps, execution count).
- Optional: CloudWatch Logs volume for the Transfer log group.
- Optional: custom IdP Lambda invocation count and API Gateway request
  count.
- Optional: Cost Explorer Transfer spend (last 14-30 days).
- Optional: workload context (client connectivity, compliance
  requirements, partner patterns).

## Outputs

- One optimization block per server (or per deployment for
  consolidation).
- Confidence level with rationale (HIGH requires server config citation
  + Cost Explorer cross-check).
- Estimated monthly and annual savings, broken down by dimension.
- Specific migration steps with CLI commands (create-server, create-
  user, update-server, delete-server, create-workflow).
- NAT Gateway / VPC endpoint cost impact surfaced alongside Transfer
  cost (endpoint migration savings extend beyond the Transfer line
  item).
- Staged cutover with user migration and rollback plan.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for Transfer Family file-transfer cost).
- `/aws:deploy-transfer-family` for deploying new Transfer Family
  servers (not cost optimization).
- `/aws:deploy-transfer-family-workflow` for deploying managed workflows
  (not cost optimization).
- `/aws:operate-s3-transfer-acceleration` for S3 Transfer Acceleration
  (large-object upload acceleration, not SFTP server cost).
- `/aws:optimize-s3-lifecycle` for S3 storage cost optimization (the
  underlying storage cost for Transfer Family home directories).
