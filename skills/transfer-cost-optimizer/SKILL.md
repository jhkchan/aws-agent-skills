---
name: transfer-cost-optimizer
description: 'Optimises AWS Transfer Family cost across eight dimensions: server endpoint type (PUBLIC vs VPC vs VPC_ENDPOINT — PUBLIC is cheapest with no VPC/NAT cost; VPC_ENDPOINT for internal-only; VPC for private connectivity with NAT Gateway overhead), per-hour server cost vs usage pattern (idle servers still incur the full per-hour charge — detect and stop them), protocol selection (SFTP vs FTPS vs FTP — SFTP is the baseline; FTP adds no TLS overhead but is rare in practice), concurrency vs server count (right-size concurrency limits vs spawning multiple servers), user session duration analysis (long sessions tie up concurrency slots), data transfer cost (S3 upload/download per-GB is the baseline; Transfer Family adds a per-GB fee on top), managed workflow cost (Step Functions execution per file — scales with file count not file size, so many small files are disproportionately expensive), CloudWatch Logs volume (SFTP logging to CloudWatch can dominate cost for high-volume servers), trusted host key rotation (no direct cost but affects session retry patterns), custom identity provider Lambda cost (per-authentication Lambda invocations), and sticky session configuration. Uses aws transfer describe-server, list-users, describe-user, aws cloudwatch get-metric-statistics (Transfer Family metrics), aws ce get-cost-and-usage (filter Service=Transfer), aws stepfunctions describe-state-machine (managed workflow execution count), and aws logs describe-metric-filters (CloudWatch Logs volume) to project monthly savings. Emits FURTHER_OPTIMIZATION_AVAILABLE with specific recommendation and estimated savings, OPTIMIZED, or NEED_MORE_INFO. Use when reviewing Transfer Family spend, detecting idle servers, choosing endpoint types, evaluating managed workflow cost, or a storage FinOps review.'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted Transfer Family server configs, CloudWatch metrics, and Cost Explorer Transfer line items. Live-account optimization uses aws transfer describe-server, aws transfer list-users, aws transfer describe-user, aws transfer describe-workflow (managed workflows), aws transfer list-accesses, aws cloudwatch get-metric-statistics (AWS/Transfer namespace: FilesIn, FilesOut, BytesIn, BytesOut, ConcurrentSessions, UserSessionsStarted), aws ce get-cost-and-usage (filter Service=Transfer), aws stepfunctions get-execution-history (workflow executions), aws logs describe-metric-filters (CloudWatch Logs volume), and aws lambda get-function-configuration (custom IdP Lambda). Pricing references us-east-1 published rates as of 2026; re-state regional rates from the reference matrix for other regions.
keywords:
- Transfer Family
- AWS Transfer
- SFTP
- FTPS
- FTP
- cost optimization
- server endpoint
- PUBLIC endpoint
- VPC endpoint
- VPC_ENDPOINT
- idle server
- per-hour cost
- concurrency
- session duration
- managed workflow
- Step Functions
- CloudWatch Logs
- trusted host key
- custom identity provider
- Lambda IdP
- sticky session
- data transfer
- S3 upload
- storage FinOps
tags:
- transfer-family
- storage
- cost-optimization
- finops
- sftp
- file-transfer
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Storage
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising AWS Transfer Family cost, choosing between PUBLIC vs VPC vs VPC_ENDPOINT server types, detecting and stopping idle Transfer servers, right-sizing concurrency limits vs server count, analysing user session duration, evaluating managed workflow (Step Functions) cost, reducing CloudWatch Logs volume from SFTP logging, auditing custom identity provider Lambda cost, or reviewing SFTP/FTPS endpoint spend.
  when_not_to_use: S3 storage cost optimization (use s3-lifecycle-optimizer), DataSync cost (use datasync-cost-optimizer), general VPC/NAT Gateway cost (use vpc-cost-optimizer), or Transfer Family server troubleshooting (connection errors, authentication failures — use transfer-family-troubleshooter). This skill focuses on cost-driven optimization decisions for Transfer Family spend, not on functional debugging of broken servers.
  activation_triggers:
  - optimise Transfer Family cost
  - Transfer Family spend too high
  - SFTP server cost
  - Transfer Family idle server
  - Transfer Family endpoint type
  - Transfer Family PUBLIC vs VPC
  - Transfer Family VPC_ENDPOINT
  - Transfer Family concurrency
  - Transfer Family session duration
  - Transfer Family managed workflow
  - Transfer Family Step Functions cost
  - Transfer Family CloudWatch Logs
  - SFTP logging cost
  - Transfer Family custom identity provider
  - Transfer Family Lambda IdP cost
  - Transfer Family sticky session
  - Transfer Family data transfer cost
  - SFTP FinOps
  - reduce Transfer Family bill
  - storage cost review
  invocation_schema: 'Input: either (a) a Transfer Family server identifier + live-account context, (b) a Cost Explorer Transfer line-item document, OR (c) Transfer Family server configurations (endpointType, protocols, concurrency, user count) with at least 14 days of CloudWatch observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/MIGRATION_STEPS block per server, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE, NEED_MORE_INFO.'
  invocation_example: "# Minimal valid input (offline server classification):\nServerId: s-1234abcdef5678901\nEndpointType: VPC\nProtocols: [SFTP]\nRegion: us-east-1\nIdentityProviderType: API_GATEWAY (custom Lambda IdP)\nLoggingRole: arn:aws:iam::<acct>:role/TransferLogging\nConcurrency: 10 (configured), observed avg 0.5\nUsers: 25 configured, 3 active in last 30 days\nManaged workflows: 1 (post-upload Step Functions, 2,000,000 executions/month)\nMetrics (last 30 days):\n  - ConcurrentSessions: avg 0.5, p95 2, p99 3\n  - FilesIn: 2,000,000/month\n  - FilesOut: 500,000/month\n  - UserSessionsStarted: 6,000/month\nCloudWatch Logs volume: 500 GB/month from Transfer logging\nCost Explorer (Service=Transfer, last 30 days): $3,800\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
