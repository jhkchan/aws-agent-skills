# EventBridge and Lambda Remediation Patterns Reference

Supplementary reference for the GuardDuty Finding Automator skill. Use
when wiring EventBridge rules for GuardDuty findings, designing Lambda
remediation functions, or debugging a broken event-driven pipeline.

## EventBridge event structure for GuardDuty findings

A GuardDuty finding event delivered to EventBridge has this shape:

```json
{
  "version": "0",
  "id": "event-id-uuid",
  "detail-type": "GuardDuty Finding",
  "source": "aws.guardduty",
  "account": "111111111111",
  "time": "2026-08-11T10:00:00Z",
  "region": "us-east-1",
  "resources": [],
  "detail": {
    "finding": {
      "id": "abc123def456...",
      "type": "UnauthorizedAccess:EC2/SSHBruteForce",
      "severity": 7.5,
      "title": "SSH brute force attempted on EC2 instance i-0abc123.",
      "description": "1 SSH brute force attempt was made...",
      "resource": {
        "resourceType": "Instance",
        "instanceDetails": {
          "instanceId": "i-0abc123def456",
          "instanceState": "running",
          "networkInterfaces": [{
            "privateIpAddress": "10.0.1.50",
            "publicIp": "203.0.113.10"
          }]
        }
      },
      "service": {
        "action": {
          "actionType": "NETWORK_CONNECTION",
          "networkConnectionAction": {
            "remoteIpDetails": {
              "ipAddressV4": "198.51.100.42",
              "organization": {"org": "AS12345 Example ISP"}
            },
            "localPortDetails": {"port": 22}
          }
        },
        "eventCount": 1,
        "eventFirstSeen": "2026-08-11T09:55:00Z",
        "eventLastSeen": "2026-08-11T10:00:00Z"
      }
    }
  }
}
```

**Key fields for Lambda logic:**

| Field | Path | Use |
|---|---|---|
| Finding ID | `detail.finding.id` | Deduplication key |
| Finding type | `detail.finding.type` | Action routing |
| Severity | `detail.finding.severity` | Tier branching (float) |
| Resource type | `detail.finding.resource.resourceType` | EC2 vs IAM vs S3 |
| Instance ID | `detail.finding.resource.instanceDetails.instanceId` | SG swap target |
| IAM user | `detail.finding.resource.accessKeyDetails.userName` | Key revocation target |
| Access key ID | `detail.finding.resource.accessKeyDetails.accessKeyId` | Key to revoke |
| Source IP | `detail.finding.service.action.networkConnectionAction.remoteIpDetails.ipAddressV4` | WAF block target |
| Event count | `detail.finding.service.eventCount` | TTP correlation |

## EventBridge rule patterns

### All GuardDuty findings

```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"]
}
```

### Critical/High only (numeric severity)

```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"],
  "detail": {
    "severity": [{"numeric": [">=", 7.0]}]
  }
}
```

**IMPORTANT:** Test the numeric match. Some GuardDuty event serializations
deliver severity as a string. If numeric matching fails, route ALL
findings to Lambda and branch internally.

### Specific finding type

```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"],
  "detail": {
    "type": ["UnauthorizedAccess:EC2/SSHBruteForce"]
  }
}
```

### Multiple finding types

```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"],
  "detail": {
    "type": [
      "CryptoCurrency:EC2/BitcoinTool",
      "CryptoCurrency:EC2/CryptoDomain",
      "Backdoor:EC2/BackdoorAtTask"
    ]
  }
}
```

### Specific resource type

```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"],
  "detail": {
    "resource": {"resourceType": ["Instance"]}
  }
}
```

## Lambda remediation function template

```python
import boto3
import json
import os
from datetime import datetime, timedelta

ec2 = boto3.client('ec2')
iam = boto3.client('iam')
sns = boto3.client('sns')
wafv2 = boto3.client('wafv2')
securityhub = boto3.client('securityhub')
dynamodb = boto3.resource('dynamodb')

ISOLATION_SG = os.environ['ISOLATION_SG_ID']
SNS_TOPIC = os.environ['SNS_TOPIC_ARN']
FINDINGS_TABLE = dynamodb.Table(os.environ['FINDINGS_TABLE_NAME'])

def lambda_handler(event, context):
    finding = event['detail']['finding']
    finding_id = finding['id']
    severity = float(finding['severity'])
    finding_type = finding['type']

    # 1. Deduplicate
    if is_duplicate(finding_id):
        return {'statusCode': 200, 'body': 'Duplicate — already processed'}

    # 2. Route by severity
    if severity >= 9.0:
        action = respond_critical(finding)
    elif severity >= 7.0:
        action = respond_high(finding)
    elif severity >= 4.0:
        action = respond_medium(finding)
    else:
        action = respond_low(finding)

    # 3. Mark processed
    mark_processed(finding_id, action)

    # 4. Security Hub enrichment
    ingest_security_hub(finding, action)

    return {'statusCode': 200, 'body': json.dumps(action)}

def respond_critical(finding):
    """Critical: isolate + snapshot + revoke keys unconditionally."""
    actions = []
    resource_type = finding['resource']['resourceType']

    if resource_type == 'Instance':
        instance_id = finding['resource']['instanceDetails']['instanceId']
        actions.append(isolate_instance(instance_id))
        actions.append(snapshot_instance(instance_id))

    # Revoke IAM keys if present
    if 'accessKeyDetails' in finding['resource']:
        key_id = finding['resource']['accessKeyDetails']['accessKeyId']
        user = finding['resource']['accessKeyDetails']['userName']
        actions.append(revoke_key(user, key_id, force=True))

    # WAF block source IP if present
    source_ip = extract_source_ip(finding)
    if source_ip:
        actions.append(waf_block_ip(source_ip))

    notify(finding, actions, page_on_call=True)
    return {'tier': 'critical', 'actions': actions}

def respond_high(finding):
    """High: conditional containment."""
    actions = []
    resource_type = finding['resource']['resourceType']

    if resource_type == 'Instance':
        instance_id = finding['resource']['instanceDetails']['instanceId']
        actions.append(isolate_instance(instance_id))

    if 'accessKeyDetails' in finding['resource']:
        key_id = finding['resource']['accessKeyDetails']['accessKeyId']
        user = finding['resource']['accessKeyDetails']['userName']
        actions.append(revoke_key(user, key_id, force=False))  # Check last-used

    notify(finding, actions, page_on_call=True)
    return {'tier': 'high', 'actions': actions}

def respond_medium(finding):
    """Medium: notify only, no containment."""
    notify(finding, [], page_on_call=False)
    return {'tier': 'medium', 'actions': []}

def respond_low(finding):
    """Low: log only."""
    print(f"Low-severity finding logged: {finding['id']} type={finding['type']}")
    return {'tier': 'low', 'actions': []}
```

