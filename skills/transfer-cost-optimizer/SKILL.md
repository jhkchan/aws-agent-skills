---
name: transfer-cost-optimizer
description: 'Optimises AWS Transfer Family cost across eight dimensions: server endpoint type (PUBLIC vs VPC vs VPC_ENDPOINT — PUBLIC is cheapest with no VPC/NAT cost; VPC_ENDPOINT for internal-only; VPC for private connectivity with NAT Gateway overhead), per-hour server cost vs usage pattern (idle servers still incur the full per-hour charge — detect and stop them), protocol selection (SFTP vs FTPS vs FTP — SFTP is the baseline; FTP adds no TLS overhead but is rare in practice), concurrency vs server count (right-size concurrency limits vs spawning multiple servers), user session duration analysis (long sessions tie up concurrency slots), data transfer cost (S3 upload/download per-GB is the baseline; Transfer Family adds a per-GB fee on top), managed workflow cost (Step Functions execution per file — scales with file count not file size, so many small files are disproportionately expensive), CloudWatch Logs volume (SFTP logging to CloudWatch can dominate cost for high-volume servers), trusted host key rotation (no d...'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted Transfer Family server configs, CloudWatch metrics, and Cost Explorer Transfer line items. Live-account optimization uses aws transfer describe-server, aws transfer list-users, aws transfer describe-user, aws transfer describe-workflow (managed workflows), aws transfer list-accesses, aws cloudwatch get-metric-statistics (AWS/Transfer namespace: FilesIn...'
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising AWS Transfer Family cost, choosing between PUBLIC vs VPC vs VPC_ENDPOINT server types, detecting and stopping idle Transfer servers, right-sizing concurrency limits vs server count, analysing user session duration, evaluating managed workflow (Step Functions) cost, reducing CloudWatch Logs volume from SFTP logging, auditing custom identity provider Lambda cost, or reviewing SFTP/FTPS endpoint spend.
  when_not_to_use: S3 storage cost optimization (use s3-lifecycle-optimizer), DataSync cost (use datasync-cost-optimizer), general VPC/NAT Gateway cost (use vpc-cost-optimizer), or Transfer Family server troubleshooting (connection errors, authentication failures — use transfer-family-troubleshooter). This skill focuses on cost-driven optimization decisions for Transfer Family spend, not on functional debugging of broken servers.
  activation_triggers: ''
  invocation_schema: '''Input: either (a) a Transfer Family server identifier + live-account context, (b) a Cost Explorer Transfer line-item document, OR (c) Transfer Family server configurations (endpointType, protocols, concurrency, user count) with at least 14 days of CloudWatch observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/MIGRATION_STEPS block per server, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE, NEED_MORE_INFO.'''
  invocation_example: '"# Minimal valid input (offline server classification):\nServerId: s-1234abcdef5678901\nEndpointType: VPC\nProtocols: [SFTP]\nRegion: us-east-1\nIdentityProviderType: API_GATEWAY (custom Lambda IdP)\nLoggingRole: arn:aws:iam::<acct>:role/TransferLogging\nConcurrency: 10 (configured), observed avg 0.5\nUsers: 25 configured, 3 active in last 30 days\nManaged workflows: 1 (post-upload Step Functions, 2,000,000 executions/month)\nMetrics (last 30 days):\n  - ConcurrentSessions: avg 0.5, p95 2, p99 3\n  - FilesIn: 2,000,000/month\n  - FilesOut: 500,000/month\n  - UserSessionsStarted: 6,000/month\nCloudWatch Logs volume: 500 GB/month from Transfer logging\nCost Explorer (Service=Transfer, last 30 days): $3,800\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Transfer Family, AWS Transfer, SFTP, FTPS, FTP, cost optimization, server endpoint, PUBLIC endpoint, VPC endpoint, VPC_ENDPOINT, idle server, per-hour cost, concurrency, session duration, managed workflow, Step Functions, CloudWatch Logs, trusted host key, custom identity provider, Lambda IdP, sticky session, data transfer, S3 upload, storage FinOps
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

per-hour dominance, endpoint+NAT compounding, invisible workflow cost, silent log multiplier — moved verbatim.
Full detail: [Advanced patterns](references/advanced-patterns.md).

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

server config, CloudWatch metrics, user activity, workflows, logs volume, Cost Explorer, IdP Lambda, Step Functions — moved verbatim.
Full detail: [Diagnostic commands](references/diagnostic-commands.md).

### Data-quality short-circuits

ResourceNotFound, absent metrics/line items, short window, OFFLINE, IAM deny — moved verbatim.
Full detail: [Diagnostic commands](references/diagnostic-commands.md).

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

PUBLIC vs NAT, idle charging, per-GB fee, workflow file-count scaling, log multiplier, FTP availability, IdP per-auth, per-server concurrency, sticky sessions, host-key rotation — moved verbatim.
Full detail: [Advanced patterns](references/advanced-patterns.md).

### Step 1: Endpoint type — PUBLIC vs VPC vs VPC_ENDPOINT

The endpoint type is the primary cost lever because it determines both
the per-hour rate and whether NAT Gateway data-processing fees apply.

per-hour rates, NAT Gateway per-GB, VPC endpoint fees — moved verbatim.
Full detail: [Pricing and endpoint types](references/transfer-pricing-and-endpoint-types.md).

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

vpc_monthly vs public_monthly formula, 500 GB worked example — moved verbatim.
Full detail: [Worked examples](references/worked-examples.md).

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

delete, migrate to serverless, keep-but-document — moved verbatim.
Full detail: [Advanced patterns](references/advanced-patterns.md).

### Step 3: Protocol selection (SFTP vs FTPS vs FTP)

Protocol selection rarely affects per-hour cost directly, but affects
session duration and retry patterns.

SFTP baseline, FTPS TLS overhead, FTP VPC-only — moved verbatim.
Full detail: [Advanced patterns](references/advanced-patterns.md).

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

N vs M servers formula, 3-to-1 worked example — moved verbatim.
Full detail: [Worked examples](references/worked-examples.md).

### Step 5: User session duration analysis

idle hold timeout, business-hours stop, connect-without-transfer audit — moved verbatim.
Full detail: [Advanced patterns](references/advanced-patterns.md).

### Step 6: Managed workflow cost (Step Functions)

Managed workflows run Step Functions state machines on file upload/
download events. Cost scales with file count, not file size.

**Workflow cost formula:**
```
workflow_monthly_cost = files_per_month × steps_per_workflow × $0.025/1000
```

2M-file $250/month example, workflow optimization signals — moved verbatim.
Full detail: [Worked examples](references/worked-examples.md).

### Step 7: CloudWatch Logs volume

SFTP logging generates one log event per file transfer. At high file
volumes, the CloudWatch Logs ingest cost can exceed the server cost.

**Logging cost formula:**
```
logs_monthly_cost = log_GB_per_month × $0.50/GB (ingest)
                    + log_GB_per_month × $0.03/GB (storage, first 5 GB free)
```

verbosity reduction, retention, log level, S3+Athena export — moved verbatim.
Full detail: [Advanced patterns](references/advanced-patterns.md).

### Step 8: Custom identity provider Lambda cost

Custom identity providers (API_GATEWAY type) invoke a Lambda function
on every SFTP authentication. At high session-start rates, the Lambda
+ API Gateway cost compounds.

**IdP cost formula:**
```
idp_monthly_cost = sessions_started_per_month × (lambda_per_invocation + apigw_per_request)
```

auth caching, Lambda URL vs API Gateway, provisioned concurrency, session reuse — moved verbatim.
Full detail: [Advanced patterns](references/advanced-patterns.md).

### Step 9: Impact estimation

current vs projected monthly cost formulas, savings, assumptions — moved verbatim.
Full detail: [Pricing and endpoint types](references/transfer-pricing-and-endpoint-types.md).

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

CONFIRM gate, connectivity check, user-config preservation, workflow test, irreversible delete, log-level timing, concurrency immediacy, 5-server batch limit — moved verbatim.
Full detail: [Diagnostic commands](references/diagnostic-commands.md).


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

## References (load on demand)

- [Pricing and endpoint types](references/transfer-pricing-and-endpoint-types.md) — endpoint pricing comparison, impact-estimation formulas
- [Worked examples](references/worked-examples.md) — endpoint-migration and consolidation savings math, workflow cost example
- [Diagnostic commands](references/diagnostic-commands.md) — required data sources, data-quality short-circuits, pre-flight safety checks
- [Advanced patterns](references/advanced-patterns.md) — mindset principles, Step 0 gotchas, per-step optimization signals, recent features

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
