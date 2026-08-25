# Auto-Tagging via EventBridge + Lambda Reference

Supplementary reference for the Tag Governance Automator skill. Use
when building, debugging, or hardening an auto-tagging pipeline that
stamps tags on resource creation based on creator IAM identity.

## Architecture

```
CloudTrail → EventBridge rule → Lambda (auto-tagger) → Resource Tagging API
                                   ↓
                              CloudWatch Logs (audit)
```

The Lambda derives tag values from:
- `detail.userIdentity.arn` → `Owner`, `CreatorARN`
- `detail.userIdentity.sessionContext.sessionIssuer.arn` → assumed-role ARN
- `detail.sourceIPAddress` → `SourceIP` (optional)
- `detail.recipientAccountId` → `Environment` (via account map)
- `detail.userAgent` → `CreatorTool` (terraform, console, aws-cli)

## EventBridge rule patterns

### EC2 RunInstances

```json
{
  "source": ["aws.ec2"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["ec2.amazonaws.com"],
    "eventName": ["RunInstances"]
  }
}
```

### S3 CreateBucket

```json
{
  "source": ["aws.s3"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["s3.amazonaws.com"],
    "eventName": ["CreateBucket"]
  }
}
```

### Lambda CreateFunction

```json
{
  "source": ["aws.lambda"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["lambda.amazonaws.com"],
    "eventName": ["CreateFunction20150331"]
  }
}
```

### Combined multi-service rule

```json
{
  "source": ["aws.ec2", "aws.s3", "aws.lambda", "aws.rds"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["ec2.amazonaws.com", "s3.amazonaws.com", "lambda.amazonaws.com", "rds.amazonaws.com"],
    "eventName": ["RunInstances", "CreateBucket", "CreateFunction20150331", "CreateDBInstance"]
  }
}
```

## Lambda handler (production-grade)

```python
import boto3, os, json, logging, urllib.parse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

EC2 = boto3.client("ec2")
S3 = boto3.client("s3")
LAMBDA = boto3.client("lambda")
RDS = boto3.client("rds")
ORG = boto3.client("organizations")

ACCOUNT_ENV = json.loads(os.environ.get("ACCOUNT_ENV_MAP", "{}"))

def derive_tags(detail):
    identity = detail.get("userIdentity", {})
    user_arn = identity.get("arn", "unknown")
    user_name = user_arn.split("/")[-1] if "/" in user_arn else user_arn
    # If assumed role, extract role name from sessionIssuer
    if "sessionContext" in identity:
        issuer = identity["sessionContext"].get("sessionIssuer", {})
        if issuer.get("arn"):
            user_arn = issuer["arn"]
            user_name = issuer["arn"].split("/")[-1]
    account_id = detail.get("recipientAccountId", "unknown")
    env = ACCOUNT_ENV.get(account_id, "unknown")
    return [
        {"Key": "Owner", "Value": user_name},
        {"Key": "CreatorARN", "Value": user_arn},
        {"Key": "Environment", "Value": env},
        {"Key": "CreatedVia", "Value": "auto-tagger"},
        {"Key": "CreatedAt", "Value": detail.get("eventTime", "")},
    ]

def tag_ec2(detail, tags):
    items = detail["responseElements"]["instancesSet"]["items"]
    ids = [i["instanceId"] for i in items]
    EC2.create_tags(Resources=ids, Tags=tags)
    return f"tagged {len(ids)} EC2 instances"

def tag_s3(detail, tags):
    bucket = detail["requestParameters"]["bucketName"]
    S3.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": tags})
    return f"tagged S3 bucket {bucket}"

def tag_lambda(detail, tags):
    fn = detail["requestParameters"]["functionName"]
    LAMBDA.tag_resource(Resource=fn, Tags={t["Key"]: t["Value"] for t in tags})
    return f"tagged Lambda function {fn}"

def tag_rds(detail, tags):
    db = detail["responseElements"]["dBInstanceIdentifier"]
    RDS.add_tags_to_resource(ResourceName=f"arn:aws:rds:{detail['awsRegion']}:{detail['recipientAccountId']}:db:{db}", Tags=tags)
    return f"tagged RDS instance {db}"

DISPATCH = {
    ("ec2.amazonaws.com", "RunInstances"): tag_ec2,
    ("s3.amazonaws.com", "CreateBucket"): tag_s3,
    ("lambda.amazonaws.com", "CreateFunction20150331"): tag_lambda,
    ("rds.amazonaws.com", "CreateDBInstance"): tag_rds,
}

def lambda_handler(event, context):
    detail = event["detail"]
    key = (detail.get("eventSource"), detail.get("eventName"))
    handler = DISPATCH.get(key)
    if not handler:
        logger.warning(f"no handler for {key}")
        return {"statusCode": 200, "skipped": True}
    try:
        tags = derive_tags(detail)
        result = handler(detail, tags)
        logger.info(result)
        return {"statusCode": 200, "result": result}
    except Exception as e:
        logger.error(f"failed to tag: {e}")
        raise  # let EventBridge retry (up to 3 times)
```

