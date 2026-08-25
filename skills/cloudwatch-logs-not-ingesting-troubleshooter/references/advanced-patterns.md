# Advanced Patterns (load on demand) — CloudWatch Logs Not-Ingesting Troubleshooter

Senior-operator behaviours, Step 0 non-obvious behaviours, the per-layer remediation summary, and recent AWS feature notes moved verbatim from SKILL.md. Loaded on demand.

---

## Philosophy — four senior-operator behaviours (moved from SKILL.md)

Four behaviours separate a senior CloudWatch engineer from a generalist:

- **The sequence token is per-stream and per-call.** Each PutLogEvents
  call (after the first) must include the `sequenceToken` returned by
  the previous successful call to the same log stream. The token
  serialises writes; two concurrent emitters writing to the same
  stream will collide, each seeing the other's token as stale. The
  fix is one writer per stream, or per-stream tokens refreshed before
  every write.
- **The Lambda log group is auto-created on first invocation — but
  only if the execution role allows `logs:CreateLogGroup`.** If the
  role lacks `logs:CreateLogGroup`, the first invocation silently
  drops logs (the function runs, but no log group is created and no
  error is surfaced in the function response). Operators who "see no
  Lambda logs" on a newly-deployed function almost always have a
  role missing `logs:CreateLogGroup` or `logs:CreateLogStream`.
- **Retention expires log streams silently.** A retention policy of
  `7 days` deletes log streams older than 7 days without a CloudTrail
  event (the deletion is internal to CloudWatch). Operators who "lost
  last week's logs" almost always had a retention policy shorter than
  they thought, or someone lowered the retention window.
- **Cross-account delivery is gated by the destination's resource
  policy, not by the source's IAM.** The source account's emitter
  needs `logs:PutLogEvents` in its IAM policy, but the destination
  account's log group must also have a resource-based policy
  permitting the source account. Operators who "added IAM on the
  source" but still see cross-account delivery fail always missed
  the destination-side policy.
---

## Step 0: Non-obvious behaviours that change diagnosis (moved from SKILL.md)

- **The sequence token must come from the previous PutLogEvents
  response.** Each call (after the first) must include the
  `sequenceToken` returned by the prior successful call to the same
  log stream. A stale or cached token produces
  `InvalidSequenceTokenException`. The token serialises writes; two
  concurrent emitters writing to the same stream will collide.
- **Lambda auto-creates the log group on first invocation only if the
  role allows it.** The Lambda service principal attempts to create
  `/aws/lambda/<name>` on the first invocation. If the execution role
  lacks `logs:CreateLogGroup`, the creation silently fails (no error
  in the function response) and subsequent invocations continue to
  drop logs.
- **Retention deletes log streams silently, without a CloudTrail
  event.** The deletion is internal to CloudWatch Logs; CloudTrail
  does not record individual stream expirations. Operators who "lost
  logs but see no DeleteLogStream event" almost always had retention
  expiry, not a malicious deletion.
- **Subscription filters share the account's Lambda concurrency
  budget.** Each subscription invokes its Lambda destination once per
  batch. Lambda subscriptions are subject to a per-account reservation
  of up to 2x the account's concurrent-invocations quota for
  subscription deliveries; a fan-out across several filters can
  exhaust the budget and silently drop batches.
- **Cross-account delivery needs a resource policy on the destination
  log group.** The destination account must attach a resource-based
  policy to the destination log group (or use a CloudWatch Logs
  destination with `put-destination-policy`) granting the source
  account `logs:PutLogEvents`. IAM alone on the source side is not
  sufficient.
- **Metric filter patterns are tested against the raw event message,
  not JSON.** A metric filter pattern like `{ $.status = 500 }` only
  matches if the log event is valid JSON with a `status` field. A
  text-formatted log line (`[ERROR] 500 ...`) will not match; the
  filter silently produces zero metric points.
- **Data protection policies redact at ingestion time.** An account-
  level data protection policy on the log group replaces sensitive
  data patterns (e.g., AWS access keys, email addresses) with
  `{{REDACTED}}` as events are ingested. Operators who "see
  `{{REDACTED}}` in CloudWatch Logs" almost always have a data
  protection policy active on the group.
