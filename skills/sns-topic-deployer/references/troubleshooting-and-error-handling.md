# Troubleshooting and Error Handling — SNS Topic Deployer

Subscription troubleshooting decision tree, per-protocol error handling,
and edge-case scenarios. Loaded on demand when diagnosing message delivery
failures or resolving deployment edge cases.

## Subscription troubleshooting decision tree

Use this tree after `publish` returns success but a subscriber reports
missing messages. Read top-to-bottom; **first match wins**. Every branch
ends in a single CLI command that confirms or rules out the cause.

```
START: A publish succeeded (MessageId returned) but a subscriber
       reports no message. Which subscriber type?

├── HTTP / HTTPS endpoint
│   ├── Is the subscription ARN in PendingConfirmation?
│   │   ├── YES → Endpoint never confirmed the SubscriptionConfirmation
│   │   │         token (3-day expiry). Fix: re-subscribe, then have the
│   │   │         endpoint GET the SubscribeURL programmatically.
│   │   │         aws sns get-subscription-attributes --subscription-arn <arn>
│   │   │         → look for "Status": "PendingConfirmation"
│   │   └── NO  → Did the endpoint return 2xx within 15s?
│   │       ├── NO (4xx/5xx or timeout) → SNS retries for 4 hours then drops.
│   │       │   Check delivery-failure logs:
│   │       │   aws logs filter-log-events --log-group-name sns/<region>/<acct>/<topic>/Failure
│   │       │   ├── 403 → endpoint auth rejected SNS POST. Fix signature validation.
│   │       │   ├── 404 → wrong endpoint URL. Re-subscribe.
│   │       │   ├── 500 → endpoint crashed. Add subscription DLQ.
│   │       │   └── timeout → endpoint too slow (SNS times out at 15s).
│   │       └── YES (2xx) but subscriber reports missing
│   │           → message acked but not processed. Endpoint-side bug.
│   │           Check delivery-SUCCESS logs to confirm SNS delivered.
│
├── Lambda subscriber
│   ├── Is the subscription in PendingConfirmation? (rare for same-account)
│   │   └── YES → confirm from the subscriber account:
│   │           aws sns confirm-subscription --topic-arn <topic> --token <token>
│   ├── Did the Lambda invocation fail? (async, 2 retries)
│   │   ├── YES → check Lambda on-failure destination. If none configured,
│   │   │   message is lost after 2 retries. Fix: configure on-failure to SQS DLQ.
│   │   └── NO  → Lambda received but did not process. Application bug;
│   │           check CloudWatch Logs.
│   └── Messages duplicated?
│       └── Retry storm. Use SQS subscription with Lambda event-source
│           mapping instead — SQS provides visibility-timeout dedup.
│
├── SQS subscriber
│   ├── Is subscription PendingConfirmation?
│   │   └── YES → cross-account SQS requires manual confirm. Queue policy
│   │           must grant SNS SendMessage BEFORE confirm.
│   ├── Queue empty but SNS shows delivery success?
│   │   ├── Check queue KMS key: does it grant SNS kms:GenerateDataKey*?
│   │   │   aws kms get-key-policy --key-id <queue-key> --policy-name default
│   │   ├── Check queue policy: does it grant SNS sqs:SendMessage?
│   │   │   aws sqs get-queue-attributes --queue-url <url> --attribute-names Policy
│   │   └── Check filter policy: non-matching attribute silently drops?
│   │       aws sns get-subscription-attributes --subscription-arn <arn>
│   └── Messages duplicated?
│       └── Multiple subscriptions from same queue to same topic.
│           De-duplicate; SNS does not prevent duplicate subscriptions.
│
├── Mobile push (application protocol)
│   ├── Endpoint disabled? SNS disables endpoints after token rejection.
│   │   aws sns get-endpoint-attributes --endpoint-arn <arn>
│   │   → "Enabled": "false" → re-register device token.
│   └── Token valid but no delivery? Check platform credential:
│       APNS cert expiry, FCM server-key rotation.
│
└── Email subscriber
    ├── PendingConfirmation?
    │   └── Recipient never clicked SubscribeURL (3-day expiry).
    │         No programmatic bypass without the token.
    └── Confirmed but not delivered?
        └── Email deliverability issue (spam, bounce). Check SES metrics.
```

**Quick triage sequence** (run when subscriber type is unknown):

