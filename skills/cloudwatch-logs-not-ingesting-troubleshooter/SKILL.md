---
name: cloudwatch-logs-not-ingesting-troubleshooter
description: 'Diagnoses CloudWatch Logs not-ingesting scenarios through a thirteen-category diagnostic tree: log group vs log stream naming, IAM permissions for PutLogEvents (logs:CreateLogStream, logs:PutLogEvents), sequence token validation errors, CloudWatch agent misconfiguration (Windows vs Linux, JSON vs text), VPC Flow Logs delivery delays, Lambda log group auto-creation, retention policy auto-expiring logs, subscription filter (Kinesis/Lambda) consuming all capacity, metric filter pattern syntax errors, log group resource policy conflicts, account-level data protection policy blocking content, and cross-account log delivery (resource-based policy on destination). Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted agent / application error output and log-group configuration. Live-account diagnosis uses aws logs describe-log-groups, describe-log-streams, get-log-events, describe-metric-filters, describe-subscription-filters, describe-resource-policies, get-data-protection-policy, aws iam simulate-principal-policy, aws cloudtrail lookup-events, aws ec2 describe-flow-logs...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing a CloudWatch Logs not-ingesting scenario (logs not appearing in a log group, sequence token errors blocking PutLogEvents, CloudWatch agent not shipping, VPC Flow Logs not arriving, Lambda logs missing after the first invocation, retention auto-expiring before the SIEM pull, subscription filter consuming all Lambda concurrency, metric filter not firing, data-protection policy redacting content, cross-account delivery failing), walking a symptom to the failing layer with verify commands.
  when_not_to_use: Authoring a new CloudWatch agent configuration from scratch (use the cloudwatch-agent deployer), CloudWatch Logs Insights query tuning (use cloudwatch-logs-insights-troubshooter), CloudWatch alarm configuration (use cloudwatch-alarm-troubleshooter), or debugging application logging frameworks (use the application logs).
  activation_triggers: CloudWatch Logs not ingesting, logs not appearing in log group, PutLogEvents AccessDenied, logs CreateLogStream denied, InvalidSequenceTokenException, sequence token already accepted, CloudWatch agent not sending logs, VPC Flow Logs not arriving, Lambda logs missing, retention policy expiring logs, subscription filter Lambda concurrency, metric filter not firing, data protection policy CloudWatch, cross-account log delivery, troubleshoot CloudWatch Logs
  invocation_schema: 'Input: either (a) a symptom description (agent / application / aws logs error string, observed behaviour, "logs stopped at 03:00"), optionally paired with the log group name and the emitter IAM principal, OR (b) a log group name plus the source (application, Lambda, VPC Flow Logs, CloudWatch agent) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {LOG_GROUP_NAMING, LOG_STREAM_NAMING, IAM_PERMISSIONS, SEQUENCE_TOKEN, AGENT_MISCONFIG, VPC_FLOW_LOGS_DELIVERY, LAMBDA_AUTO_CREATE, RETENTION_EXPIRED, SUBSCRIPTION_FILTER_CAPACITY, METRIC_FILTER_PATTERN, RESOURCE_POLICY_CONFLICT, DATA_PROTECTION_BLOCKING, CROSS_ACCOUNT_POLICY, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"application logs stopped appearing in\n  /aws/lambda/fn-prod-processor at 03:00 UTC; PutLogEvents returns\n  InvalidSequenceTokenException on every attempt.\"\nLogGroup: /aws/lambda/fn-prod-processor\nSource: Lambda (auto-publishes to /aws/lambda/<name>)\nEmitter IAM principal: the Lambda service principal\nLast successful PutLogEvents: 03:00 UTC (2 hours ago)"
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudWatch Logs, log group, log stream, PutLogEvents, CreateLogStream, sequence token, InvalidSequenceTokenException, CloudWatch agent, VPC Flow Logs, retention policy, subscription filter, metric filter, resource policy, data protection, cross-account logs, logs not ingesting, troubleshoot
  tags: cloudwatch, management, troubleshooting, logs, iam, agent, retention, subscription-filter
