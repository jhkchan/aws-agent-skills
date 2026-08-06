---
name: sns-topic-public-subscription-auditor
description: >-
  Audits AWS SNS topics for public subscription exposure (Principal:"*" with
  sns:Subscribe or sns:Publish in topic policy), missing KMS encryption
  (plaintext messages at rest), delivery-status logging gaps (silent message
  loss with no CloudWatch signal), cross-account subscription vectors, and
  FIFO deduplication misconfiguration. Emits a deterministic verdict
  (PUBLIC_SUBSCRIPTION | NO_ENCRYPTION | CONFIG_GAP | OK) per topic with
  enumerated findings and specific CLI remediation. Use when reviewing SNS
  topic policies, checking for public subscription access, validating
  encryption-at-rest, auditing delivery observability, or hardening message
  bus posture before production deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline policy-document classification.
  Live-account audits use aws sns get-topic-attributes, aws sns
  list-subscriptions-by-topic, and aws sns list-topics (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - SNS
  - topic policy
  - public subscription
  - Principal:"*"
  - sns:Subscribe
  - sns:Publish
  - cross-account subscription
  - KMS encryption
  - delivery status logging
  - FIFO deduplication
  - ContentBasedDeduplication
  - MessageDeduplicationId
  - aws:SourceOwner
  - data exfiltration
  - message fanout
  - topic policy remediation
tags: [sns, app-integration, messaging, security, public-access, encryption, delivery-logging, fifo, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: App Integration
  verdict_shape: "PUBLIC_SUBSCRIPTION | NO_ENCRYPTION | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing an SNS topic policy before production deployment, checking for
    public subscription or publish access, validating KMS encryption-at-rest,
    auditing delivery-status logging coverage, verifying FIFO deduplication
    configuration, or hardening message-bus posture across an account.
  activation_triggers:
    - "audit this SNS topic"
    - "is my SNS topic public"
    - "check SNS topic policy"
    - "SNS public subscription"
    - "SNS cross-account access"
    - "SNS delivery logging"
    - "SNS FIFO deduplication"
    - "harden SNS topic policy"
  invocation_schema: >-
    Input: either (a) an SNS topic policy JSON document, optionally paired with
    topic attributes (KmsMasterKeyId, FifoTopic, ContentBasedDeduplication,
    delivery logging config, subscription list), OR (b) a topic ARN for
    live-account audit. Output: deterministic TOPIC / VERDICT / REASON /
    FINDINGS / REMEDIATION block per topic, where VERDICT is in
    {PUBLIC_SUBSCRIPTION, NO_ENCRYPTION, CONFIG_GAP, OK}.
---

# SNS Topic Public Subscription Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
five dimensions, and `sns:Subscribe` on `Principal: "*"` is a **push-based
data exfiltration** vector — worse than the equivalent SQS public-read
because SNS delivers messages to the attacker's endpoint automatically, no
polling required.

SNS is a push-based fan-out bus. A single topic can have 12.5 million
subscriptions, each receiving every published message. Three SNS behaviours
are in a class of their own:

- `sns:Subscribe` is a **push exfiltration vector**: a wildcard principal
  lets anyone register an HTTPS endpoint, email, or SQS queue, and SNS
  pushes every message to them automatically. Unlike SQS (pull), the
  attacker does nothing after the initial subscription — SNS delivers.
- `sns:Publish` on `Principal: "*"` is a **message injection vector**: anyone
  can publish arbitrary payloads that fan out to every subscriber. If any
  subscriber processes messages without validation (Lambda, SQS worker),
  this is remote code execution via the message bus.
- A FIFO topic without deduplication is a **silent duplicate-delivery
  engine**: the whole point of FIFO is exactly-once, and disabling
  ContentBasedDeduplication without publisher-side `MessageDeduplicationId`
  defeats it silently.

## Quick reference — severity thresholds

| Condition | Verdict | Rule |
|---|---|---|
| `Principal: "*"` + `sns:Subscribe`/`sns:*` + no STRONG condition | **PUBLIC_SUBSCRIPTION** | Rule 5a |
| `Principal: "*"` + `sns:Publish` + no STRONG condition | **PUBLIC_SUBSCRIPTION** | Rule 5b |
| `Principal: "*"` + `sns:SetTopicAttributes`/`sns:DeleteTopic` + no STRONG condition | **PUBLIC_SUBSCRIPTION** | Rule 5c |
| `Principal: "*"` + any `sns:` action + STRONG condition (`aws:SourceOwner`) | **CONFIG_GAP** (downgrade) | Rule 5d |
| `KmsMasterKeyId` is empty or absent | **NO_ENCRYPTION** | Step 2 |
| Cross-account principal + `sns:Subscribe`/`sns:Publish` + no STRONG condition | **CONFIG_GAP** | Rule 5e |
| No delivery-status logging on any protocol | **CONFIG_GAP** | Step 3 |
| FIFO topic + `ContentBasedDeduplication: false` | **CONFIG_GAP** | Step 4 |
| Confirmed subscription from a foreign account | **CONFIG_GAP** | Step 5 |
| Same-account only + CMK encryption + delivery logging on all active protocols + dedup OK | **OK** | Step 6 |

See the ordered steps below for edge cases. Deep SNS delivery internals
(retry semantics, CloudWatch log resource policy, FIFO throughput quotas)
are in the [Deep reference](#deep-reference-sns-internals) section.

## Pre-flight: topic metadata gate (run before policy classification)

Several topic attributes **short-circuit** the audit. Misclassifying them
produces false positives that erode trust.

**Multi-topic / account-wide sweep note (pagination):** when auditing every
topic in an account, `aws sns list-topics` returns 100 per page. Use
`--next-token` to page through. For each topic, page
`aws sns list-subscriptions-by-topic --topic-arn <arn>` (also capped at 100
per page). Always drain `NextToken` to completion — a topic with 500
subscriptions spans 5 pages, and the long-tail subscriptions are where stale
or unexpected cross-account endpoints hide.

**Live-account pre-flight checks (skip if doing offline policy-doc audit):**
1. Verify the caller can run `sns:SetTopicAttributes` if remediation is
   intended — most read-only auditor roles CANNOT, and remediation commands
   will fail with `AuthorizationError`. Surface this BEFORE the operator
   approves.
2. Snapshot `aws sns get-topic-attributes --topic-arn <arn>` BEFORE any
   policy edit. Topic attributes are not versioned — a `SetTopicAttributes`
   replaces the attribute value atomically with no rollback.
3. For cross-account subscription enumeration, verify the caller has
   `sns:ListSubscriptionsByTopic` on the topic — the topic policy may
   restrict this to the topic owner.

| Attribute | Value | Effect on audit |
|---|---|---|
| `FifoTopic` | `true` | **FIFO topic.** Only SQS FIFO queues can be subscribers — HTTP, email, SMS, and Lambda subscriptions are structurally impossible. If the subscription list shows non-SQS protocols on a FIFO topic, it is stale data or a data inconsistency. Evaluate ContentBasedDeduplication (Step 4). |
| `FifoTopic` | `false` / absent | **Standard topic.** Skip FIFO dedup check (Step 4 is N/A). |
| `KmsMasterKeyId` | empty / null | **Unencrypted topic.** Messages are stored in plaintext in SNS infrastructure. Jump to Step 2. |
| `KmsMasterKeyId` | `alias/aws/sns` | **AWS-managed key.** Encryption at rest is enabled. BUT cross-account subscribers cannot decrypt — the AWS-managed key policy only permits the owning account. Flag as a note if cross-account subscriptions exist. |
| `KmsMasterKeyId` | CMK ARN / alias | **Customer-managed key.** Encryption is enabled. Proceed to verify the CMK policy grants decrypt to subscriber accounts. |
| `DisplayName` | empty | **No display name.** SMS delivery is impossible (SNS requires a DisplayName for SMS protocol). Note as operational gap if SMS subscriptions exist. |
| `SubscriptionsConfirmed` | 0 | Topic has no active subscribers. Messages are published but delivered to no one — note as operational risk (cost waste, not security). |

**If the topic policy JSON is malformed** (invalid JSON, missing `Statement`,
missing `Principal` or `Action`), output:

```text
TOPIC: <topic-arn>
VERDICT: ERROR
REASON: Topic policy document is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical policy with `aws sns get-topic-attributes --topic-arn <arn> --query 'Attributes.Policy' --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

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

### Step 1: Topic policy — public subscription exposure (highest priority)

For each `Effect: Allow` statement in the topic policy, classify the principal:

- **WILDCARD** — `Principal` is `"*"`, `{"AWS": "*"}`, or any construct that
  resolves to all principals. `NotPrincipal` in an Allow is also WILDCARD.
- **CROSS_ACCOUNT** — `Principal` includes a 12-digit account ID that
  differs from the topic's owning account (extract from the topic ARN).
- **SAME_ACCOUNT** — All principals share the topic's owning account ID.

Then classify the action danger:

| Danger level | Actions | Why |
|---|---|---|
| **SUBSCRIBE_ACCESS** | `sns:Subscribe`, `sns:*`, `*` | Anyone can register an endpoint and receive all messages. Push-based data exfiltration. |
| **PUBLISH_ACCESS** | `sns:Publish`, `sns:PublishBatch` | Anyone can inject messages into the fanout. Message bus injection. |
| **TOPIC_CONTROL** | `sns:SetTopicAttributes`, `sns:DeleteTopic`, `sns:RemovePermission`, `sns:AddPermission` | Can modify the topic, change encryption, or delete it. |
| **METADATA** | `sns:GetTopicAttributes`, `sns:ListSubscriptionsByTopic` | Information disclosure (topic config, subscriber list). Low severity. |

`NotAction` in an Allow is an inverse wildcard — treat as SUBSCRIBE_ACCESS +
PUBLISH_ACCESS + TOPIC_CONTROL (all danger levels).

### Step 2: KMS encryption-at-rest

Evaluate `KmsMasterKeyId` from topic attributes:

- **Empty or absent** → **NO_ENCRYPTION** (primary verdict driver). Messages
  are stored in plaintext within SNS infrastructure. If CloudWatch delivery
  logging is enabled, message content appears in plaintext in CloudWatch
  Logs. Cross-account delivery works (no KMS key to decrypt), but the
  security posture is unencrypted-at-rest.
- **`alias/aws/sns`** → **OK** for encryption. BUT if cross-account
  subscriptions exist, flag as a note: AWS-managed key blocks cross-account
  decryption — subscribers in other accounts cannot decrypt the message
  body, and deliveries silently fail.
- **Customer-managed key ARN** → **OK** for encryption. Note: verify the
  CMK policy grants `kms:Decrypt` and `kms:GenerateDataKey*` to subscriber
  accounts — the topic policy may allow cross-account subscriptions but the
  CMK policy is a separate gate.

### Step 3: Delivery status logging

Check for delivery-status logging configuration on each protocol that has
active subscriptions. For each protocol, SNS uses paired attributes:
`<Protocol>SuccessFeedbackRoleArn` and `<Protocol>FailureFeedbackRoleArn`.

Protocols: `HTTP` (covers HTTP/HTTPS), `SQS`, `Application` (covers Lambda,
mobile push, Firehose).

- **No `FailureFeedbackRoleArn` on any protocol with active subscriptions**
  → **CONFIG_GAP** (additive finding). Delivery failures are invisible —
  SNS retries HTTP for up to 4 hours (100,010 attempts), then silently drops
  the message. Without failure logging, dropped messages are undetectable.
- **Partial logging** (some protocols logged, others not) → **CONFIG_GAP**.
  Each protocol needs its own logging configuration.
- **Failure logging configured on all active protocols** → OK for this
  dimension.

**Expert note:** delivery logging also requires a CloudWatch Logs resource
policy granting SNS `logs:CreateLogStream` and `logs:PutLogEvents`. Without
it, SNS silently fails to write logs. If you can verify this in a
live-account audit, check
`aws logs describe-resource-policy --log-group-name <sns-log-group>`.

### Step 4: FIFO deduplication (FIFO topics only)

Skip if `FifoTopic` is `false` or absent (standard topic — dedup is N/A).

- **FIFO + `ContentBasedDeduplication: false`** → **CONFIG_GAP** (additive
  finding). The publisher MUST send `MessageDeduplicationId` on every
  message. If the publisher omits it, SNS delivers duplicate messages within
  the 5-minute dedup window — silently breaking the exactly-once guarantee.
  This is an architectural gap, not a security exposure, but it defeats the
  sole purpose of using a FIFO topic.
- **FIFO + `ContentBasedDeduplication: true`** → OK for this dimension. SNS
  computes a content hash for dedup automatically.
- **FIFO + `ContentBasedDeduplication` absent** → treat as `false` (the API
  default is false). Flag as CONFIG_GAP.

### Step 5: Cross-account subscription audit (live-account or subscription list)

If a subscription list is provided or available via live-account audit,
enumerate subscriptions and classify each by the subscriber's account ID:

- **Confirmed subscription from a foreign account** → **CONFIG_GAP**
  (additive finding). The foreign account receives every message published
  to the topic. This may be intentional (cross-account fanout) but should be
  verified against the topic policy — if the topic policy does NOT
  explicitly allow the foreign account, the subscription should not exist.
- **`PendingConfirmation` subscriptions** → note only (no message delivery).
  These are zombie subscriptions from unconfirmed requests. The confirmation
  token expired after 3 days but the record persists. Clean up with
  `aws sns unsubscribe --subscription-arn <arn>`.
- **All subscriptions from the owning account** → OK for this dimension.

### Step 6: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all dimensions, where
`PUBLIC_SUBSCRIPTION > NO_ENCRYPTION > CONFIG_GAP > OK`:

```text
verdict = max(
    topic_policy_severity,        # Step 1
    encryption_severity,          # Step 2
    delivery_logging_severity,    # Step 3
    fifo_dedup_severity,          # Step 4
    cross_account_sub_severity    # Step 5
)
```

If no findings (all dimensions OK), the verdict is **OK**.

## Output format (per topic)

```text
TOPIC: <topic-arn>
VERDICT: PUBLIC_SUBSCRIPTION | NO_ENCRYPTION | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its rule>
FINDINGS:
  - [PUBLIC_SUBSCRIPTION] <finding description (Rule Na)>
  - [CONFIG_GAP] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific CLI commands per finding, or "None required" if OK>
```

### Worked example — public subscribe with no encryption

```text
TOPIC: arn:aws:sns:us-east-1:111111111111:public-subscribe-no-encryption
VERDICT: PUBLIC_SUBSCRIPTION
REASON: Topic policy grants sns:Subscribe to Principal "*" with no restrictive
condition — anyone can register an endpoint and receive all messages (Rule 5a).
Messages are also unencrypted at rest.
FINDINGS:
  - [PUBLIC_SUBSCRIPTION] Principal "*" + sns:Subscribe with no condition (Rule 5a)
  - [NO_ENCRYPTION] KmsMasterKeyId is empty — messages stored in plaintext (Step 2)
REMEDIATION:
  1. Remove the wildcard principal, or add aws:SourceOwner condition:
     aws sns set-topic-attributes --topic-arn <arn> --attribute-name Policy \
       --attribute-value '<tightened-policy-json>'
  2. Enable KMS encryption:
     aws sns set-topic-attributes --topic-arn <arn> \
       --attribute-name KmsMasterKeyId --attribute-value <cmk-key-id>
```

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

## Anti-Patterns — NEVER

- NEVER classify `Principal: "*"` with `sns:Subscribe` as anything other
  than PUBLIC_SUBSCRIPTION (when no STRONG condition). SNS pushes messages
  to subscribers — a wildcard Subscribe is passive, persistent data
  exfiltration. It is not "broad access"; it is a data pipe to anyone who
  asks.

- NEVER treat `Principal: "*"` with `sns:Publish` as less severe than
  `sns:Subscribe`. Publish is an injection vector: arbitrary payloads fan
  out to every subscriber. If any subscriber writes to a database or
  triggers Lambda, this is remote code execution via the message bus.

- NEVER downgrade a wildcard Subscribe/Publish because of an
  `aws:SourceIp` condition. SourceIp is caller-controlled in practice — any
  principal with a NAT gateway or VPN can route through an allowed CIDR.
  Only `aws:SourceOwner`, `aws:SourceAccount`, and `aws:SourceArn` are
  STRONG (set by the AWS service infrastructure, not forgeable).

- NEVER flag an AWS-managed key (`alias/aws/sns`) as NO_ENCRYPTION. The
  AWS-managed SNS key DOES encrypt messages at rest. It is OK for the
  encryption dimension. The issue with `alias/aws/sns` is cross-account
  delivery (the subscriber cannot decrypt), which is a CONFIG_GAP, not
  NO_ENCRYPTION.

- NEVER flag `ContentBasedDeduplication: false` on a **standard** (non-FIFO)
  topic. Deduplication is a FIFO-only concept. Standard topics have no
  dedup guarantee by design — flagging it is a false positive.

- NEVER assume a FIFO topic supports HTTP/email/Lambda subscriptions. FIFO
  topics ONLY support SQS FIFO queue subscribers. If the metadata shows
  non-SQS subscriptions on a FIFO topic, the data is stale — flag as a data
  inconsistency, not a security finding.

- NEVER treat `PendingConfirmation` subscriptions as active data
  exfiltration. Pending subscriptions do not receive messages. They are
  zombie records that pollute the list — clean them up, but do not classify
  them as PUBLIC_SUBSCRIPTION findings.

- NEVER recommend removing the topic policy entirely as remediation. An
  empty topic policy blocks ALL external access, including legitimate
  same-account service-to-service publishing. The fix is to scope the
  principal to explicit account/role ARNs, not to delete the policy.

- NEVER ignore `NotPrincipal` in an Allow statement. `NotPrincipal` grants
  access to everyone EXCEPT the listed principal — the inverse of intended
  scope. Treat as WILDCARD and flag as PUBLIC_SUBSCRIPTION if the action is
  Subscribe/Publish.

- NEVER assume delivery-status logging works just because the feedback role
  ARN is set. SNS also requires a CloudWatch Logs resource policy granting
  `logs:CreateLogStream` and `logs:PutLogEvents`. Without it, SNS silently
  drops delivery logs. Both sides must be configured.

- NEVER classify a cross-account subscription as PUBLIC_SUBSCRIPTION.
  Cross-account means a specific foreign account has access — bad, but not
  "anyone on the internet." Cross-account subscription is a CONFIG_GAP;
  wildcard principal is PUBLIC_SUBSCRIPTION.

- NEVER overlook `sns:SetTopicAttributes` in a wildcard or cross-account
  statement. A principal with `SetTopicAttributes` can change the KMS key
  (disabling encryption), modify delivery logging (blinding observability),
  or change the topic policy (locking out the owner). This is topic-level
  admin control — treat as PUBLIC_SUBSCRIPTION when combined with wildcard
  principal.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`SetTopicAttributes`, `DeleteTopic`, `Subscribe`, `Unsubscribe`), the
  auditor MUST emit:
  `CONFIRM: About to <action> on topic <arn> in account <account>. This
  affects <consequence>. Proceed? (yes/no)`
  Do NOT execute until the operator confirms.
- Capture the current topic attributes for rollback:
  `aws sns get-topic-attributes --topic-arn <arn> --output json > /tmp/<topic-name>-backup-$(date +%s).json`
  BEFORE any modification. Topic attributes are not versioned — there is no
  undo without a backup.
- Before changing `KmsMasterKeyId`, verify the new key exists and that all
  subscriber accounts have `kms:Decrypt` + `kms:GenerateDataKey*` on the key
  policy. Changing the key without updating subscriber permissions causes
  immediate delivery failure for all cross-account subscribers.
- Before removing a wildcard principal from the topic policy, verify that
  legitimate publishers/subscribers have IAM permissions to access the
  topic. The topic policy and IAM policies intersect for same-account
  access — removing the policy statement may break same-account services
  that relied on it.
- Prefer additive changes (add a Deny statement, add a condition) over
  destructive changes (remove an Allow statement) — additive changes are
  reversible and do not risk breaking existing access patterns.

## Remediation guidance

**Ordering principle:** always prefer additive changes (add a Deny, add a
condition) over destructive changes (remove an Allow). A Deny blocks access
immediately and is reversible; removing an Allow may break a publisher or
subscriber you did not anticipate.

### For PUBLIC_SUBSCRIPTION — wildcard Subscribe/Publish (Rules 5a, 5b, 5c)

1. **Immediately** scope the wildcard principal to explicit account/role
   ARNs, or add a STRONG condition (`aws:SourceOwner`):
   ```bash
   aws sns set-topic-attributes --topic-arn <arn> \
     --attribute-name Policy --attribute-value '<scoped-policy-json>'
   ```
2. **Assume exfiltration.** Audit CloudTrail for `Subscribe` and `Publish`
   events from unexpected principals during the exposure window. Review
   delivery logs (if configured) for subscriber endpoints that received
   messages.
3. If the topic genuinely needs public publish (e.g., a public API
   webhook), restrict to `sns:Publish` only and add `aws:SourceIp` or
   `aws:SourceOwner` conditions. NEVER leave `sns:Subscribe` open to `"*"`.

### For NO_ENCRYPTION — missing KMS key

1. Enable KMS encryption with a customer-managed key:
   ```bash
   aws sns set-topic-attributes --topic-arn <arn> \
     --attribute-name KmsMasterKeyId --attribute-value <cmk-key-id>
   ```
2. Verify the CMK policy grants `kms:Decrypt` and `kms:GenerateDataKey*` to
   all subscriber accounts (for cross-account subscriptions).
3. Existing messages published before encryption was enabled are NOT
   retroactively encrypted — only future messages are affected.

### For CONFIG_GAP — delivery logging missing

1. Configure delivery-status logging with a CloudWatch role:
   ```bash
   aws sns set-topic-attributes --topic-arn <arn> \
     --attribute-name SQSSuccessFeedbackRoleArn \
     --attribute-value arn:aws:iam::<account>:role/SNSDeliveryFeedback
   aws sns set-topic-attributes --topic-arn <arn> \
     --attribute-name SQSFailureFeedbackRoleArn \
     --attribute-value arn:aws:iam::<account>:role/SNSDeliveryFeedback
   ```
2. Add the CloudWatch Logs resource policy granting SNS write access:
   ```bash
   aws logs put-resource-policy --policy-name SNSDeliveryLogging \
     --policy-document '<sns-logs-policy-json>'
   ```
3. Repeat for each active protocol (HTTP, Application/Lambda).

### For CONFIG_GAP — FIFO dedup disabled

1. Enable content-based deduplication:
   ```bash
   aws sns set-topic-attributes --topic-arn <arn> \
     --attribute-name ContentBasedDeduplication --attribute-value true
   ```
2. Alternatively, ensure every publisher sends a unique
   `MessageDeduplicationId` per message. This is more error-prone than
   topic-level dedup — prefer `ContentBasedDeduplication: true` unless
   the publisher needs explicit dedup control.

### For CONFIG_GAP — cross-account subscription

1. Verify the subscription is intentional against the topic policy.
2. If unintentional, unsubscribe:
   ```bash
   aws sns unsubscribe --subscription-arn <sub-arn>
   ```
3. Tighten the topic policy to restrict `sns:Subscribe` to the owning
   account only.

### For OK

1. No remediation required for the current posture.
2. Recommend verifying the CloudWatch Logs resource policy is in place
   (defense-in-depth — delivery logging is configured but SNS needs the log
   resource policy to write).
3. For cross-account topics, verify the CMK policy grants decrypt to all
   subscriber accounts.

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

## Domain

AWS CloudOps / App Integration Security & Compliance.

## AWS documentation

- **Amazon SNS Developer Guide** — https://docs.aws.amazon.com/sns/latest/dg/welcome.html
- **SNS Security** — https://docs.aws.amazon.com/sns/latest/dg/sns-security.html
- **SNS API Reference** — https://docs.aws.amazon.com/sns/latest/api/welcome.html
- **AWS CLI SNS Command Reference** — https://docs.aws.amazon.com/cli/latest/reference/sns/
- **Message data protection** — https://docs.aws.amazon.com/sns/latest/dg/sns-message-data-protection.html