```bash
# 1. Was the message published?
aws sns get-topic-attributes --topic-arn <arn> \
  --query 'Attributes.DeliveryStatusSr.Notification'

# 2. Is the subscription confirmed?
aws sns list-subscriptions-by-topic --topic-arn <arn> \
  --query 'Subscriptions[?Endpoint==`<endpoint>`].{Status:SubscriptionArn}'

# 3. Did SNS attempt delivery? (delivery logging must be enabled)
aws logs filter-log-events \
  --log-group-name sns/<region>/<account>/<topic>/Failure \
  --filter-pattern <message-id>

# 4. Is there a subscription DLQ catching failures?
aws sns get-subscription-attributes --subscription-arn <arn> \
  --query 'Attributes.RedrivePolicy'
```

## Per-protocol subscription error handling

Each SNS subscription protocol has distinct failure semantics.

### HTTP / HTTPS

- **Retry budget:** SNS retries for up to 4 hours (100,010 attempts) with
  exponential backoff.
- **Failure detection:** endpoint returns 4xx/5xx, times out at >15s, or
  refuses connection.
- **Required mitigation:** attach subscription-level DLQ via RedrivePolicy.
  Without one, message is silently dropped after retries.
- **Recommended:** return HTTP 429 under load — SNS interprets as "back off."
  Avoid returning 200 to a message you cannot process — SNS will not retry.
- **Signature validation:** ensure endpoint accepts both SignatureVersion=1
  and SignatureVersion=2. Mismatch causes spurious 403 responses.

### Lambda

- **Retry budget:** Lambda async retries **2 times** on top of SNS delivery.
  SNS considers delivery successful once Lambda acks the async invocation.
- **Required mitigation:** configure Lambda on-failure destination
  (SQS/SNS/EventBridge), NOT the SNS subscription DLQ. The subscription
  DLQ only catches SNS-to-Lambda delivery failures (rare).
- **Duplicate invocations:** SNS-to-Lambda does NOT deduplicate. For
  exactly-once semantics, use SQS subscription with Lambda event-source
  mapping.

```bash
aws lambda put-function-event-invoke-config \
  --function-name order-handler \
  --maximumretry-attempts 2 \
  --destination-config '{"OnFailure":{"Destination":"arn:aws:sqs:us-east-1:222222222222:lambda-failure-dlq"}}'
```

### SQS

- **Retry budget:** SNS delivers once; SQS visibility-timeout and redrive
  policy handle downstream retries.
- **Failure detection:** queue empty after successful publish with delivery-
  success logged — usually KMS decrypt failure or queue policy issue.
- **Required mitigation:** configure SQS DLQ via the queue's RedrivePolicy,
  NOT the SNS subscription DLQ. They operate at different layers.
- **Message retention:** SQS retains messages for 4 days by default
  (configurable up to 14 days). Set `MessageRetentionPeriod` to match
  recovery SLA.

### Mobile push (application)

- **Retry budget:** SNS retries per platform policy. APNS retries
  immediately; FCM uses exponential backoff. Failed endpoints auto-disabled.
- **Failure detection:** endpoint shows `Enabled=false`. Delivery-failure
  logs show platform response (BadDeviceToken, Unregistered).
- **Required mitigation:** subscribe endpoints via topic and attach
  subscription DLQ. Direct-push failures are silent.
- **Token lifecycle:** device tokens rotate. Periodic job to re-call
  `create-platform-endpoint` with fresh tokens.

### Email / Email-JSON

- **Retry budget:** none. SNS sends once; if SMTP rejects, message is lost.
- **Required mitigation:** none at SNS layer. For reliable notifications,
  prefer SQS or HTTPS subscriptions. Treat SNS email as best-effort.
- **Confirmation required:** recipient must click SubscribeURL within 3
  days. No programmatic bypass without the token.

## Edge-case handling

### SNS-to-SQS subscription with SSE-KMS

Both the SNS topic and the SQS queue may use SSE-KMS. The SNS topic's KMS
key must be usable by SNS, and the SQS queue's KMS key must grant SNS
`kms:GenerateDataKey*` and `kms:Decrypt`. Common cross-service encryption
failure: messages published but never arrive in the SQS queue.

### FIFO topic to FIFO SQS subscription

Supported, but the SQS FIFO queue must have its own deduplication configured.
If the topic has `ContentBasedDeduplication=true` and the queue has
`ContentBasedDeduplication=false`, dedup runs at the topic level only.