---

# CloudWatch Logs Not-Ingesting Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  `logs not appearing at all` → LOG_GROUP_NAMING / IAM_PERMISSIONS;
  `AccessDenied ... logs:PutLogEvents` → IAM_PERMISSIONS;
  `InvalidSequenceTokenException` → SEQUENCE_TOKEN;
  agent is running but no logs ship → AGENT_MISCONFIG;
  VPC Flow Logs missing → VPC_FLOW_LOGS_DELIVERY;
  Lambda logs missing on first invocation → LAMBDA_AUTO_CREATE;
  old logs vanishing → RETENTION_EXPIRED;
  subscription receiver starved → SUBSCRIPTION_FILTER_CAPACITY;
  metric not firing → METRIC_FILTER_PATTERN;
  cross-account delivery denied → CROSS_ACCOUNT_POLICY;
  content showing `{{REDACTED}}` → DATA_PROTECTION_BLOCKING.
- **Always verify with a probe, never guess.** Each layer has a single
  command that proves or disproves it. A ROOT_CAUSE_IDENTIFIED verdict
  requires positive evidence — a failing probe that matches the symptom
  — not a process of elimination.
- **The sequence token must come from the previous PutLogEvents
  response.** CloudWatch Logs requires each PutLogEvents call to
  include the `sequenceToken` returned by the prior successful call to
  the same log stream. A stale, cached, or colliding token (two
  emitters writing to the same stream) produces
  `InvalidSequenceTokenException`. The fix is to read the token fresh
  before every write, not to cache it.
- **Subscription filters have a 2x account-concurrent-invocation
  budget.** Each subscription filter on a log group invokes its
  destination (Lambda / Kinesis) once per batch. Lambda subscriptions
  share the account's overall concurrency budget; a fan-out of several
  filters can exhaust Lambda concurrency and silently drop batches.
  The budget is per-account, not per-filter.
- **Cross-account log delivery needs a resource-based policy on the
  destination.** The destination account's log group must have a
  resource policy granting `logs:PutLogEvents` to the source account.
  IAM alone on the source side is not enough — the destination
  resource policy is the gating side.

## Mindset

A "logs not ingesting" report is almost always a naming, IAM, token,
or agent-configuration incident, not a CloudWatch service outage.
Senior operators do not start by reading the application code; they
start with `describe-log-groups`, the emitter's IAM policy simulation,
the latest log stream, and the agent configuration, and only then
escalate to the application.

## Philosophy

The four senior-operator behaviours (per-stream sequence tokens, Lambda auto-create IAM gating, silent retention expiry, destination-gated cross-account delivery) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the reasoning behind the diagnostic order.

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| `logs not appearing`, empty log group | LOG_GROUP_NAMING | `describe-log-groups` — confirm the expected log group exists and the source writes to it |
| `AccessDenied ... logs:PutLogEvents` / `logs:CreateLogStream` | IAM_PERMISSIONS | `iam simulate-principal-policy` for `logs:PutLogEvents`, `logs:CreateLogStream` on the log group ARN |
| `InvalidSequenceTokenException`, `The given sequenceToken is invalid` | SEQUENCE_TOKEN | Read the current stream's `uploadSequenceToken` via `describe-log-streams`; compare to what the emitter is sending |
| Agent running, no logs in CloudWatch | AGENT_MISCONFIG | Agent config file — `logs.logs_create_log_stream`, `log_stream_name`, JSON vs text parsing |
| VPC Flow Logs missing | VPC_FLOW_LOGS_DELIVERY | `ec2 describe-flow-logs` — confirm the flow log is ACTIVE and points to the right log group |
| Lambda logs missing on first invocation | LAMBDA_AUTO_CREATE | `lambda get-function-configuration` execution role; `iam simulate-principal-policy` for `logs:CreateLogGroup` |
| Old logs vanishing | RETENTION_EXPIRED | `describe-log-groups` `retentionInDays` |
| Subscription receiver starved / dropped batches | SUBSCRIPTION_FILTER_CAPACITY | `describe-subscription-filters`; Lambda concurrency metrics for the destination |
| Metric not firing | METRIC_FILTER_PATTERN | `describe-metric-filters`; test the pattern with `filter-log-events` |
| Content showing `{{REDACTED}}` | DATA_PROTECTION_BLOCKING | `get-data-protection-policy` on the log group |
| Cross-account delivery denied | CROSS_ACCOUNT_POLICY | `describe-resource-policies` on the destination account |