## Lambda IAM role policy

Minimum permissions for the remediation Lambda:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:ModifyNetworkInterfaceAttribute",
        "ec2:DescribeInstances",
        "ec2:DescribeNetworkInterfaces",
        "ec2:CreateSnapshot",
        "ec2:CreateTags"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:UpdateAccessKey",
        "iam:GetAccessKeyLastUsed",
        "iam:ListAccessKeys"
      ],
      "Resource": "arn:aws:iam::*:user/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:*:*:guardduty-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "wafv2:GetIPSet",
        "wafv2:UpdateIPSet"
      ],
      "Resource": "arn:aws:wafv2:*:*:ipset/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "securityhub:BatchImportFindings"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/guardduty-*"
    }
  ]
}
```

## Common EventBridge + Lambda failures

| Failure | Root cause | Fix |
|---|---|---|
| Lambda not triggered | Rule pattern does not match event serialization | Test with sample event; route all findings to Lambda and filter internally |
| Lambda times out | Default 3-second timeout too short for EC2/IAM API calls | Set timeout to 60 seconds minimum |
| Lambda re-processes same finding | No deduplication on finding ID | Add DynamoDB dedup table with 7-day TTL |
| `ACCESS_DENIED` on EC2 modify | Lambda role missing `ec2:ModifyNetworkInterfaceAttribute` | Add EC2 permissions to Lambda execution role |
| `ACCESS_DENIED` on IAM update | Lambda role missing `iam:UpdateAccessKey` | Add IAM permissions scoped to `arn:aws:iam::*:user/*` |
| WAF update fails with `WAFOptimisticLockException` | Concurrent updates to same IP set | Retry with exponential backoff; re-fetch LockToken before update |
| Security Hub finding not ingested | ASFF schema mismatch (missing required field) | Validate with ASFF schema before `BatchImportFindings` |
| SNS notification not delivered | Email subscription not confirmed | Use HTTPS or Lambda subscriptions (auto-confirmed) for critical alerts |
| DLQ filling up | Lambda invocation failures exceeding retry limit | Check CloudWatch logs for the root error; fix the Lambda code |

## Cross-account EventBridge forwarding

For multi-account setups, each member account forwards GuardDuty events
to the delegated admin's event bus:

### Member account side

```bash
# EventBridge rule in member account
aws events put-rule \
  --name forward-gd-to-admin \
  --event-pattern '{"source":["aws.guardduty"],"detail-type":["GuardDuty Finding"]}'

# Target: admin account's event bus (requires cross-account role)
aws events put-targets \
  --rule forward-gd-to-admin \
  --targets '[{
    "Id": "admin-bus",
    "Arn": "arn:aws:events:us-east-1:111111111111:event-bus/default",
    "RoleArn": "arn:aws:iam::222222222222:role/EventBridgeCrossAccountRole"
  }]'
```

### Admin account side

```bash
# Allow member account to put events on admin's event bus
aws events put-permission \
  --action events:PutEvents \
  --principal 222222222222 \
  --statement-id AllowMemberAccount222
```

### Member account role (CloudFormation via StackSet)

```yaml
EventBridgeCrossAccountRole:
  Type: AWS::IAM::Role
  Properties:
    AssumeRolePolicyDocument:
      Version: "2012-10-17"
      Statement:
        - Effect: Allow
          Principal:
            Service: events.amazonaws.com
          Action: sts:AssumeRole
    Policies:
      - PolicyName: CrossAccountEventBus
        PolicyDocument:
          Version: "2012-10-17"
          Statement:
            - Effect: Allow
              Action: events:PutEvents
              Resource: arn:aws:events:us-east-1:111111111111:event-bus/default
```

## Lambda concurrency and rate limiting

GuardDuty can emit bursts of findings (e.g., a distributed brute-force
sweep hitting 500 instances). Without concurrency control, 500
simultaneous Lambda invocations exhaust API throttling limits.

**Reserved concurrency configuration:**

```bash
aws lambda put-function-concurrency \
  --function-name guardduty-auto-remediation \
  --reserved-concurrent-invocations 10
```

**SQS buffer pattern (for high-volume accounts):**

```
EventBridge → SQS queue → Lambda (batch size 10, concurrency 10)
```

This batches findings, prevents API throttling, and provides a natural
deduplication layer (SQS `ApproximateFirstReceiveTimestamp` for ordering).