### Lambda subscription vs SQS subscription for Lambda processing

Direct Lambda subscriptions invoke the function on every publish (async).
SQS subscriptions queue messages and let the Lambda event source mapping
control batching and retry. For high-throughput or batch-processing
workloads, prefer SNS → SQS → Lambda (decouples publish rate from
processing rate).

### HTTP endpoint confirmation

HTTP/HTTPS subscriptions require explicit confirmation — SNS sends a
`SubscriptionConfirmation` message with a `SubscribeURL`. The endpoint
must GET this URL within 3 days. For automated deployments, handle the
confirmation programmatically.

### Cross-account subscription confirmation

Only the subscriber account can confirm a cross-account subscription. The
subscribing account receives the token and must call `ConfirmSubscription`.

### Topic policy size limit (30 KiB)

Large policies with many statements can hit this cap. Use IAM identity-
based policies for same-account access instead of growing the resource-based
policy.

### DisplayName for SMS delivery

SNS requires a `DisplayName` for SMS protocol subscriptions. Without it,
SMS delivery fails.

### FIFO topic with non-FIFO SQS subscriber (rejected)

SNS enforces protocol compatibility at subscribe time. A FIFO topic
(`*.fifo`) ONLY accepts SQS FIFO queue subscribers. **Detection:**
`InvalidParameter: Subscription to FIFO topic requires FIFO SQS queue`.
**Fix:** either convert subscriber to FIFO queue, or switch TOPIC to
Standard and preserve ordering downstream via per-consumer FIFO queue
with Lambda event-source mapping.

### Cross-account subscription with SSE-KMS (both key policies required)

When the SNS topic uses a customer-managed CMK and a subscriber lives in
a different account, messages encrypt at the topic with the topic
account's key. The subscriber must decrypt at delivery time. This fails
silently. **Both** key policies must be in place: (a) the TOPIC account's
CMK must grant subscriber account `kms:Decrypt` and `kms:GenerateDataKey*`;
(b) if the subscriber queue also uses SSE-KMS, the subscriber's CMK must
grant SNS `kms:GenerateDataKey*`.

```json
{
  "Sid": "Allow cross-account SNS subscribers",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::222222222222:root" },
  "Action": ["kms:Decrypt", "kms:GenerateDataKey*"],
  "Resource": "*",
  "Condition": {
    "StringEquals": { "kms:ViaService": "sns.us-east-1.amazonaws.com" }
  }
}
```

### Fanout to 100+ SQS queues (high-fanout topology)

A single SNS topic can fan out to up to 12.5M subscriptions, but
operational limits bite at ~100+ SQS subscribers: (a) topic policy size
cap (30 KiB) — use IAM identity-based policies and keep topic policy to
`Principal: "*" + Condition: aws:SourceAccount`; (b) CloudWatch delivery-
log volume — sample the feedback role or scope to failure-only; (c) per-
subscription KMS throttle — 100+ concurrent pushes can hit the shared CMK
rate limit. Fix: customer-managed CMK with higher request quota, or split
into a topic-of-topics hierarchy.

## Error-handling branches

| Error | Cause | Fix |
|---|---|---|
| `InvalidParameter: FIFO topic name must end with .fifo` | FIFO without suffix | Rename with `.fifo` |
| `InvalidParameter: Subscription to FIFO topic requires FIFO SQS queue` | Non-SQS endpoint on FIFO | Use SQS FIFO queue, or Standard topic |
| `KMSAccessDeniedException` | Subscriber lacks `kms:Decrypt` on CMK | Add `kms:Decrypt` + `kms:GenerateDataKey*` to subscriber key policy |
| `AuthorizationError: sns:Subscribe` | Topic policy blocks cross-account | Add foreign account to topic policy |
| Messages not delivered to cross-account SQS | AWS-managed key blocks decrypt | Switch to customer-managed CMK |
| HTTP subscription in `PendingConfirmation` | Endpoint did not confirm within 3 days | Re-subscribe; endpoint must GET SubscribeURL |
| Filter policy silently dropping messages | Non-JSON body with `FilterPolicyScope=MessageBody` | Ensure JSON bodies, or use MessageAttributes |
| Delivery logs not in CloudWatch | Missing CloudWatch Logs resource policy | Add resource policy granting SNS logs permissions |