## Pre-flight: log group and gather-info gate

### Account-wide pre-flight commands

Account-wide pre-flight command listing (describe-log-groups, describe-log-streams, get-log-events, describe-subscription-filters, describe-metric-filters, get-data-protection-policy, health describe-events) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before live-account diagnosis.

### Log-group-state short-circuit

| `describe-log-groups` field | Effect on diagnosis |
|---|---|
| Log group missing | The source never created it. Route to LOG_GROUP_NAMING (wrong name) or LAMBDA_AUTO_CREATE (Lambda role missing `logs:CreateLogGroup`). |
| `retentionInDays: 1` (or very short) | Old streams are being deleted silently. Route to RETENTION_EXPIRED. |
| `kmsKeyId: <cmk>` | The log group is CMK-encrypted; the emitter needs `kms:GenerateDataKey` and readers need `kms:Decrypt`. A KMS denial surfaces as a PutLogEvents failure. |
| Empty `storedBytes` | Nothing has ever been ingested — likely a naming or IAM issue on the very first write. |

If the input is malformed (missing log group name, no symptom
description, no emitter context), emit:

```text
TARGET: <log-group-name or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a symptom
  description (the error string or observed behaviour) and the log
  group name.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact error string or
  observed behaviour, (2) the log group name, and (3) the emitter
  source (application / Lambda / VPC Flow Logs / CloudWatch agent)
  and its IAM principal.
```

## Process — Diagnostic decision tree (apply in symptom order)

### Step 0: Non-obvious behaviours that change diagnosis

Step 0 non-obvious behaviours (sequence-token serialization, Lambda auto-create gating, silent retention deletion, subscription concurrency budget, destination resource policies, metric-filter raw-message matching, ingestion-time redaction, agent log_stream_name defaults) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand — each behaviour changes which layer the symptom routes to.

### Step 1: Symptom entry

| Symptom | Branch |
|---|---|
| Logs not appearing; empty log group | Step 2 — Log group naming |
| `AccessDenied ... logs:PutLogEvents` / `logs:CreateLogStream` | Step 3 — IAM |
| `InvalidSequenceTokenException` | Step 4 — Sequence token |
| Agent running, no logs shipping | Step 5 — Agent misconfig |
| VPC Flow Logs missing | Step 6 — VPC Flow Logs |
| Lambda logs missing on first invocation | Step 7 — Lambda auto-create |
| Old logs vanishing | Step 8 — Retention |
| Subscription receiver starved | Step 9 — Subscription filter |
| Metric not firing | Step 10 — Metric filter |
| Content showing `{{REDACTED}}` | Step 11 — Data protection |
| Cross-account delivery denied | Step 12 — Cross-account |

### Step 2: LOG_GROUP_NAMING — wrong log group or log stream name

Symptom: logs not appearing where the operator expects them.

LOG_GROUP_NAMING probe commands (describe-log-groups / describe-log-streams by prefix) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when executing this layer's probe.
Common naming mismatches:

| Source | Expected log group | Common mistake |
|---|---|---|
| Lambda function `fn-prod` | `/aws/lambda/fn-prod` | Operator queries `/aws/lambda/fn-prod-prod` or `/aws/lambda/fn_prod` |
| API Gateway REST API `abc123` | `API-Gateway-Execution-Logs_<id>/<stage>` | Operator queries `API-Gateway-Execution-Logs_<id>` (missing stage) |
| CloudWatch agent (`/var/log/app.log`) | whatever is configured in the agent's `logs` section | Agent config has a typo or wrong group name |
| VPC Flow Logs | the log group configured in `create-flow-logs` | Operator queries the default group, not the configured one |

