# Advanced patterns - SNS Topic Public Subscription Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Step 0: Expert knowledge — non-obvious SNS behaviours that change classification

These behaviours are easy to misjudge without operational SNS experience.
Each changes a verdict if ignored:

- **`sns:Subscribe` is push-based, not pull-based.** Unlike SQS where the
  attacker must actively poll, SNS pushes messages to the subscriber
  endpoint on every publish. A `Principal: "*"` with `sns:Subscribe` means
  anyone can register an HTTPS endpoint and passively receive every message
  without further action. This is worse than an SQS queue with public read —
  the attacker sets up once and collects data automatically. Do NOT
  downplay wildcard Subscribe as "they still need to confirm" — confirmation
  is a one-time step, not an ongoing barrier.

- **Subscription confirmation has a 3-day token expiry, but the subscription
  remains in `PendingConfirmation` state.** The confirmation token expires
  after 3 days, but the subscription record persists in
  `PendingConfirmation` indefinitely. These zombie subscriptions pollute the
  subscription list and are invisible in delivery metrics. When auditing
  cross-account subscriptions, filter on `Status: Confirmed` — pending
  subscriptions do not receive messages but still count against the
  subscription quota.

- **FIFO topics ONLY support SQS FIFO queues as subscribers.** An HTTP,
  HTTPS, email, SMS, application (mobile push), or Lambda subscription on a
  FIFO topic is impossible — SNS rejects the subscribe call. If the metadata
  shows a FIFO topic with non-SQS subscriptions, the input is stale or from
  a data-migration artifact. Do NOT flag this as a security issue; flag it
  as a data inconsistency.

- **`ContentBasedDeduplication` is a two-layer dedup system.** If the topic
  has `ContentBasedDeduplication: true`, SNS computes a SHA-256 hash of the
  message body and deduplicates within a 5-minute window. If `false`, the
  publisher MUST send a `MessageDeduplicationId` on every message. If both
  are absent, SNS delivers duplicate messages with identical content within
  the dedup window — silently breaking the exactly-once guarantee that is
  the sole reason to use a FIFO topic.

- **Delivery status logging is per-protocol, not global.** SNS requires
  setting delivery logging SEPARATELY for each protocol category: HTTP/HTTPS
  (`HTTPSuccessFeedbackRoleArn` / `HTTPFailureFeedbackRoleArn`), SQS
  (`SQSSuccessFeedbackRoleArn` / `SQSFailureFeedbackRoleArn`), Lambda /
  Application (`ApplicationSuccessFeedbackRoleArn` /
  `ApplicationFailureFeedbackRoleArn`). A common mistake is configuring
  HTTP logging but not SQS, leaving SQS delivery failures invisible.

- **Delivery status logging requires a CloudWatch Logs resource policy.**
  SNS needs `logs:CreateLogStream` and `logs:PutLogEvents` on the log group.
  Without this resource policy, SNS silently fails to write delivery logs
  even if the topic has the feedback role configured. The logging appears
  "enabled" in topic attributes but produces no CloudWatch data. Always
  check both the topic attribute AND the CloudWatch log resource policy.

- **AWS-managed key (`alias/aws/sns`) blocks cross-account delivery.** The
  AWS-managed SNS key policy only allows the owning account to decrypt. If a
  topic uses `alias/aws/sns` and has cross-account SQS subscribers, those
  subscribers cannot decrypt the message body — the delivery silently fails
  with a KMS error that appears in delivery logs (if configured) but not in
  the subscriber's queue. Cross-account SNS requires a customer-managed key
  with the subscriber account granted `kms:Decrypt` and
  `kms:GenerateDataKey*` in the key policy.

- **`aws:SourceOwner` is SNS-specific.** This condition key is set by the
  SNS service itself and identifies the account that owns the resource
  making the request. It is SNS's native equivalent of
  `aws:SourceAccount`. Use `aws:SourceOwner` for SNS topic policies — it is
  more reliable than `aws:SourceAccount` for SNS because SNS guarantees it
  is set on every request.

- **`sns:PublishBatch` dedup is per-message, not per-batch.** A batch
  publish of 10 messages on a FIFO topic requires a
  `MessageDeduplicationId` per entry (if topic-level dedup is off). If the
  publisher sends the same dedup ID for all 10 entries, SNS delivers only
  the first and silently drops the other 9 as duplicates — even if the
  payloads differ (dedup is on the ID, not the content, when
  ContentBasedDeduplication is false).

- **Topic policy size limit is 30 KiB** (not 6 KiB like IAM managed policies
  or 32 KiB like KMS key policies). A topic policy with many statements can
  hit this cap and `SetTopicAttributes` fails with `InvalidParameter`. When
  proposing additive Deny statements, estimate cumulative size.

