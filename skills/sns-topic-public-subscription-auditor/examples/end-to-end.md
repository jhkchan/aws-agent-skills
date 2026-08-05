# End-to-end usage scenario: sns-topic-public-subscription-auditor

A walkthrough showing the skill auditing an SNS topic that has both a
public subscription grant (PUBLIC_SUBSCRIPTION) and no KMS encryption
(NO_ENCRYPTION), plus a FIFO topic with dedup disabled, demonstrating
severity aggregation, the push-exfiltration concept, and the
aws:SourceOwner downgrade.

## Input (user prompt)

> Review this SNS topic before we go live. It's our notification fanout
> topic for the payments pipeline — Lambda and SQS subscribers in two
> accounts.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RootAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": "sns:*",
      "Resource": "arn:aws:sns:us-east-1:111111111111:payments-fanout"
    },
    {
      "Sid": "OpenSubscribe",
      "Effect": "Allow",
      "Principal": "*",
      "Action": [
        "sns:Subscribe",
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:us-east-1:111111111111:payments-fanout"
    }
  ]
}
```

Topic attributes:
- FifoTopic: false
- KmsMasterKeyId: (empty)
- SubscriptionsConfirmed: 4
- No delivery feedback roles configured

## Skill output

```text
TOPIC: arn:aws:sns:us-east-1:111111111111:payments-fanout
VERDICT: PUBLIC_SUBSCRIPTION
REASON: Topic policy grants sns:Subscribe and sns:Publish to Principal "*"
with no restrictive condition — anyone can register an endpoint and receive
all messages, plus inject arbitrary messages (Rule 5a/5b). Messages are also
unencrypted at rest and delivery logging is absent.
FINDINGS:
  - [PUBLIC_SUBSCRIPTION] Principal "*" + sns:Subscribe with no condition
    (Rule 5a) — push-based data exfiltration: SNS delivers every message to
    the subscriber's endpoint automatically
  - [PUBLIC_SUBSCRIPTION] Principal "*" + sns:Publish with no condition
    (Rule 5b) — message injection: anyone can publish arbitrary payloads
    that fan out to all subscribers
  - [NO_ENCRYPTION] KmsMasterKeyId is empty — messages stored in plaintext
    (Step 2)
  - [CONFIG_GAP] No delivery-status logging on any protocol (Step 3) —
    delivery failures are invisible
REMEDIATION:
  1. Scope the wildcard principal to explicit account/role ARNs, or add
     aws:SourceOwner condition:
     aws sns set-topic-attributes --topic-arn <arn> \
       --attribute-name Policy --attribute-value '<scoped-policy-json>'
  2. Enable KMS encryption with a customer-managed key:
     aws sns set-topic-attributes --topic-arn <arn> \
       --attribute-name KmsMasterKeyId --attribute-value <cmk-key-id>
  3. Configure delivery-status logging for all active protocols:
     aws sns set-topic-attributes --topic-arn <arn> \
       --attribute-name SQSFailureFeedbackRoleArn \
       --attribute-value arn:aws:iam::111111111111:role/SNSDeliveryFeedback
  4. Add the CloudWatch Logs resource policy granting SNS write access.
```

## Key reasoning the skill applies

1. **Push vs pull exfiltration:** `sns:Subscribe` with `Principal: "*"` is
   worse than an SQS public-read because SNS pushes messages to the
   subscriber endpoint on every publish. The attacker registers once and
   passively receives every message — no polling, no ongoing API calls.

2. **aws:SourceOwner downgrade:** If the same policy had
   `Condition: {"StringEquals": {"aws:SourceOwner": "111111111111"}}`, the
   verdict would downgrade to CONFIG_GAP — the exposure is scoped to the
   owning account but remains fragile (a policy edit could widen it).

3. **Aggregation order:** PUBLIC_SUBSCRIPTION > NO_ENCRYPTION >
   CONFIG_GAP > OK. The topic has findings in all three non-OK categories,
   so the verdict is PUBLIC_SUBSCRIPTION (the worst). Encryption and
   logging findings are still enumerated in FINDINGS for the operator to
   address after the public exposure is fixed.