---

# Transfer Family Cost Optimizer

## What this skill does

Translates an AWS Transfer Family server's runtime posture into a
concrete cost-optimization recommendation with a dollar-denominated
savings estimate. The verdict is the highest-leverage action across
eight dimensions — endpoint type, idle server detection, protocol
selection, concurrency right-sizing, session duration, managed workflow
cost, CloudWatch Logs volume, and custom identity provider cost —
applied in priority order. Always pairs the recommendation with exact
CLI commands.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Five headline rules and the cost formula | First read |
| Mindset | Why endpoint type and idle detection are the top levers | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a server |
| Pre-flight data gate | Server config, CloudWatch metrics, Cost Explorer | Before any recommendation |
| Step 0 non-obvious behaviours | Endpoint pricing, idle charging, workflow scaling | Edge cases |
| Step 1 Endpoint type | PUBLIC vs VPC vs VPC_ENDPOINT | The headline savings dimension |
| Step 2 Idle server detection | Per-hour charge on idle servers | Sporadic-usage servers |
| Step 3 Protocol selection | SFTP vs FTPS vs FTP | Protocol cost implications |
| Step 4 Concurrency right-sizing | Concurrency limit vs server count | Multi-server deployments |
| Step 5 Session duration analysis | Long sessions tie up slots | Session-heavy workloads |
| Step 6 Managed workflow cost | Step Functions per-file scaling | Workflow-enabled servers |
| Step 7 CloudWatch Logs volume | SFTP logging cost | High-volume servers |
| Step 8 Custom identity provider | Lambda per-auth cost | Custom IdP deployments |
| Step 9 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, protocol verification | Before any apply CLI |

## Quick start

- **Endpoint type is the #1 lever.** PUBLIC endpoint is the cheapest
  — no VPC, no NAT Gateway, no VPC_ENDPOINT hourly surcharge. VPC and
  VPC_ENDPOINT add per-hour cost plus NAT Gateway data processing for
  outbound traffic. Migrate to PUBLIC wherever the network topology
  permits.
- **Cost formula (memorise this):**
  `monthly_transfer_cost = (server_hourly_rate × 730 hours)
                           + (GB_transferred × per_GB_rate)
                           + (workflow_executions × step_rate)
                           + (CloudWatch_Logs_GB × logs_rate)
                           + (Lambda_IdP_invocations × lambda_rate)`
- **Idle servers still charge per hour.** A Transfer server with zero
  sessions still incurs the full per-hour rate (~$0.30/hour = ~$219/month
  per server, PUBLIC). Detect and stop servers with near-zero
  ConcurrentSessions.