- **`NotPrincipal` in a topic policy Allow statement** grants access to
  every principal EXCEPT the listed one — the inverse of intended scope.
  Treat any `NotPrincipal` in an Allow as WILDCARD (equivalent to
  `Principal: "*"`).

- **`NotAction` in an Allow statement** grants every SNS action EXCEPT the
  listed ones. Treat as DATA_CONTROL (worst case: covers Subscribe + Publish
  + SetTopicAttributes + DeleteTopic).

## Edge-case handling

- **`Principal: "*"` with `aws:SourceOwner` condition.** The condition is
  STRONG (SNS-specific, set by the service). Downgrade from
  PUBLIC_SUBSCRIPTION to CONFIG_GAP — the exposure is scoped to the named
  account but remains fragile (a policy edit could widen it).

- **AWS-managed key with cross-account subscribers.** The topic is
  encrypted (OK for Step 2), but cross-account SQS subscribers cannot
  decrypt. This is a CONFIG_GAP — delivery silently fails for cross-account
  subscribers. The fix is to switch to a customer-managed key whose policy
  grants `kms:Decrypt` + `kms:GenerateDataKey*` to the subscriber accounts.

- **FIFO topic with zero subscriptions.** FIFO dedup is still evaluated
  (Step 4) — the topic may receive subscribers later. A FIFO topic with
  `ContentBasedDeduplication: false` is a CONFIG_GAP regardless of current
  subscription count.

- **Topic policy with Deny on `aws:SecureTransport: false`.** A Deny that
  blocks non-HTTPS access does NOT cancel a wildcard Subscribe Allow — it
  only enforces TLS. The wildcard subscription is still PUBLIC_SUBSCRIPTION;
  the Deny is defense-in-depth (good practice, but does not remediate the
  exposure).

- **Empty topic policy (no statements).** A topic with an empty `Statement`
  array means no external principal can publish or subscribe — only the
  topic owner (via IAM) has access. This is OK for the policy dimension
  (same-account access is governed by IAM). Not an error.

- **Standard topic with `ContentBasedDeduplication` attribute present.**
  Standard topics ignore dedup attributes. Do NOT flag this — the attribute
  is harmless on a standard topic and is often left over from a topic-type
  migration.

## Deep reference: SNS internals

### Delivery retry semantics

SNS retries HTTP/HTTPS delivery up to **4 hours** (100,010 delivery
attempts with exponential backoff: 20s, 20s, 20s, 20s, 20s, 30s, ...). After
the retry budget is exhausted, the message is silently dropped. SQS,
Lambda, and Application protocols do NOT retry — delivery is a single
attempt (success or failure). FIFO topics deliver to SQS FIFO queues with
exactly-once semantics (if dedup is configured correctly).

### Subscription confirmation flow

When `sns:Subscribe` is called, SNS sends a confirmation token to the
endpoint. The endpoint must confirm within **3 days**. After confirmation,
the subscription is `Confirmed`. If unconfirmed, it stays in
`PendingConfirmation` indefinitely — the subscription record exists, counts
against the quota, but does not receive messages. For cross-account
subscriptions, only the subscriber account can confirm.

### Topic policy vs IAM policy intersection

- **Same-account access:** EITHER the topic policy OR the caller's IAM
  policy must allow the action (union). A same-account caller with IAM
  `sns:Publish` can publish even if the topic policy does not list them.
- **Cross-account access:** BOTH the topic policy AND the caller's IAM
  policy must allow the action (intersection). The topic policy is the
  resource-owner's gate; the IAM policy is the caller's gate.

This means an empty topic policy does NOT block same-account access (IAM is
sufficient) but DOES block all cross-account access.

### FIFO throughput quota

FIFO topics are rate-limited to **300 messages per second** (or 10 MB/s
aggregate). Exceeding this quota results in throttling (HTTP 429), not
queuing. Standard topics have effectively unlimited throughput. Batch
publish (`PublishBatch`) sends up to 10 messages per API call, but the
aggregate rate limit still applies.

## Recent AWS features (2024-2026)

- **SNS message data protection (2024):** SNS now provides message data protection policies that can detect and block sensitive data (PII, financial data) in published messages. Auditors should verify that data protection policies are enabled on topics processing user-generated content.
- **FIFO topic delivery status logging (2024-2025):** Enhanced delivery status logging for FIFO topics. Auditors should verify that delivery status logging is enabled — FIFO topics with missing delivery status logging can silently lose messages.
- **Cross-region delivery improvements (2024):** SNS cross-region message delivery via AWS X-Ray tracing integration. No new audit-surface fields, but auditors should verify that cross-region SNS subscriptions have appropriate DLQs.
- **SNS-to-SQS SSE-KMS consistency requirement (2024):** SNS topics and SQS subscriptions must use compatible KMS keys for SSE-KMS. Auditors should verify that the topic KMS key policy grants `kms:Decrypt` to the SQS queue's consumer role.

