# Worked Examples — SNS Topic Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Required output structure

Every response MUST be the checklist block below — nothing before it,
nothing after `VERIFICATION_COMMANDS`. The labels are case-sensitive
all-caps keywords.

```text
TOPIC: <topic-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗|OPTIONAL]      Topic type — Standard | FIFO
  [✓|✗]               Encryption — SSE-KMS (key, same-account | cross-account)
  [✓|✗]               Access policy — <pattern: S3 notification | cross-account | IAM-only>
  [✓|✗]               Subscriptions — <count> active (<protocols>)
  [✓|✗]               Delivery logging — <protocols> failure (role: <role-arn>)
  [✓|✗|OPTIONAL]      Filter policy — <summary> | N/A
  [✓|✗|OPTIONAL]      Subscription DLQ — <dlq-arn> | N/A
  [✓|✗|OPTIONAL]      FIFO dedup — ContentBasedDeduplication=<true|false> | N/A
  [✓|✗|OPTIONAL]      Mobile push — <platform ARNs> | N/A
VERIFICATION_COMMANDS:
  <one command per [✓] item>
```

### Perfect example output — PREREQUISITES_MISSING

```text
TOPIC: order-events-cross-account
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Topic type — Standard (cross-account fan-out, no ordering requirement)
  [✗]      Encryption — alias/aws/sns selected but cross-account subscriber in account 222222222222 needs kms:Decrypt — supply customer-managed CMK with cross-account key policy
  [✓]      Access policy — Cross-account publisher (Principal: account 222222222222, Action: sns:Publish)
  [✗]      Subscriptions — 0 active: SQS queue arn in account 222222222222 not yet subscribed — subscribe the cross-account queue and confirm from the subscriber account
  [✗]      Delivery logging — CloudWatch role SNSDeliveryFeedback not found — create IAM role with trust policy for sns.amazonaws.com + logs:PutLogEvents
  [OPTIONAL] Filter policy — N/A (no filtering needed)
  [OPTIONAL] Subscription DLQ — N/A (SQS has own DLQ)
  [OPTIONAL] FIFO dedup — N/A (Standard topic)
  [OPTIONAL] Mobile push — N/A (no mobile subscribers)
VERIFICATION_COMMANDS:
  aws kms describe-key --key-id alias/my-sns-cross-account-key
  aws kms get-key-policy --key-id alias/my-sns-cross-account-key --policy-name default
  aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:111111111111:order-events-cross-account
  aws iam get-role --role-name SNSDeliveryFeedback
```

## Self-check before emit

**Self-check before emit:**
- [ ] All 9 checklist rows present (REQUIRED + OPTIONAL)?
- [ ] Cross-account topic uses customer-managed CMK (not alias/aws/sns)?
- [ ] Delivery logging cites BOTH role ARN AND CW Logs resource policy?
- [ ] No subscription in PendingConfirmation marked as active?
- [ ] FIFO topic has `.fifo` suffix and only SQS FIFO subscribers?
- [ ] Every `[✗]` cites the specific gap and what the operator must provide?
- [ ] Literal labels used exactly (no markdown variants)?