- **Managed workflow cost scales with file count, not file size.** A
  Step Functions managed workflow charges per execution (per file). 1M
  small files cost the same workflow fee as 1M large files — the
  per-file overhead dominates for high-volume small-file workloads.
- **CloudWatch Logs can dominate cost.** SFTP logging to CloudWatch
  generates one log event per file transfer. At high file volumes,
  the CloudWatch Logs ingest cost can exceed the Transfer server cost.

## Mindset

Transfer Family cost optimization is a usage-pattern decision, not a
pure capacity-sizing exercise. The goal is the endpoint type,
concurrency, and workflow configuration that minimizes dollar cost
while preserving the file-transfer SLO — not the maximum concurrency
that the server can handle.

Four principles guide every recommendation:

- **Per-hour charges dominate for low-usage servers.** A server running
  24/7 at $0.30/hour costs $219/month even with zero transfers. Idle
  detection is the highest-leverage action for sporadic workloads.
- **Endpoint type compounds with NAT Gateway cost.** A VPC endpoint
  server that routes outbound through a NAT Gateway adds per-GB data
  processing on top of the per-hour surcharge. PUBLIC eliminates both.
- **Managed workflow cost is invisible until you count executions.**
  Step Functions charges per state transition. A multi-step workflow
  on every uploaded file multiplies cost linearly with file count.
- **Logging cost is a silent multiplier.** CloudWatch Logs ingest at
  ~$0.50/GB; a high-volume SFTP server can generate hundreds of GB of
  logs per month, exceeding the server cost itself.

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| EndpointType = VPC or VPC_ENDPOINT AND public internet access is acceptable for the use case | **FURTHER_OPTIMIZATION_AVAILABLE** (endpoint) | Step 1 — migrate to PUBLIC |
| ConcurrentSessions avg < 0.1 AND server runs 24/7 | **FURTHER_OPTIMIZATION_AVAILABLE** (idle) | Step 2 — stop the server, use on-demand |
| Multiple servers AND combined ConcurrentSessions < single-server concurrency limit | **FURTHER_OPTIMIZATION_AVAILABLE** (server count) | Step 4 — consolidate onto fewer servers |
| Managed workflow enabled AND file count > 100,000/month AND workflow is multi-step | **FURTHER_OPTIMIZATION_AVAILABLE** (workflow) | Step 6 — simplify workflow or batch files |
| CloudWatch Logs volume > 100 GB/month from Transfer logging | **FURTHER_OPTIMIZATION_AVAILABLE** (logging) | Step 7 — reduce log verbosity or archive |
| Custom IdP Lambda invocations > 50,000/month AND auth caching not configured | **FURTHER_OPTIMIZATION_AVAILABLE** (IdP) | Step 8 — enable auth caching or batch |
| ConcurrentSessions sustained > 90% of configured concurrency | **FURTHER_OPTIMIZATION_AVAILABLE** (concurrency) | Step 4 — increase concurrency or add server |
| Average session duration > 30 min AND sessions are file-transfer-only | **FURTHER_OPTIMIZATION_AVAILABLE** (session) | Step 5 — investigate idle session hold |
| All dimensions verified AND PUBLIC + no idle + no workflow waste + logs controlled | **OPTIMIZED** | None — continue monitoring |
| Cost Explorer Transfer line items absent or window < 14 days | **NEED_MORE_INFO** | Pull 14-30 day Cost Explorer data, re-evaluate |

## Pre-flight: data gate (run before any optimization decision)

Optimization decisions are only as good as the underlying data. Pull
these metrics before any recommendation. Full CLI sequences are in
`references/transfer-pricing-and-endpoint-types.md`.