- **CloudWatch agent `log_stream_name` defaults to `{instance_id}`.**
  A wrong `log_stream_name` template (e.g., a hardcoded string
  shared across hosts) causes concurrent writes to the same stream
  and sequence-token collisions. Use `{instance_id}` or `{hostname}`
  for one-stream-per-host.
---

## Remediation guidance summary (moved from SKILL.md)

Each layer's fix is summarised below; the step sections above carry
the full probe commands and worked examples.

| Layer | Fix |
|---|---|
| LOG_GROUP_NAMING | Align the source's configured log group name with what the operator queries. Lambda: `/aws/lambda/<name>`. API Gateway: `API-Gateway-Execution-Logs_<id>/<stage>`. Agent: as configured in `logs.log_group_name`. |
| LOG_STREAM_NAMING | Use `{instance_id}` or `{hostname}` for one-stream-per-host; include `{task_id}` for ECS tasks. Never share a stream across concurrent writers. |
| IAM_PERMISSIONS | Add the missing action on the log group ARN: `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`. For Lambda, attach `AWSLambdaBasicExecutionRole`. |
| SEQUENCE_TOKEN | One writer per stream; refresh the token from `describe-log-streams` (or the prior PutLogEvents `nextSequenceToken`) before every write. |
| AGENT_MISCONFIG | Correct `logs_create_log_stream`, `log_stream_name`, `file_path`, `multi_line_start_pattern`. Restart the agent (`amazon-cloudwatch-agent-ctl -a start`). Verify the agent IAM role has `CloudWatchAgentServerPolicy`. |
| VPC_FLOW_LOGS_DELIVERY | Verify `describe-flow-logs` shows `FlowLogStatus: ACTIVE`; check the `DeliverLogsPermissionArn` role has `logs:PutLogEvents`. Account for the 10-minute aggregation window. |
| LAMBDA_AUTO_CREATE | Attach `AWSLambdaBasicExecutionRole` (or add `logs:CreateLogGroup`) to the execution role. Re-invoke to trigger auto-creation. |
| RETENTION_EXPIRED | Raise retention: `aws logs put-retention-policy --log-group-name <group> --retention-in-days <new>`. Expired logs are not recoverable. |
| SUBSCRIPTION_FILTER_CAPACITY | Provision reserved concurrency for the Lambda destination; reduce fan-out; or switch the destination to Kinesis for higher throughput. |
| METRIC_FILTER_PATTERN | Correct the pattern to match the log format. JSON events: `{ $.status = 500 }`. Text events: `ERROR 500` (term-based). Verify with `filter-log-events`. |
| RESOURCE_POLICY_CONFLICT | Resolve conflicts between resource policies on the log group (e.g., explicit deny overriding allow). Read with `describe-resource-policies`; merge carefully. |
| DATA_PROTECTION_BLOCKING | Surface the policy; coordinate with the security owner before disabling or narrowing the pattern set. |
| CROSS_ACCOUNT_POLICY | Add a resource-based policy on the destination log group granting the source account `logs:PutLogEvents`; or use `put-destination` / `put-destination-policy` for the destination pattern. |
---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **CloudWatch Logs data protection (2024-2025):** Account-level and log-group-level data protection policies redact sensitive patterns at ingestion. Operators may see `{{REDACTED}}` and mistake it for a formatting bug; check `get-data-protection-policy`.
- **Subscription filter account-concurrency budget (2024-2025):** Lambda subscription deliveries are capped at 2x the account's concurrent-invocations quota. A fan-out across several filters can silently drop batches under sustained load.
- **CloudWatch agent unified config (2024):** The agent's JSON config now supports `multi_line_start_pattern` with regex; older literal patterns silently break on stack traces.
- **VPC Flow Logs aggregation intervals (2024):** 1-minute intervals are now generally available; the default remains 10 minutes. Operators who "see no flow logs for 10 minutes" may be on the default.
- **CloudWatch Logs KMS-by-customer-key enforcement (2024-2025):** Some accounts have SCPs requiring CMK encryption for log groups; `associate-kms-key` must run at creation or before the first write.
