# Diagnostic commands — log-retention-automator

Inventory, audit, and verification CLI moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Step 1: Inventory the current state — CLI

```bash
# List all log groups with current retention
aws logs describe-log-groups \
  --output json \
  --query 'logGroups[*].[logGroupName,retentionInDays,storedBytes]' \
  --region us-east-1

# Identify Never Expire groups (retentionInDays is null/absent)
aws logs describe-log-groups \
  --output json \
  --query 'logGroups[?retentionInDays==`null`].logGroupName' \
  --region us-east-1

# Get tags for a specific group
aws logs list-tags-log-group \
  --log-group-name /aws/lambda/my-function \
  --region us-east-1
```

## Step 10: audit and verify — CLI

```bash
# 1. Check that no Never Expire groups remain (except explicitly exempted)
aws logs describe-log-groups \
  --output json \
  --query 'logGroups[?retentionInDays==`null`].logGroupName' \
  --region us-east-1

# 2. Verify the EventBridge rule is active
aws events describe-rule \
  --name auto-retention-new-log-groups \
  --region us-east-1

# 3. Test: create a test log group and verify auto-retention
aws logs create-log-group \
  --log-group-name /retention-test-$(date +%s) \
  --region us-east-1

# Wait 10 seconds for EventBridge + Lambda
sleep 10

aws logs describe-log-groups \
  --log-group-name-prefix /retention-test- \
  --region us-east-1

# 4. Verify Firehose delivery stream is active (if archival configured)
aws firehose describe-delivery-stream \
  --delivery-stream-name log-archive-prod \
  --query 'DeliveryStreamDescription.DeliveryStreamStatus' \
  --region us-east-1

# 5. CloudTrail audit — verify put-retention-policy calls
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutRetentionPolicy \
  --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date +%Y-%m-%dT%H:%M:%S) \
  --region us-east-1
```