**Required data sources** (summarized — see reference for full CLI):
1. Server configuration: `aws transfer describe-server --server-id <id>`
2. ConcurrentSessions, FilesIn, FilesOut (14-30 day window): `aws cloudwatch get-metric-statistics --namespace AWS/Transfer`
3. User list and activity: `aws transfer list-users --server-id <id>` + `describe-user`
4. Managed workflows: `aws transfer list-workflows` + `describe-workflow`
5. CloudWatch Logs volume: `aws logs describe-metric-filters` + `get-metric-statistics` on `IncomingLogEvents`
6. Cost Explorer Transfer spend: `aws ce get-cost-and-usage --filter '{"Dimensions":{"Key":"SERVICE","Values":["Transfer"]}}'`
7. Custom IdP Lambda (if API_GATEWAY): `aws lambda get-function-configuration` + CloudWatch invocations
8. Step Functions executions (if managed workflow): `aws stepfunctions get-execution-history`

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `describe-server` returns `ResourceNotFoundException` | Server does not exist in this region. Skip. |
| `ConcurrentSessions` metric absent (server never used) | **NEED_MORE_INFO**. Verify server wiring; may be idle since creation. |
| Cost Explorer Transfer line items absent | **NEED_MORE_INFO**. Transfer Family may not be in use, or filter is wrong. |
| Observation window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| `State = OFFLINE` | Server is stopped. Surface as already-idle; no per-hour charge while offline. |
| CloudWatch `IncomingBytes` for Transfer log group absent | Logging may be disabled or log group deleted. Surface gap. |
| IAM denies `transfer:DescribeServer` | Surface as BLOCKED; cannot evaluate without server config. |

When Cost Explorer and CloudWatch metrics disagree, CloudWatch
(`ConcurrentSessions`, `FilesIn`, `FilesOut`) is the ground truth for
usage patterns — Cost Explorer reflects invoiced spend which may lag.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **PUBLIC is cheapest; VPC adds NAT cost.** A VPC endpoint server
  routing S3 access through a NAT Gateway incurs per-GB data processing
  ($0.045/GB) on top of the per-hour VPC surcharge. PUBLIC endpoints
  access S3 directly over the AWS network with no NAT overhead.
- **Idle servers charge per hour.** A server with zero sessions still
  incurs the full per-hour rate. The only way to stop the charge is to
  delete the server (configuration is lost) or accept the cost. For
  sporadic workloads, consider whether a serverless alternative (e.g.,
  S3 pre-signed URLs for occasional transfers) is viable.
- **Per-GB Transfer fee is on top of S3 data transfer.** Transfer
  Family charges a per-GB fee ($0.04/GB) for data transferred through
  the server. This is separate from S3 upload/download costs.
- **Managed workflow cost scales with file count.** A Step Functions
  managed workflow charges per execution. A 5-step workflow on 1M files
  = 5M state transitions. The cost is the same whether each file is 1
  KB or 1 GB.
- **CloudWatch Logs ingest is the silent cost multiplier.** SFTP
  logging generates one log event per file transfer operation. At
  $0.50/GB ingest, a server transferring 1M small files can generate
  200+ GB of logs per month — $100+ in logging cost alone.
- **FTP protocol is rarely available.** FTP (unencrypted) is supported
  only on VPC-type servers and is disabled by default. SFTP is the
  standard; FTPS adds TLS overhead. Protocol choice rarely affects
  cost directly but affects session duration and retry patterns.
- **Custom IdP Lambda charges per authentication.** Each SFTP login
  triggers a Lambda invocation via API Gateway. At high session-start
  rates, the Lambda + API Gateway cost compounds.
- **Concurrency limit is per-server, not per-user.** A server with
  `Protocols.Sftp.SessionPolicy` concurrency of 10 can handle 10
  concurrent sessions across ALL users. Spawning a second server to
  handle more is a cost decision vs increasing the concurrency limit.
- **Sticky sessions affect retry patterns.** If sticky sessions are
  configured, session reconnects target the same server. This can
  cause uneven load distribution, leading to over-provisioning.
- **Trusted host key rotation causes transient reconnects.** Rotating
  the host key invalidates cached client `known_hosts` entries. While
  rotation has no direct cost, the resulting retry storm can spike
  ConcurrentSessions and Lambda IdP invocations.

### Step 1: Endpoint type — PUBLIC vs VPC vs VPC_ENDPOINT

The endpoint type is the primary cost lever because it determines both
the per-hour rate and whether NAT Gateway data-processing fees apply.

**Pricing comparison:**
```
PUBLIC:        $0.30/hour per server (baseline rate)
               No NAT Gateway overhead; S3 access direct over AWS network
VPC:           $0.30/hour + VPC infrastructure (NAT Gateway $0.045/GB if outbound)
               Required for private connectivity or FTP protocol
VPC_ENDPOINT:  $0.30/hour + VPC endpoint hourly + per-GB fees
               Required for internal-only access without internet gateway
```

