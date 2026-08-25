# Diagnostic Commands — SNS Delivery Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Account-wide pre-flight commands

```bash
# 1. Topic attributes (FifoTopic, policy, delivery status, KmsMasterKeyId)
aws sns get-topic-attributes --topic-arn <topic-arn> --output json

# 2. All subscriptions on the topic
aws sns list-subscriptions-by-topic --topic-arn <topic-arn> --output json

# 3. Per-subscription attributes (ConfirmationStatus, FilterPolicy,
#    DeliveryPolicy, RawMessageDelivery, SubscriptionRolePolicy)
aws sns get-subscription-attributes \
  --subscription-arn <subscription-arn> --output json

# 4. SNS delivery metrics (per-subscription dimension available)
aws cloudwatch get-metric-statistics --namespace AWS/SNS \
  --metric-name NumberOfNotificationsFailed \
  --dimensions Name=TopicName,Value=<topic-name> \
  Name=Endpoint,Value=<endpoint-url> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json

# 5. For Lambda subscriptions: Lambda errors and throttles
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=<fn> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json
```
