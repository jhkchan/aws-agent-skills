# Advanced Patterns (load on demand) — CloudWatch Logs Retention Auditor

Expert-knowledge deep dive (Step 0), edge-case catalog, and recent AWS features moved verbatim from SKILL.md. Load on demand when the audit input hits a non-mainline path.


---

## Step 0: Expert knowledge — non-obvious CloudWatch Logs behaviors (moved from SKILL.md)

These behaviors change a verdict if ignored. Each is load-bearing:

- **`retentionInDays` absence is the default for new log groups.**
  Unlike S3 lifecycle rules or CloudTrail retention, CloudWatch Logs
  does NOT apply a default retention. New groups remain Never-expire
  until you explicitly call `PutRetentionPolicy`. Operators assume a
  "default sane retention" exists — it does not.

- **Retention changes apply only to NEW events.** Setting retention
  from Never to 30 days does NOT immediately delete existing logs.
  Existing events expire on the schedule they were originally written
  under; only events received AFTER the `PutRetentionPolicy` call are
  bound by the new retention. For incident response, shortening
  retention does not cleanse historical data — you must delete log
  streams or the log group itself.

- **SSE-KMS CMK is a paid feature with hidden cost.** Associating a
  CMK via `AssociateKmsKey` causes every `PutLogEvents` batch to
  trigger a `kms:GenerateDataKey` call. At $0.03 per 10,000 KMS
  requests, a high-volume group emitting 1,000 batches/sec accrues
  ~$8,000/month in KMS charges alone — frequently more than the
  CloudWatch Logs ingestion charge itself.

- **The default service-managed SSE is NOT `aws/logs` AWS-managed.**
  Unlike S3 (`aws/s3`) or EBS (`aws/ebs`), CloudWatch Logs does not
  expose an AWS-managed CMK in the customer account. The default is
  a CloudWatch-internal service key that never appears in
  `aws kms list-keys`. Therefore "no `kmsKeyId`" cannot be remediated
  by "switch to AWS-managed key" — the only CMK path is customer-
  managed.

- **Subscription filter quota is 2, not unlimited.** A common
  misconfiguration chains Logs → Lambda → Logs (cross-region) →
  Firehose → S3, where each hop consumes a slot. The third filter on
  the same source fails at `PutSubscriptionFilter` time, but producers
  continue writing logs unaware the fan-out is silently incomplete.

- **Metric filters do not backfill.** A filter processes only events
  received AFTER creation. Adding an "ERROR" counter today produces
  no historical baseline. Always pair with a CloudWatch Logs Anomaly
  Detector if retroactive signal is needed.

- **Metric filter pattern syntax is CloudSearch-style, not regex.**
  Complex patterns cost more per-GB to evaluate. The cheapest pattern
  is a literal token (`"ERROR"`); multi-field `[..., ...]` patterns
  with anchoring/alternation are most expensive. For high-volume
  groups, prefer two cheap filters over one complex filter.

- **Anomaly Detectors require a 2-week baseline.** A newly-created
  detector returns `Status: TRAINING` for ~14 days, during which it
  produces no findings. A less-than-2-week-old group has no meaningful
  anomaly detection even with a detector configured. Treat as
  CONFIG_GAP, not OK.

- **Cross-account subscription filters use a destination, not the
  filter itself.** The recipient account creates a
  `aws logs put-destination` + destination policy; the sender's filter
  targets the destination ARN. The destination policy IS the security
  boundary — a permissive policy allows any sender account to write
  to the recipient's Kinesis/Lambda. Always audit destination
  policies alongside subscription filters.

- **`describe-log-groups --log-group-name-prefix` is a PREFIX match,
  not a wildcard.** `/aws/lambda` matches `/aws/lambdaFoo` and
  `/aws/lambda-prod`. For exact-match, omit `--log-group-name-prefix`
  and pass `--log-group-name` (CLI v2 only).

- **`storedBytes` is monotonic.** Never decreases — not on retention
  expiry, not on `DeleteLogStream`. The only reset is `DeleteLogGroup`.

- **Insights queries bill per-GB-scanned, not per-query.** A
  `fields @timestamp, @message | filter level == "ERROR"` query on a
  100 GB group costs the same as a `stats count(*)` query — both scan
  the full time-range selection. Long retention + high volume =
  compounding query cost.

- **PutLogEvents batch limits: 1 MB and 10,000 events per batch.**
  Producers exceeding these limits receive
  `DataAlreadyAcceptedException` or throttling. Not a verdict driver,
  but high `storedBytes` growth with these errors suggests the
  producer needs better batching or stream sharding.

- **Log group KMS key region must match the log group region.**
  Multi-Region KMS keys are supported, but the in-region replica ARN
  must be referenced — the primary ARN from another region is
  rejected at `AssociateKmsKey` time.

- **Log group names cannot be renamed.** "Renaming" requires creating
  a new group, re-pointing the producer, and accepting that historical
  logs remain under the old name. A Never-expire group with a misnamed
  producer is doubly expensive — you cannot migrate cheaply.