**Decision tree:**
```
Does the use case require private/VPC-internal access?
├── NO (clients connect from the public internet)
│   └── Use PUBLIC. It is the cheapest and avoids NAT Gateway cost.
├── YES — internal-only (no public internet access needed)
│   └── Use VPC_ENDPOINT. No internet gateway required.
└── YES — private connectivity with outbound internet needs
    └── Use VPC. Accept the NAT Gateway cost as a network requirement.
```

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

### Step 2: Idle server detection

Idle servers charge per hour regardless of usage. Detecting and
stopping them is the second lever.

**Idle detection threshold:**
| ConcurrentSessions (14-30 day avg) | Verdict |
|---|---|
| 0 (never used) | Server may be orphaned. Verify with the owning team before deleting. |
| < 0.1 (near-zero) | Idle. Consider deleting if the use case has moved to alternatives. |
| 0.1 – 1 | Low-usage. Evaluate whether the per-hour cost justifies the usage. |
| > 1 | Active. Proceed to other dimensions. |

**Idle server options:**
- **Delete the server** if the use case is decommissioned. This is
  the only way to fully eliminate the per-hour charge.
- **Migrate to serverless alternatives** (S3 pre-signed URLs, S3
  Access Points for occasional partner transfers) if the usage is
  sporadic and does not require the SFTP protocol.
- **Keep but document** if the server is required for compliance or
  partner connectivity even at low usage. Accept the cost as
  operational overhead.

### Step 3: Protocol selection (SFTP vs FTPS vs FTP)

Protocol selection rarely affects per-hour cost directly, but affects
session duration and retry patterns.

| Protocol | Cost impact | Notes |
|---|---|---|
| SFTP | Baseline | Default; most cost-efficient (single TCP connection, no TLS handshake) |
| FTPS | TLS overhead per session | Slightly longer session setup; negligible per-session cost impact |
| FTP | Only on VPC servers | Unencrypted; rare in practice. Requires VPC endpoint (higher cost). |

**Recommendation:** Use SFTP wherever the client supports it. FTPS is
acceptable if the partner requires it. FTP is almost never justified.

### Step 4: Concurrency right-sizing vs server count

Concurrency limit is per-server. Spawning multiple servers to handle
more sessions is a cost decision vs increasing the concurrency limit
on a single server.

**Decision gate:**
| Observed ConcurrentSessions | Configured concurrency | Recommendation |
|---|---|---|
| avg < 50% of configured | High | Reduce configured concurrency to ~p99 + 20% headroom |
| avg > 90% of configured | Low | Increase concurrency limit OR add a server |
| Multiple servers, each < 30% utilized | Over-provisioned | Consolidate onto fewer servers |

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

### Step 5: User session duration analysis

Long sessions tie up concurrency slots without transferring files. A
user who connects and holds the session open for hours without
transferring data wastes concurrency capacity.

**Session duration checklist:**
| Symptom | Fix |
|---|---|
| Average session > 30 min AND few files per session | Investigate idle session hold; set session timeout |
| Sessions correlate with business hours only | Consider stopping the server outside business hours (VPC_ENDPOINT only) |
| Session count >> file transfer count | Users are connecting and disconnecting without transferring; audit user scripts |

### Step 6: Managed workflow cost (Step Functions)

Managed workflows run Step Functions state machines on file upload/
download events. Cost scales with file count, not file size.

**Workflow cost formula:**
```
workflow_monthly_cost = files_per_month × steps_per_workflow × $0.025/1000
```

Example: 2,000,000 files/month, 5-step workflow:
- 2,000,000 × 5 × $0.000025 = $250/month in Step Functions charges

**Workflow optimization:**
| Signal | Recommendation |
|---|---|
| Multi-step workflow (5+ steps) on every file | Simplify the workflow; combine steps where possible |
| File count > 100,000/month AND workflow is validation-only | Move validation to S3 Event Notifications + Lambda (per-invocation, no state machine) |
| Workflow triggers on every small file | Batch files before triggering the workflow (reduce execution count) |
| Workflow has retry logic that re-executes on failure | Ensure idempotency; reduce retry count |

### Step 7: CloudWatch Logs volume

SFTP logging generates one log event per file transfer. At high file
volumes, the CloudWatch Logs ingest cost can exceed the server cost.

**Logging cost formula:**
```
logs_monthly_cost = log_GB_per_month × $0.50/GB (ingest)
                    + log_GB_per_month × $0.03/GB (storage, first 5 GB free)
```

