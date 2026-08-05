---
description: Audit an SNS topic for public subscription exposure (Principal:* with sns:Subscribe/Publish), missing KMS encryption, delivery-status logging gaps, FIFO deduplication misconfiguration, and cross-account subscriptions.
nl_triggers:
  - "audit this SNS topic"
  - "check SNS topic policy"
  - "SNS public subscription"
  - "SNS cross-account access"
  - "sns:Subscribe Principal star"
  - "SNS topic encryption"
  - "SNS delivery logging"
  - "SNS FIFO deduplication"
  - "ContentBasedDeduplication"
  - "SNS message exfiltration"
  - "harden SNS topic"
routes_to: sns-topic-public-subscription-auditor
---

# /aws:audit-sns-topic-public-subscription

Activate the `sns-topic-public-subscription-auditor` skill and audit one or
more SNS topic configurations (topic policy + topic attributes) for security
exposure.

## What it does

Reads an SNS topic policy document plus topic attributes (KmsMasterKeyId,
FifoTopic, ContentBasedDeduplication, delivery logging config, subscription
list) and applies the ordered classification logic:

1. Topic policy — public subscription exposure (Principal: "*" with
   sns:Subscribe/Publish/SetTopicAttributes and no STRONG condition).
2. KMS encryption — empty KmsMasterKeyId means plaintext messages at rest.
3. Delivery status logging — per-protocol; missing means invisible message
   loss.
4. FIFO deduplication — ContentBasedDeduplication: false on a FIFO topic
   breaks exactly-once silently.
5. Cross-account subscriptions — confirmed subscriptions from foreign
   accounts.
6. Aggregation — worst finding wins (PUBLIC_SUBSCRIPTION > NO_ENCRYPTION >
   CONFIG_GAP > OK).

Emits a deterministic VERDICT per topic:

```text
TOPIC: <topic-arn>
VERDICT: PUBLIC_SUBSCRIPTION | NO_ENCRYPTION | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and rule>
FINDINGS:
  - [PUBLIC_SUBSCRIPTION] <finding description (Rule Na)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific CLI commands per finding, or "None required" if OK>
```

## When to invoke

Paste an SNS topic policy and attributes and ask any of:

- "audit this SNS topic"
- "is my SNS topic public?"
- "check SNS topic policy for public access"
- "who can subscribe to my SNS topic?"
- "is SNS delivery logging configured?"
- "does my FIFO topic have deduplication?"

A bare topic ARN + any audit verb ("audit this topic", "check topic
policy") also routes here via the orchestrator.

## Inputs

- An SNS topic policy document (JSON), pasted inline or referenced by file
  path.
- Topic attributes: KmsMasterKeyId, FifoTopic, ContentBasedDeduplication,
  delivery feedback role ARNs (SQSSuccessFeedbackRoleArn,
  SQSFailureFeedbackRoleArn, HTTPSuccessFeedbackRoleArn, etc.),
  SubscriptionsConfirmed.
- For cross-account audit: a subscription list with subscriber account IDs.

## Outputs

- One VERDICT block per topic (multiple findings aggregate to the worst
  verdict).
- Enumerated FINDINGS list with per-finding severity and rule citation.
- Specific remediation: scope principals, enable KMS, configure delivery
  logging, enable content-based deduplication, unsubscribe foreign
  endpoints.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for App Integration security).
- `/aws:audit-kms-key-policy` for auditing the CMK policy that protects
  SNS message encryption (if the topic uses a customer-managed key).
