# End-to-End Example: SNS Topic Deployment

A walkthrough showing how to use the `sns-topic-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are deploying a production SNS topic that receives S3 Event
Notifications when orders are uploaded, fans out to an SQS queue for
order processing, and triggers a Lambda function for real-time
analytics. The topic requires:

- Standard topic type (best-effort ordering, unlimited throughput)
- SSE-KMS encryption (AWS-managed key, same-account)
- S3 Event Notification access policy (Principal:* + aws:SourceArn)
- SQS subscription with filter policy (event_type: order_created)
- Lambda subscription
- SQS delivery status logging (CloudWatch role)
- Cross-account publishing for a partner account (optional)

Topic name: `order-events`
Region: `us-east-1`
Account: `111111111111`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-sns-topic
```

Then paste the topic requirements.

### Option B: Natural language

```
You: "Deploy a production SNS topic named order-events in us-east-1.
      It receives S3 notifications from bucket order-uploads. Two
      subscribers: SQS queue order-queue (filter on event_type
      order_created) and Lambda function order-handler. SSE-KMS with
      AWS-managed key. Enable SQS delivery status logging.
      Account: 111111111111."
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
TOPIC: order-events
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Topic type — Standard (best-effort ordering, unlimited TPS)
  [✓]      Encryption — SSE-KMS (alias/aws/sns, same-account)
  [✓]      Access policy — S3 notification pattern (Principal:* + aws:SourceArn: order-uploads)
  [✓]      Subscriptions — 2 active (SQS: order-queue, Lambda: order-handler)
  [✓]      Delivery logging — SQS failure (role: SNSDeliveryFeedback)
  [✓]      Filter policy — event_type: ["order_created"] on SQS subscription
  [OPTIONAL] Subscription DLQ — N/A (SQS has own DLQ)
  [OPTIONAL] FIFO dedup — N/A (Standard topic)
  [OPTIONAL] Mobile push — N/A (no mobile subscribers)
VERIFICATION_COMMANDS:
  aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:111111111111:order-events
  aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:111111111111:order-events
  aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:111111111111:order-events --query 'Attributes.KmsMasterKeyId'
  aws sns publish --topic-arn arn:aws:sns:us-east-1:111111111111:order-events --message '{"test": true}'
```

---

## Step 3 — Deployment commands

The skill generates the CLI sequence (from
`references/deployment-cli-commands.md`):

```bash
# Step 1: Create the topic
aws sns create-topic --name order-events

# Step 2: Enable SSE-KMS (AWS-managed key)
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name KmsMasterKeyId \
  --attribute-value alias/aws/sns

# Step 3: S3 Event Notification access policy
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name Policy \
  --attribute-value '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:us-east-1:111111111111:order-events",
      "Condition": {
        "ArnEquals": { "aws:SourceArn": "arn:aws:s3:::order-uploads" }
      }
    }]
  }'

# Step 4: SQS subscription
SQS_SUB_ARN=$(aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:111111111111:order-queue \
  --return-subscription-arn --query 'SubscriptionArn' --output text)

# Step 5: Filter policy on SQS subscription
aws sns set-subscription-attributes \
  --subscription-arn "$SQS_SUB_ARN" \
  --attribute-name FilterPolicy \
  --attribute-value '{"event_type": ["order_created"]}'

# Step 6: Lambda subscription
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:111111111111:function:order-handler \
  --return-subscription-arn

# Step 7: SQS delivery status logging
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name SQSFailureFeedbackRoleArn \
  --attribute-value arn:aws:iam::111111111111:role/SNSDeliveryFeedback

# Step 8: S3 Event Notification to SNS
aws s3api put-bucket-notification-configuration \
  --bucket order-uploads \
  --notification-configuration '{
    "TopicConfigurations": [{
      "TopicArn": "arn:aws:sns:us-east-1:111111111111:order-events",
      "Events": ["s3:ObjectCreated:*"]
    }]
  }'
```

---

## Step 4 — Post-deployment verification

```bash
TOPIC_ARN=arn:aws:sns:us-east-1:111111111111:order-events

# Topic attributes (all configuration)
aws sns get-topic-attributes --topic-arn "$TOPIC_ARN" --output json

# List subscriptions
aws sns list-subscriptions-by-topic --topic-arn "$TOPIC_ARN"

# Verify encryption
aws sns get-topic-attributes --topic-arn "$TOPIC_ARN" \
  --query 'Attributes.KmsMasterKeyId' --output text

# Verify delivery logging
aws sns get-topic-attributes --topic-arn "$TOPIC_ARN" \
  --query 'Attributes.SQSFailureFeedbackRoleArn' --output text

# Test publish
aws sns publish \
  --topic-arn "$TOPIC_ARN" \
  --message '{"test": true}'
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| S3 access policy | Missing aws:SourceArn | Principal:* + aws:SourceArn | Without the condition, any account can publish (message injection). aws:SourceArn is set by the S3 service layer and cannot be forged. |
| Delivery logging | Not configured | SQSFailureFeedbackRoleArn set | Without failure logging, SQS delivery failures are invisible. SNS silently drops messages after retry exhaustion. |
| Filter policy | Not set | event_type filter on SQS sub | Without filtering, the SQS queue receives ALL events including ones it cannot process — wasted throughput. |
| KMS key type | Not verified | AWS-managed (same-account only) | AWS-managed key blocks cross-account decryption. The skill flags if a cross-account subscriber is present. |
| Subscription confirmation | Manual reminder | Auto-confirm for same-account SQS/Lambda | Same-account SQS and Lambda subscriptions auto-confirm with --return-subscription-arn. HTTP/email require manual confirmation. |
| FIFO subscriber check | N/A | Verified SQS FIFO for FIFO topic | FIFO topics only support SQS FIFO subscribers. The skill flags if a non-SQS endpoint is specified for a FIFO topic. |

---

## Related artifacts

- **Skill definition:** `skills/sns-topic-deployer/SKILL.md`
- **Configuration guide:** `skills/sns-topic-deployer/references/topic-configuration-guide.md`
- **Deployment CLI commands:** `skills/sns-topic-deployer/references/deployment-cli-commands.md`
- **Slash command:** `commands/aws/deploy-sns-topic.md`
- **Eval suite:** `skills/sns-topic-deployer/evals/evals.json`
- **Legacy test cases:** `skills/sns-topic-deployer/eval/test-cases.yaml`