If the log group the source writes to differs from the one the
operator is querying, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: LOG_GROUP_NAMING`. Fix: align the source's configured log
group name with what the operator expects to query.

### Step 3: IAM_PERMISSIONS — missing logs:PutLogEvents or CreateLogStream

Symptom: `AccessDenied ... is not authorized to perform:
logs:PutLogEvents` or `logs:CreateLogStream`.

IAM_PERMISSIONS probe (simulate-principal-policy for logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents, logs:DescribeLogStreams) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when executing this layer's probe.
For an emitter to write to CloudWatch Logs, it needs at minimum:

| Action | When |
|---|---|
| `logs:CreateLogGroup` | First-ever write to a new log group (Lambda auto-create needs this) |
| `logs:CreateLogStream` | First write to a new log stream |
| `logs:PutLogEvents` | Every batch of events |
| `logs:DescribeLogStreams` | Some SDKs call this before PutLogEvents to find the stream |

If any required action returns `implicitDeny`, **ROOT_CAUSE_IDENTIFIED**
with `LAYER: IAM_PERMISSIONS`. Add the missing action on the specific
log group ARN. For Lambda, the managed policy
`AWSLambdaBasicExecutionRole` includes all four actions on
`arn:aws:logs:*:*:log-group:/aws/lambda/*` — if that managed policy is
detached, Lambda logs silently fail.

### Step 4: SEQUENCE_TOKEN — sequence token validation errors

Symptom: `InvalidSequenceTokenException: The given sequenceToken is
invalid. The next expected sequenceToken is: <token>`.

SEQUENCE_TOKEN probe (describe-log-streams uploadSequenceToken via jq) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when executing this layer's probe.
The `uploadSequenceToken` returned by `describe-log-streams` is the
token the next PutLogEvents call must include. Common causes:

| Pattern | Cause |
|---|---|
| Two emitters writing to the same stream | Each sees the other's token as stale; both get InvalidSequenceTokenException |
| Emitter caches the token across calls | After the first call, the cached token is stale |
| Emitter retries after a transient error | The retry uses the old token; the original call may have succeeded |

If the emitter's sent token does not match the stream's current
`uploadSequenceToken`, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: SEQUENCE_TOKEN`. Fix: one writer per stream; refresh the token
from `describe-log-streams` (or from the previous PutLogEvents
response's `nextSequenceToken`) before every write.

### Step 5: AGENT_MISCONFIG — CloudWatch agent misconfiguration

Symptom: agent is running (`status: running`) but no logs appear in
CloudWatch.

AGENT_MISCONFIG probes (agent status via amazon-cloudwatch-agent-ctl, config jq) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when executing this layer's probe.
Common misconfigurations:

| Pattern | Cause |
|---|---|
| `logs.logs_create_log_stream: false` and stream does not exist | Agent does not create the stream; no events are written |
| `log_stream_name` hardcoded to the same string across hosts | Concurrent writes collide; sequence token errors |
| `file_path` does not match the application's log location | Agent is tailing the wrong file; no events captured |
| `log_group_name` typo | Events go to a different log group than the operator expects |
| `multi_line_start_pattern` wrong | Multi-line stack traces are split incorrectly; events malformed |
| Windows agent: `collect_list` with wrong `file_path` (Windows paths) | Windows path format differs; `C:\\logs\\app.log` not `/var/log/app.log` |
| JSON log format: `json_log: true` but application emits text | Metric filters expecting JSON see no fields |
| Agent IAM role missing `logs:PutLogEvents` | Agent cannot write; check `CloudWatchAgentServerPolicy` attachment |

If the agent config or IAM role is misconfigured, **ROOT_CAUSE_IDENTIFIED**
with `LAYER: AGENT_MISCONFIG`. Fix: correct the config, restart the
agent, verify with `get-log-events`.

### Step 6: VPC_FLOW_LOGS_DELIVERY — VPC Flow Logs not arriving

Symptom: VPC Flow Logs are enabled but the log group is empty.

VPC_FLOW_LOGS_DELIVERY probe (ec2 describe-flow-logs) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when executing this layer's probe.
| `describe-flow-logs` field | Effect |
|---|---|
| Flow log missing | No flow log is configured for the VPC/ENI/Subnet — create one |
| `FlowLogStatus: ACTIVE` | Flow log is publishing; check aggregation interval (default 10 minutes) |
| `FlowLogStatus: FAILED` | Delivery failed; often IAM (delivers logs role) or missing log group |
| `DeliverLogsPermissionArn` role missing `logs:PutLogEvents` | Delivery denied silently |

VPC Flow Logs aggregate over a window (1 or 10 minutes) before
publishing; a delay of up to 10 minutes is normal. If the flow log is
`ACTIVE` but the log group is empty after 15 minutes, check the
delivery role's IAM permissions. If the delivery role or log group is
the issue, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: VPC_FLOW_LOGS_DELIVERY`.

### Step 7: LAMBDA_AUTO_CREATE — Lambda logs missing on first invocation

Symptom: newly-deployed Lambda function runs successfully but no logs
appear in CloudWatch.

LAMBDA_AUTO_CREATE probes (lambda get-function-configuration + simulate-principal-policy) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when executing this layer's probe.
If the execution role lacks `logs:CreateLogGroup`, the Lambda service
cannot create `/aws/lambda/<name>` on the first invocation and logs
are silently dropped. If `logs:CreateLogGroup` returns `implicitDeny`,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: LAMBDA_AUTO_CREATE`. Fix:
attach `AWSLambdaBasicExecutionRole` (or add the missing
`logs:CreateLogGroup` permission).

### Step 8: RETENTION_EXPIRED — retention policy auto-expiring logs

Symptom: old log streams are vanishing; the log group has only recent
streams.

RETENTION_EXPIRED probe (describe-log-groups retentionInDays via jq) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when executing this layer's probe.
If `retentionInDays` is shorter than expected (e.g., `1` when the
operator thought it was `Never expire`), **ROOT_CAUSE_IDENTIFIED** with
`LAYER: RETENTION_EXPIRED`. Fix: raise the retention with
`put-retention-policy`. Note that expired logs are not recoverable;
the deletion is final.

### Step 9: SUBSCRIPTION_FILTER_CAPACITY — subscription filter consuming all capacity

Symptom: the subscription destination (Lambda / Kinesis) is starved or
dropping batches; CloudWatch Logs shows the source log group receiving
events but the downstream is not processing all of them.

SUBSCRIPTION_FILTER_CAPACITY probes (describe-subscription-filters, ConcurrentExecutions metrics, account limits) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when executing this layer's probe.
Subscription filters deliver to Lambda at up to 2x the account's
concurrent-invocations quota (a per-account subscription budget). A
fan-out across several high-volume log groups can exhaust this budget
and silently drop batches. If the destination's concurrency is at the
account limit and batches are being dropped, **ROOT_CAUSE_IDENTIFIED**
with `LAYER: SUBSCRIPTION_FILTER_CAPACITY`. Fix: provision reserved
concurrency for the destination, reduce fan-out, or switch to Kinesis
as the destination (higher throughput).

### Step 10: METRIC_FILTER_PATTERN — metric filter pattern syntax errors

Symptom: the log group is receiving events but the metric alarm is not
firing.

METRIC_FILTER_PATTERN probes (describe-metric-filters, filter-log-events pattern test) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when executing this layer's probe.
Common pattern issues:

| Pattern | Issue |
|---|---|
| `{ $.status = 500 }` | Only matches if the event is valid JSON with a `status` field; text logs produce zero matches |
| `[ERROR]` (term match) | Case-sensitive; `[error]` will not match |
| Unbalanced quotes / brackets | Filter is rejected silently; no metric points emitted |
| `metricTransformations` with wrong `metricNamespace` or `metricValue` | The metric exists but in a different namespace; the alarm queries the wrong namespace |

If the pattern does not match the actual log format, **ROOT_CAUSE_IDENTIFIED**
with `LAYER: METRIC_FILTER_PATTERN`. Fix: correct the pattern to match
the log format; verify with `filter-log-events`.

### Step 11: DATA_PROTECTION_BLOCKING — data protection policy redacting content

Symptom: log events appear but contain `{{REDACTED}}` where sensitive
data was expected.

DATA_PROTECTION_BLOCKING probe (get-data-protection-policy) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when executing this layer's probe.
An account-level or log-group-level data protection policy replaces
sensitive data patterns (AWS access keys, email addresses, credit card
numbers) with `{{REDACTED}}` at ingestion time. If a data protection
policy is active and the operator did not expect it,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: DATA_PROTECTION_BLOCKING`.
Surface the policy; do NOT recommend disabling without a security
owner.

### Step 12: CROSS_ACCOUNT_POLICY — cross-account delivery failing

Symptom: source account A's logs are not arriving in destination
account B's log group.

CROSS_ACCOUNT_POLICY probes (describe-resource-policies, describe-destinations) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when executing this layer's probe.
Cross-account log delivery requires a resource-based policy on the
destination (account B) granting the source account (account A)
`logs:PutLogEvents` (or `logs:PutSubscriptionFilter` for the
destination pattern). The source account's IAM policy is necessary
but not sufficient.

If the destination has no resource policy listing the source account,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: CROSS_ACCOUNT_POLICY`. Fix: add
a resource policy on the destination log group (or use
`put-destination` / `put-destination-policy`).

### Step 13: INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, emit
`VERDICT: INSUFFICIENT_DATA` with the missing probe listed.

## Output format

```text
TARGET: <log-group-name>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <LOG_GROUP_NAMING | LOG_STREAM_NAMING | IAM_PERMISSIONS |
        SEQUENCE_TOKEN | AGENT_MISCONFIG | VPC_FLOW_LOGS_DELIVERY |
        LAMBDA_AUTO_CREATE | RETENTION_EXPIRED |
        SUBSCRIPTION_FILTER_CAPACITY | METRIC_FILTER_PATTERN |
        RESOURCE_POLICY_CONFLICT | DATA_PROTECTION_BLOCKING |
        CROSS_ACCOUNT_POLICY | UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <log-group> in <region>.
  Proceed? (yes/no)"
```

### Worked example — IAM_PERMISSIONS on Lambda execution role

```text
TARGET: /aws/lambda/fn-prod-processor
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The Lambda execution role is missing logs:CreateLogGroup and
  logs:PutLogEvents on the /aws/lambda/* log group ARN. The Lambda
  service silently failed to auto-create the log group on first
  invocation; no logs have been ingested since the deploy 1 hour ago.
LAYER: IAM_PERMISSIONS
EVIDENCE:
  - Symptom: fn-prod-processor runs successfully (returns 200) but
    /aws/lambda/fn-prod-processor has zero log streams.
  - Probe: aws iam simulate-principal-policy for the execution role
    returns implicitDeny for logs:CreateLogGroup and logs:PutLogEvents
    on arn:aws:logs:us-east-1:111111111111:log-group:/aws/lambda/*.
  - Probe: aws logs describe-log-streams confirms zero streams in the
    log group (it does not exist).
  - Passing: the function's InvocationRate metric shows traffic; the
    function is being invoked and returning success. The execution
    role has AWSLambdaVPCAccessExecutionRole (VPC) but
    AWSLambdaBasicExecutionRole is NOT attached.
REMEDIATION:
  1. Attach AWSLambdaBasicExecutionRole:
     aws iam attach-role-policy --role-name fn-prod-processor-role \
       --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  2. Re-invoke the function; the log group will auto-create on the
     next invocation.
  3. Verify with aws logs describe-log-streams --log-group-name
     /aws/lambda/fn-prod-processor.
```

### Worked example — SEQUENCE_TOKEN collision

Worked example — SEQUENCE_TOKEN collision (ECS firelens shared stream) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when diagnosing token collisions; the primary IAM_PERMISSIONS worked example stays inline above.

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom.
- NEVER recommend refreshing the sequence token as the only fix
  without checking for concurrent writers. The root cause of
  InvalidSequenceTokenException is often two emitters sharing a
  stream; refreshing the token masks the symptom but the collisions
  recur on the next write.
- NEVER assume Lambda logs are missing because the function is
  failing. The function may run successfully while logs are silently
  dropped because the execution role lacks `logs:CreateLogGroup`. Run
  `simulate-principal-policy` before concluding the function is
  broken.
- NEVER assume retention is `Never expire` without reading
  `retentionInDays`. Retention changes are silent; an operator or a
  tag-based automation may have lowered it.
- NEVER assume subscription filter drops are a Lambda-side bug. The
  per-account 2x concurrency budget for subscription deliveries can
  silently drop batches when multiple filters fan out to the same
  account's Lambda quota.
- NEVER assume metric filters work on text logs the same way they
  work on JSON logs. A pattern like `{ $.status = 500 }` only matches
  JSON; a text log line requires a term-based pattern like `ERROR 500`.
- NEVER recommend disabling a data protection policy without a
  security owner sign-off. The policy is there for compliance;
  disabling it may violate a regulatory requirement.
- NEVER add a resource-based policy on a destination log group with a
  too-broad principal (`"AWS": "*"`) for cross-account delivery.
  Always scope to the source account root or a specific role ARN.
- NEVER assume cross-account log delivery works with only the source
  account's IAM policy. The destination's resource-based policy is
  the gating side; missing it produces silent delivery failure.
- NEVER conflate CloudWatch Logs Insights query failures with
  ingestion failures. Insights queries time out or return empty on
  syntax errors regardless of whether logs are arriving — use
  `get-log-events` to verify ingestion.
- NEVER assume the CloudWatch agent's `log_stream_name` defaults are
  safe. A hardcoded shared string across hosts causes sequence-token
  collisions; always use `{instance_id}` or `{hostname}`.

## Pre-flight safety checks (run before any state-changing CLI)

Pre-flight safety checks (CONFIRM gate, read-only-first rule, retention/subscription/resource-policy/KMS warnings, batch limits) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before executing any state-changing CLI.

## Remediation guidance

The per-layer remediation summary table moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when writing REMEDIATION; each step section above already carries its inline fix.

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when redaction, subscription budgets, or aggregation intervals are in play.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Philosophy behaviours, Step 0 non-obvious behaviours, remediation summary table, and Recent AWS features (2024-2026) moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — account-wide pre-flight commands, Step 2-12 probe commands, and pre-flight safety checks moved from SKILL.md
- [references/worked-examples.md](references/worked-examples.md) — SEQUENCE_TOKEN collision worked example moved from SKILL.md (primary IAM_PERMISSIONS example stays inline)
- [references/cwl-ingestion-and-iam-reference.md](references/cwl-ingestion-and-iam-reference.md) — ingestion and IAM reference (pre-existing)
- [references/cwl-filters-and-cross-account-reference.md](references/cwl-filters-and-cross-account-reference.md) — filter patterns and cross-account delivery reference (pre-existing)

## Domain

AWS CloudOps / CloudWatch Logs Ingestion Diagnostics, Identity & Access
Management for Logs, Agent Configuration, Subscription Filter Delivery,
Cross-Account Log Routing, and Data Protection.

## AWS documentation

- **Amazon CloudWatch Logs User Guide** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html
- **CloudWatch Logs IAM permissions** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/permissions-reference-cwl.html
- **PutLogEvents API (sequence tokens)** — https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_PutLogEvents.html
- **CloudWatch agent configuration** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html
- **VPC Flow Logs** — https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html
- **Subscription filters** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/SubscriptionFilters.html
- **Metric filters** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html
- **Data protection policies** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/log-groups-dataprotection.html
- **Cross-account log delivery** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CrossAccountSubscriptions.html
- **CloudWatch Logs retention** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html