## Lambda execution role (trust + permissions)

Trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

Permissions policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ec2:CreateTags"],
      "Resource": ["arn:aws:ec2:*:*:instance/*", "arn:aws:ec2:*:*:volume/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutBucketTagging"],
      "Resource": ["arn:aws:s3:::*"]
    },
    {
      "Effect": "Allow",
      "Action": ["lambda:TagResource"],
      "Resource": ["arn:aws:lambda:*:*:function:*"]
    },
    {
      "Effect": "Allow",
      "Action": ["rds:AddTagsToResource"],
      "Resource": ["arn:aws:rds:*:*:db:*"]
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": ["arn:aws:logs:*:*:log-group:/aws/lambda/*"]
    }
  ]
}
```

## Idempotency and retry

EventBridge retries failed invocations up to 3 times (configurable
via the target's `RetryPolicy`). The Lambda MUST be idempotent:

- `ec2:CreateTags` is idempotent — re-tagging with the same key-value
  is a no-op. Safe.
- `s3:PutBucketTagging` is NOT idempotent — it REPLACES the entire
  tag set. If a human added tags between the event and the Lambda
  retry, those tags are lost. Always read existing tags first and
  merge.
- `lambda:TagResource` is additive (idempotent for same keys).
- `rds:AddTagsToResource` is additive (idempotent for same keys).

**S3 merge-safe pattern:**

```python
def tag_s3_safe(bucket, new_tags):
    try:
        existing = S3.get_bucket_tagging(Bucket=bucket)["TagSet"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchTagSet":
            existing = []
        else:
            raise
    merged = {t["Key"]: t["Value"] for t in existing}
    for t in new_tags:
        merged[t["Key"]] = t["Value"]  # new tags override
    S3.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": [
        {"Key": k, "Value": v} for k, v in merged.items()
    ]})
```

## Dead-letter queue

Always configure a DLQ on the EventBridge target to capture events
that exhaust retries:

```bash
aws events put-targets \
  --rule auto-tag-on-create \
  --targets '[{
    "Id": "auto-tagger-lambda",
    "Arn": "arn:aws:lambda:us-east-1:111111111111:function:auto-tagger",
    "DeadLetterConfig": {
      "Arn": "arn:aws:sqs:us-east-1:111111111111:auto-tagger-dlq"
    },
    "RetryPolicy": {"MaximumRetryAttempts": 3, "MaximumEventAgeInSeconds": 300}
  }]'
```

## Cross-account auto-tagging (org-level)

For a single auto-tagger Lambda in the org management account to
receive events from all member accounts:

1. Each member account configures EventBridge to forward to the
   org management account's event bus:
   ```bash
   aws events put-rule --name forward-to-org --event-bus-name default \
     --event-pattern '{"source":["aws.ec2","aws.s3","aws.lambda"]}'
   aws events put-targets --rule forward-to-org \
     --targets '[{"Id":"org-bus","Arn":"arn:aws:events:us-east-1:111111111111:event-bus/default","RoleArn":"arn:aws:iam::222222222222:role/EventBridgeForwardRole"}]'
   ```
2. The org management account's auto-tagger assumes a role in the
   member account to tag resources cross-account.

This pattern reduces Lambda deployment to 1 (org account) instead of
N (per member account), but requires `sts:AssumeRole` per member.

## Verification and monitoring

```bash
# Lambda is firing on creation events
aws logs filter-log-events \
  --log-group-name /aws/lambda/auto-tagger \
  --filter-pattern "tagged" \
  --start-time $(date -v-1H +%s)000

# Verify a specific resource was tagged
aws ec2 describe-tags \
  --filters Name=resource-id,Values=i-0abc123 \
  --query 'Tags[?Key==`Owner`]'

# DLQ depth (events that failed tagging)
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/auto-tagger-dlq \
  --attribute-names ApproximateNumberOfMessages
```

## Step 3: Build EventBridge + Lambda auto-tagging (moved from SKILL.md)

Auto-tagging stamps tags on resource creation so the fleet starts
compliant rather than waiting for remediation. The pattern: CloudTrail
logs the creation API call → EventBridge rule matches → Lambda derives
tags from the event context → Lambda calls the resource-type-specific
tagging API.

EventBridge rule for EC2 RunInstances:

```bash
aws events put-rule \
  --name auto-tag-ec2-on-create \
  --event-pattern '{
    "source": ["aws.ec2"],
    "detail-type": ["AWS API Call via CloudTrail"],
    "detail": {
      "eventSource": ["ec2.amazonaws.com"],
      "eventName": ["RunInstances"]
    }
  }'
```

EventBridge rule for S3 CreateBucket and Lambda CreateFunction:

```bash
aws events put-rule \
  --name auto-tag-on-create-multi \
  --event-pattern '{
    "source": ["aws.s3", "aws.lambda"],
    "detail-type": ["AWS API Call via CloudTrail"],
    "detail": {
      "eventSource": ["s3.amazonaws.com", "lambda.amazonaws.com"],
      "eventName": ["CreateBucket", "CreateFunction20150331"]
    }
  }'
```

Lambda handler (Python, handles EC2 + S3 + Lambda):

```python
import boto3, os, json

EC2 = boto3.client("ec2")
S3 = boto3.client("s3")
LAMBDA = boto3.client("lambda")

# Account ID -> Environment mapping (inject via env or Secrets Manager)
ACCOUNT_ENV = json.loads(os.environ["ACCOUNT_ENV_MAP"])

def lambda_handler(event, context):
    detail = event["detail"]
    source = detail["eventSource"]
    event_name = detail["eventName"]
    identity = detail["userIdentity"]
    user_arn = identity.get("arn", "unknown")
    user_name = user_arn.split("/")[-1] if "/" in user_arn else user_arn
    account_id = detail.get("recipientAccountId", event["account"])
    env = ACCOUNT_ENV.get(account_id, "unknown")
    base_tags = [
        {"Key": "Owner", "Value": user_name},
        {"Key": "CreatorARN", "Value": user_arn},
        {"Key": "Environment", "Value": env},
        {"Key": "CreatedVia", "Value": "auto-tagger"},
        {"Key": "CreatedAt", "Value": detail["eventTime"]},
    ]
    if source == "ec2.amazonaws.com" and event_name == "RunInstances":
        instances = detail["responseElements"]["instancesSet"]["items"]
        ids = [i["instanceId"] for i in instances]
        EC2.create_tags(Resources=ids, Tags=base_tags)
    elif source == "s3.amazonaws.com" and event_name == "CreateBucket":
        bucket = detail["requestParameters"]["bucketName"]
        S3.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": base_tags})
    elif source == "lambda.amazonaws.com":
        fn = detail["requestParameters"]["functionName"]
        LAMBDA.tag_resource(Resource=fn, Tags={t["Key"]: t["Value"] for t in base_tags})
    return {"statusCode": 200, "tagged": True}
```

**Lambda execution role requirements:**
- `ec2:CreateTags` on `arn:aws:ec2:*:*:instance/*`
- `s3:PutBucketTagging` on `arn:aws:s3:::*`
- `lambda:TagResource` on `arn:aws:lambda:*:*:function:*`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

**Trade-off table:**

| Dimension | EventBridge + Lambda | SSM Automation |
|---|---|---|
| Latency | ~seconds | ~minutes |
| Multi-resource type support | Custom branching logic | One document per type |
| Idempotency | Consumer must handle | SSM handles retries |
| Backfill (existing resources) | No — only creation events | Yes — Config-driven remediation |
| Audit trail | CloudTrail + Lambda logs | SSM execution history |
