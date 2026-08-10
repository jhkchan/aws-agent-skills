---
description: Deploy an AWS SNS topic with production-grade configuration (correct topic type, subscriptions across all protocols, filter policies, SSE-KMS encryption, delivery status logging, subscription-level DLQ, FIFO deduplication, mobile push). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create sns topic"
  - "deploy sns topic"
  - "sns topic configuration"
  - "sns subscription"
  - "sns filter policy"
  - "sns delivery status logging"
  - "sns fifo topic"
  - "sns encryption"
  - "sns cross-account"
  - "sns mobile push"
  - "sns dead letter queue"
  - "sns http subscription"
  - "sns sqs subscription"
  - "sns lambda subscription"
  - "sns firehose subscription"
routes_to: sns-topic-deployer
---

# /aws:deploy-sns-topic

Activate the `sns-topic-deployer` skill and deploy an SNS topic with
production-grade configuration.

## What it does

The skill walks a 10-step deployment procedure and emits a
READY_TO_DEPLOY checklist:

1. Topic type selection (Standard vs FIFO — immutable after creation)
2. Subscriptions (HTTP/S, SQS, Lambda, Email, Firehose, mobile push)
3. Subscription filter policy (MessageAttributes vs MessageBody scope)
4. Access policy (least-privilege, S3/CloudWatch/cross-account patterns)
5. Encryption (SSE-KMS, AWS-managed vs customer-managed, cross-account decrypt)
6. Delivery status logging (per-protocol CloudWatch Logs)
7. Subscription-level dead-letter queue (RedrivePolicy on subscriptions)
8. FIFO specifics (deduplication, MessageGroupId, .fifo suffix)
9. Mobile push (APNS, FCM, Baidu, platform application setup)
10. Verification commands

## When to use

- You need to create a new SNS topic with production defaults.
- You are deploying a topic to production and want to validate config.
- You need deployment CLI commands or Terraform/SAM templates.
- You want to check for deployment blockers (FIFO with Lambda subscriber,
  AWS-managed key with cross-account, HTTP without delivery logging).

## How to invoke

### Slash command

```
/aws:deploy-sns-topic
```

Then provide: topic name, topic type (Standard/FIFO), subscriber list
(protocol + endpoint), workload pattern, and any optional features
(SSE-KMS, filter policies, delivery logging, mobile push).

### Natural language

Any of these routes to the same skill:

- "create an SNS topic"
- "deploy a FIFO topic with an SQS subscriber"
- "set up an SNS topic for S3 notifications"
- "configure SNS delivery status logging"
- "deploy an SNS topic with mobile push"

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline. The
output checklist feeds into verification pipelines and audit skills
(sns-topic-public-subscription-auditor for post-deployment security checks).

## Example

```
You: /aws:deploy-sns-topic

     Deploy a production SNS topic "order-events" in us-east-1.
     Standard topic. S3 notifications from bucket "order-uploads".
     Subscribers: SQS queue "order-queue" (filter event_type
     order_created), Lambda function "order-handler". SSE-KMS with
     AWS-managed key. Enable SQS delivery status logging.
     Account: 111111111111.

Skill:
  TOPIC: order-events
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Topic type — Standard (best-effort ordering, unlimited TPS)
    [✓]      Encryption — SSE-KMS (alias/aws/sns, same-account)
    [✓]      Access policy — S3 notification pattern (Principal:* + aws:SourceArn)
    [✓]      Subscriptions — 2 active (SQS: order-queue, Lambda: order-handler)
    [✓]      Delivery logging — SQS failure (role: SNSDeliveryFeedback)
    [✓]      Filter policy — event_type: ["order_created"] on SQS subscription
  VERIFICATION_COMMANDS:
    aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:111111111111:order-events
    aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:111111111111:order-events
    aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:111111111111:order-events --query 'Attributes.KmsMasterKeyId'
```

## References

- Skill definition: `skills/sns-topic-deployer/SKILL.md`
- Configuration guide: `skills/sns-topic-deployer/references/topic-configuration-guide.md`
- Deployment CLI commands: `skills/sns-topic-deployer/references/deployment-cli-commands.md`
- Eval suite: `skills/sns-topic-deployer/evals/evals.json`