- **Log group ARN suffix `:*` is required for resource-level IAM
  permissions.** `arn:aws:logs:<region>:<account>:log-group:<name>:*`
  matches stream-scoped actions (PutLogEvents, GetLogEvents,
  DeleteLogStream). Without `:*`, identity-based policies targeting
  the ARN will NOT match — the most common IAM policy error for
  CloudWatch Logs.

- **`AssociateKmsKey` is NOT retroactive.** When you associate a CMK
  on an existing log group, only events received AFTER the association
  are encrypted with the CMK. Existing events remain under the prior
  service-managed key — there is no re-encryption API. For
  compliance-mandated CMK coverage, you must rotate the underlying
  data (delete log streams after verifying CMK coverage is in place
  for new events) or migrate to a new CMK-associated group.

- **CloudFormation `AWS::Logs::LogGroup` without `RetentionInDays`
  creates a Never-expire group silently.** Unlike console-created
  groups (which at least surface the retention field), IaC templates
  that omit the property produce no warning — the stack succeeds and
  the group begins accumulating immediately. This is the dominant
  source of Never-expire groups in IaC-managed accounts. Always
  require `RetentionInDays` as a stack-level parameter or use a
  CloudFormation hook (rule `cloudwatch-logs-retention-set`) to fail
  the stack on omission.

- **`PutRetentionPolicy` is throttled at 5 requests/sec/account.**
  Bulk remediation across thousands of groups needs exponential
  backoff or the CLI returns `ThrottlingException`. The same cap
  applies to `AssociateKmsKey`, `PutMetricFilter`, and
  `PutSubscriptionFilter` — all control-plane mutations share the
  CloudWatch Logs account-level rate limit.

- **Lambda subscription filters without `DeadLetterConfig` silently
  drop failed invocations.** A Lambda fan-out that errors (exception,
  timeout, payload-too-large) is retried twice then dropped — without
  a DLQ, the drop has no metric and no alarm. For audit trails that
  must not lose events, always pair the subscription filter with a
  DeadLetterConfig (an SQS ARN); treat its absence as an additive
  finding when the subscription filter is on a security-relevant
  group.

- **CloudWatch Logs Anomaly Detectors bill per-detector-hour
  (~$0.15/detector/day, ~$4.50/detector/month at ONE_MIN frequency).**
  Adding a detector to every group in a 1,000-group account accrues
  ~$4,500/month in detector charges alone — sometimes more than the
  logs themselves. Reserve anomaly detectors for groups with
  operational or security signal, not for low-volume debug groups.

---

## Edge-case handling (moved from SKILL.md)

- **`retentionInDays: 0` literal.** The API never returns 0; absence is
  the Never-expire signal. If a snapshot shows `retentionInDays: 0`, the
  snapshot is hand-edited or stale — treat as NO_RETENTION and note.

- **AWS service-created log groups** (`/aws/lambda/<function>`,
  `/ecs/<cluster>/<task>`, `AWSChatBot/<account>`). AWS services
  auto-create these on first PutLogEvents with NO retention. They
  silently accumulate until audited. Apply the same Step 1 logic —
  origin does not exempt them.

- **OpenSearch subscription filter (formerly Elasticsearch).** The
  subscription-to-OpenSearch integration can bypass the 2-per-group
  quota rule in some legacy configurations — flag any group with > 2
  subscription filters as an anomaly.

- **`kmsKeyId` referencing a deleted key.** If the CMK is in
  `PendingDeletion` state, PutLogEvents fails immediately. Treat as
  NO_ENCRYPTION (effectively unusable) and note the deleted-key state.

- **Metric filter with pattern `""` (empty).** Matches every event —
  effectively a no-op that inflates metric count. Flag as a CONFIG_GAP
  sub-finding (filter exists but is non-functional).

- **Subscription filter on a Never-retention group.** Double cost driver
  (storage + Lambda invocation). First-fail-wins verdict is still
  NO_RETENTION; surface the Lambda fan-out as an additive HIGH finding.

- **Anomaly Detector in `TRAINING` status.** Treat the group as not-yet-
  observable for anomaly purposes — verdict CONFIG_GAP with REMEDIATION
  noting "wait 14 days for baseline".

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **CloudWatch Logs Infrequent Access log class (2024):** Logs now supports an `STANDARD` vs `INFREQUENT_ACCESS` log class. Auditors should verify that high-volume, low-query log groups (e.g., VPC Flow Logs, audit trails) are assigned to the Infrequent Access class for cost optimization, and that the log class is intentional — not silently defaulted.
- **Account-level data protection policies (2024):** CloudWatch Logs now supports account-level data protection policies that mask sensitive data (PII, credentials) in log events. Auditors should verify that data protection policies are enabled, especially for log groups ingesting application logs that may contain PII.
- **CloudWatch Logs data lifecycle (2025):** Integrated lifecycle management that can transition logs to S3, Glacier, or delete based on policies. Auditors should check whether the lifecycle policy aligns with compliance retention requirements.
- **Subscription filter improvements (2024):** Enhanced subscription filter support with Kinesis Data Firehose destination and cross-account delivery. Auditors should verify that subscription filter fan-out does not create silent data-loss vectors when destinations are misconfigured.