**Logging optimization:**
| Signal | Recommendation |
|---|---|
| Log volume > 100 GB/month | Reduce log verbosity; log only errors and authentication events |
| Log group retention = Never expire | Set retention to 7-30 days; archive older logs to S3 |
| Every file operation logged at INFO | Change to WARNING or ERROR level; filter at the source |
| Logs used for audit compliance | Export to S3 (cheaper storage) and query via Athena |

### Step 8: Custom identity provider Lambda cost

Custom identity providers (API_GATEWAY type) invoke a Lambda function
on every SFTP authentication. At high session-start rates, the Lambda
+ API Gateway cost compounds.

**IdP cost formula:**
```
idp_monthly_cost = sessions_started_per_month × (lambda_per_invocation + apigw_per_request)
```

**IdP optimization:**
| Signal | Recommendation |
|---|---|
| Sessions started > 50,000/month | Enable authentication caching in the Lambda (short-lived cache for repeated logins) |
| API Gateway cost dominates | Evaluate Lambda Function URL instead of API Gateway (cheaper per-request) |
| Lambda is cold-start heavy | Provisioned concurrency on the IdP Lambda (trade-off: provisioned cost vs latency) |
| Every file transfer triggers re-authentication | Investigate session reuse; SFTP should authenticate once per session, not per file |

### Step 9: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  (N_servers × server_hourly × 730)
  + (GB_transferred × per_GB_rate)
  + (workflow_executions × step_rate)
  + (CloudWatch_Logs_GB × $0.50)
  + (Lambda_IdP_invocations × lambda_rate)
  + (NAT_GB × $0.045)            [if VPC]

projected_monthly_cost =
  (M_servers × server_hourly × 730)
  + (GB_transferred × per_GB_rate)
  + (projected_workflow_executions × step_rate)
  + (projected_Logs_GB × $0.50)
  + (projected_Lambda_invocations × lambda_rate)
  + 0                            [if migrated to PUBLIC]

