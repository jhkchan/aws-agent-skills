---
description: Diagnoses CloudWatch Logs not-ingesting scenarios through a thirteen-category diagnostic tree (log group / stream naming, IAM PutLogEvents, sequence token, agent misconfig, VPC Flow Logs, Lambda auto-create, retention, subscription filter capacity, metric filter pattern, resource policy, data protection, cross-account delivery) — emits ROOT_CAUSE_IDENTIFIED with the specific failure layer or INSUFFICIENT_DATA.
nl_triggers:
  - "CloudWatch Logs not ingesting"
  - "logs not appearing in log group"
  - "PutLogEvents AccessDenied"
  - "logs CreateLogStream denied"
  - "InvalidSequenceTokenException"
  - "sequence token already accepted"
  - "CloudWatch agent not sending logs"
  - "VPC Flow Logs not arriving"
  - "Lambda logs missing"
  - "Lambda logs not in CloudWatch"
  - "retention policy expiring logs"
  - "subscription filter Lambda concurrency"
  - "metric filter not firing"
  - "data protection policy CloudWatch"
  - "cross-account log delivery"
  - "troubleshoot CloudWatch Logs"
  - "logs stopped ingesting"
routes_to: cloudwatch-logs-not-ingesting-troubleshooter
---

# /aws:troubleshoot-cloudwatch-logs-not-ingesting

Activate the `cloudwatch-logs-not-ingesting-troubleshooter` skill and
diagnose a CloudWatch Logs not-ingesting scenario through the
thirteen-category diagnostic tree.

## What it does

Reads a symptom description (agent / application / aws logs error
string, observed behaviour, "logs stopped at 03:00") plus the log
group configuration, then walks the symptom-driven diagnostic tree
to a root cause with positive evidence:

1. **Pre-flight** — log group configuration (`describe-log-groups` —
   retention, kmsKeyId, dataProtectionPolicy), latest log streams
   (`describe-log-streams`), recent events (`get-log-events`),
   subscription filters (`describe-subscription-filters`), metric
   filters (`describe-metric-filters`), data protection policy
   (`get-data-protection-policy`), AWS Health (regional incidents).
2. **Symptom entry** — map the error to one of: log group naming,
   IAM permissions, sequence token, agent misconfig, VPC Flow Logs
   delivery, Lambda auto-create, retention expired, subscription
   filter capacity, metric filter pattern, resource policy conflict,
   data protection blocking, cross-account delivery.
3. **Layer-specific probes** —
   - IAM: `iam simulate-principal-policy` for `logs:CreateLogGroup`,
     `logs:CreateLogStream`, `logs:PutLogEvents` on the log group
     ARN.
   - Sequence token: `describe-log-streams` `uploadSequenceToken`;
     check for concurrent writers sharing a stream.
   - Agent: agent config file (`file_path`, `log_stream_name`,
     `multi_line_start_pattern`); Windows path vs Linux path;
     `CloudWatchAgentServerPolicy` attachment.
   - VPC Flow Logs: `ec2 describe-flow-logs` (`FlowLogStatus`,
     `DeliverLogsPermissionArn`); account for the 10-minute
     aggregation window.
   - Lambda auto-create: `lambda get-function-configuration` role;
     `simulate-principal-policy` for `logs:CreateLogGroup`.
   - Retention: `describe-log-groups` `retentionInDays`.
   - Subscription filter: `describe-subscription-filters`; Lambda
     `ConcurrentExecutions` and `Throttles` for the destination;
     2x account-concurrency budget.
   - Metric filter: `describe-metric-filters`; test the pattern with
     `filter-log-events`.
   - Data protection: `get-data-protection-policy` on the log group.
   - Cross-account: `describe-resource-policies` / `describe-destinations`
     on the destination account.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that
   matches the symptom) or INSUFFICIENT_DATA (a probe requires
   operator input).

Emits a deterministic diagnostic block per target:

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
```

## When to invoke

Paste a symptom description and ask any of:

- "Lambda function has no CloudWatch Logs"
- "CloudWatch agent not shipping logs"
- "PutLogEvents returns InvalidSequenceTokenException"
- "VPC Flow Logs not arriving in the log group"
- "logs stopped appearing at 03:00"
- "cross-account log delivery not working"
- "metric alarm not firing despite errors in the log group"
- "subscription Lambda is dropping batches"

A bare log group name + any not-ingesting verb ("no logs",
"logs missing", "logs stopped") also routes here via the orchestrator.

## Inputs

- Symptom description: error string, observed behaviour,
  intermittent vs persistent pattern, the emitter source
  (application / Lambda / VPC Flow Logs / CloudWatch agent /
  ECS firelens).
- Log group context: log group name, expected log stream pattern,
  emitter IAM principal.
- For live-account diagnosis: the emitter IAM principal, the log
  group ARN, and (for cross-account) the source and destination
  account IDs. The skill uses `describe-log-groups`,
  `describe-log-streams`, `get-log-events`, `describe-subscription-filters`,
  `describe-metric-filters`, `get-data-protection-policy`,
  `describe-resource-policies`, `describe-destinations`,
  `iam simulate-principal-policy`, `cloudtrail lookup-events`,
  `ec2 describe-flow-logs`, `lambda get-function-configuration`.

## Outputs

- One diagnostic block per target log group.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: IAM policy edit, agent config fix, retention
  raise, subscription filter reconfiguration, metric filter pattern
  fix, resource-policy add for cross-account, or AWS Support
  escalation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for CloudWatch Logs
  not-ingesting scenarios).
- `/aws:audit-cloudwatch-logs-retention` for retention posture audits
  across log groups.
- `/aws:troubleshoot-cloudwatch-logs-insights` for Logs Insights query
  failures (syntax, timeouts) rather than ingestion failures.
- `/aws:troubleshoot-cloudwatch-alarm` for alarm-not-firing scenarios
  rooted in the alarm configuration rather than the metric filter.