monthly_saving = current_monthly_cost − projected_monthly_cost
```

Always state assumptions: server count, per-hour rate, GB transferred,
files per month, workflow steps, log volume, pricing region.

### Step 10: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions verified AND PUBLIC endpoint + no idle servers +
  no workflow waste + logs controlled → **OPTIMIZED**.
- Change applied and verified this session → **OPTIMIZED** (post-state).
- Data insufficient (metrics absent, window < 14 days) →
  **NEED_MORE_INFO**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every `NEED_MORE_INFO`/`BLOCKED` gate.

## Output format

```text
TARGET: <server-id>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <endpoint type>, <concurrency>, <servers>, <workflow>, <logs volume>
  Proposed: <endpoint type>, <concurrency>, <servers>, <workflow>, <logs volume>
  Dimensions changed: <endpoint | idle | protocol | concurrency | session | workflow | logs | idp>
  Dimensions checked: <list ALL eight, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>
    server hourly: <N_servers × $0.30 × 730>
    data transfer: <GB × $0.04/GB>
    workflow: <executions × steps × $0.025/1000>
    CloudWatch Logs: <GB × $0.50>
    Lambda IdP: <invocations × per-invocation>
    NAT Gateway: <GB × $0.045>     [if VPC]
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
  Assumptions: <list (server count, GB transferred, pricing region, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <server-id> in <region>.
  Proceed? (yes/no)"
```

Full worked examples (endpoint migration, idle server deletion,
workflow simplification, log reduction, already-optimized,
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
TARGET: <server-id>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <endpoint type>, <concurrency>, <servers>, <workflow>, <logs volume>
  Proposed: <endpoint type>, <concurrency>, <servers>, <workflow>, <logs volume>
  Dimensions changed: <endpoint | idle | protocol | concurrency | session | workflow | logs | idp>
  Dimensions checked: <list ALL eight, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show all cost subtotals
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

4. **NEVER recommend an endpoint type change without citing the network
   topology constraint.** The REASON MUST name the current endpoint
   type, the target endpoint type, and why the migration is safe (or
   blocked).

5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all eight dimensions, each marked
   ✓ (no finding) or → (finding).

6. **NEVER present a cost-neutral reconfiguration as "cost savings."**
   Surface the concurrency/latency improvement explicitly and set
   `Monthly saving: $0.00` with verdict `OPTIMIZED` (or
   `FURTHER_OPTIMIZATION_AVAILABLE` ONLY if a different dimension has
   positive saving).

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent. Copy this shape exactly.

```text
TARGET: s-1234abcdef5678901
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: VPC endpoint server with outbound traffic via NAT Gateway
  averages 0.5 concurrent sessions (near-idle) and processes 1,500 GB/month
  outbound ($67.50/month NAT data processing alone). ConcurrentSessions
  peak is 3, well under the configured concurrency of 10. Managed
  workflow (5-step) runs on 2,000,000 files/month, generating $250/month
  in Step Functions charges. CloudWatch Logs volume is 300 GB/month
  ($150/month in ingest). Migrating to PUBLIC eliminates NAT overhead;
  consolidating concurrency and simplifying the workflow reduce the
  remaining spend.
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
    Lambda IdP: $0.00 (service-managed)
    VPC endpoint: $73.00
  Projected monthly: $422.00
    server hourly: 1 × $0.30 × 730 = $219.00
    data transfer: 1,500 GB × $0.04 = $60.00
    workflow: 2,000,000 × 3 × $0.000025 = $150.00
    CloudWatch Logs: 50 GB × $0.50 = $25.00
    NAT Gateway: $0.00 (PUBLIC, no NAT)
    Lambda IdP: $0.00
    VPC endpoint: $0.00 (PUBLIC)
  Monthly saving: $397.50
    ($819.50 − $422.00 = $397.50 ✓)
  Annual saving: $4,770.00
MIGRATION_STEPS:
  1. Verify all clients can connect over the public internet:
     aws transfer describe-server --server-id s-1234abcdef5678901 | \
       jq '.EndpointType, .Protocols'
  2. Create a new PUBLIC server with the same configuration:
     aws transfer create-server --endpoint-type PUBLIC --protocols SFTP \
       --identity-provider-type SERVICE_MANAGED --region us-east-1
  3. Migrate users to the new server:
     aws transfer create-user --server-id <new-id> --user-name <user> \
       --ssh-public-key-body <key>
  4. Simplify the managed workflow from 5 steps to 3:
     aws transfer create-workflow --steps <simplified-steps-json>
  5. Reduce CloudWatch Logs verbosity (log only authentication + errors):
     aws transfer update-server --server-id <new-id> \
       --logging-role arn:aws:iam::<acct>:role/TransferLogging
  6. Delete the old VPC server once migration is confirmed:
     aws transfer delete-server --server-id s-1234abcdef5678901
  7. Monitor Cost Explorer (Service=Transfer) for 7 days post-change:
     aws ce get-cost-and-usage --filter '{"Dimensions":{"Key":"SERVICE","Values":["Transfer"]}}'
CONFIRM: About to migrate s-1234abcdef5678901 from VPC to PUBLIC endpoint,
  simplify workflow from 5 steps to 3, and reduce log volume from 300 GB
  to 50 GB. Monthly saving $397.50 (48.5% reduction). Proceed? (yes/no)
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
| `OPTIMIZED` | All dimensions verified (PUBLIC + no idle + no workflow waste + logs controlled + IdP cached); or a change was applied and verified this session. |
| `NEED_MORE_INFO` | Data gate failed: Cost Explorer Transfer line items absent, window < 14 days, or ConcurrentSessions metric unavailable with no fallback. |
| `BLOCKED` | Hard precondition prevents evaluation: IAM denies `transfer:DescribeServer`, server does not exist. |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `OPTIMIZED`, never `FURTHER_OPTIMIZATION_AVAILABLE`.
Exception: concurrency/latency improvement without cost change is
surfaced in REASON, not as dollar savings.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend migrating from VPC/VPC_ENDPOINT to PUBLIC without
   verifying that all clients can connect over the public internet.**
   Internal-only partners or compliance requirements may block PUBLIC
   migration. Verify the network topology before recommending.

2. **NEVER recommend deleting an idle server without confirming the use
   case is decommissioned.** An idle server may be required for partner
   connectivity, compliance, or disaster recovery. Confirm with the
   owning team before deleting.

3. **NEVER recommend simplifying a managed workflow without verifying
   each step's purpose.** Removing a validation or transformation step
   may break downstream processes. Audit the workflow steps before
   removing any.

4. **NEVER recommend reducing log verbosity without confirming the audit/
   compliance requirements.** Some regimes mandate full file-transfer
   logging. Verify before reducing log level.

5. **NEVER consolidate servers without verifying that the combined peak
   ConcurrentSessions fits within a single server's concurrency limit.**
   Over-consolidation causes session rejection during peak hours.

Extended anti-patterns in `references/transfer-pricing-and-endpoint-types.md`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Verify client connectivity before PUBLIC migration.** Confirm all
  clients can reach the server over the public internet before
  migrating from VPC/VPC_ENDPOINT.
- **Preserve user configurations during server migration.** When
  creating a new server and migrating users, copy all SSH public keys,
  home directory mappings, and session policies before deleting the old
  server.
- **Test the simplified workflow before cutover.** Run the new workflow
  on a test file to verify all required transformations still execute
  correctly.
- **Server deletion is irreversible.** `delete-server` removes the
  server and all its configuration. Ensure user data (home directories
  in S3) is preserved before deletion.
- **Log level changes apply to new transfers only.** In-flight log
  events are not re-filtered.
- **Concurrency limit changes are immediate.** Reducing the limit may
  reject in-flight sessions if the current count exceeds the new limit.
- **Bulk-operation limit:** Process at most 5 servers per batch. Sort
  by estimated savings, verify each batch before proceeding. Abort if
  any server shows increased errors or session rejection post-change.

## Recent AWS features (2024-2026)

- **Transfer Family managed workflows GA (2024-2025):** Step Functions-
  backed workflows triggered on file upload/download. Cost scales with
  file count × steps per workflow.
- **Transfer Family async (2025-2026):** Delegated authentication with
  caching, reducing per-authentication Lambda invocations for repeated
  logins.
- **Transfer Family web apps (2025):** AWS-managed web app for SFTP
  file transfer without a custom client. May reduce session duration
  for interactive users.
- **Improved CloudWatch metrics (2024):** `BytesIn`, `BytesOut`,
  `FilesIn`, `FilesOut`, `ConcurrentSessions`, `UserSessionsStarted`
  per server. Enables precise usage-pattern analysis.
- **Transfer Family directory listing optimization (2024-2025):**
  Reduced per-listing S3 ListObjects calls for large directories.
  Lowers indirect S3 request cost for browsing-heavy workloads.
- **VPC endpoint for Transfer Family (2024):** `VPC_ENDPOINT` type
  enables internal-only access without an internet gateway. Adds
  per-hour VPC endpoint fee but eliminates NAT Gateway requirement for
  internal-only servers.
- **S3 Access Points integration (2025):** Transfer Family home
  directory mappings can target S3 Access Points, simplifying multi-
  tenant server configurations.

## References

- `references/transfer-pricing-and-endpoint-types.md` — pricing tables,
  endpoint-type comparison (PUBLIC vs VPC vs VPC_ENDPOINT), protocol
  cost implications, concurrency limit reference, managed workflow
  Step Functions cost model, CloudWatch Logs cost model, custom IdP
  Lambda cost model, regional pricing multipliers, cost calculation
  worked examples.
- `references/worked-examples.md` — full worked examples (endpoint
  migration, idle server deletion, workflow simplification, log
  reduction, concurrency consolidation, already-optimized,
  NEED_MORE_INFO, end-to-end walkthrough).

## Domain

AWS CloudOps / Storage File-Transfer Cost Optimization & FinOps.

## AWS documentation

- **AWS Transfer Family User Guide** — https://docs.aws.amazon.com/transfer/latest/userguide/
- **AWS Transfer Family pricing** — https://aws.amazon.com/transfer-family/pricing/
- **Transfer Family endpoint types** — https://docs.aws.amazon.com/transfer/latest/userguide/configure-server-endpoint.html
- **Transfer Family managed workflows** — https://docs.aws.amazon.com/transfer/latest/userguide/create-workflow.html
- **Transfer Family custom identity providers** — https://docs.aws.amazon.com/transfer/latest/userguide/custom-lambda-idp.html
- **Transfer Family CloudWatch metrics** — https://docs.aws.amazon.com/transfer/latest/userguide/monitoring-cloudwatch.html
- **Transfer Family concurrency** — https://docs.aws.amazon.com/transfer/latest/userguide/configure-server-concurrency.html
- **AWS Step Functions pricing** — https://aws.amazon.com/step-functions/pricing/
- **Amazon CloudWatch Logs pricing** — https://aws.amazon.com/cloudwatch/pricing/
- **AWS CLI Transfer reference** — https://docs.aws.amazon.com/cli/latest/reference/transfer/
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
