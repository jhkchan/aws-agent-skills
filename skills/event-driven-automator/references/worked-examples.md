# Worked Examples

Blocks moved verbatim from SKILL.md in the agentskills.io progressive-disclosure
restructure. No content changed; load when a SKILL.md pointer stub applies.

## Step 5: Reference idempotent-consumer Lambda pattern (moved from SKILL.md)

```python
import boto3, hashlib, json
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('event-dedup')

def lambda_handler(event, context):
    # Compute a deterministic dedup key from event fields
    key = hashlib.sha256(json.dumps({
        'source': event['source'],
        'detail-type': event['detail-type'],
        'id': event.get('id'),  # EventBridge assigns a unique id per event
    }, sort_keys=True).encode()).hexdigest()

    try:
        table.put_item(
            Item={'dedup_key': key, 'ts': event['time']},
            ConditionExpression='attribute_not_exists(dedup_key)'
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        # Already processed — skip
        return {'status': 'duplicate'}

    # ... actual processing ...
```

## Worked example — MANUAL_STEP_REQUIRED, missing idempotency (moved from SKILL.md)

```text
ARCHITECTURE: codebuild-failure-notify
BUS: default
PATTERN: source=aws.codebuild, detail-type=CodeBuild Build State Change, detail.build-status=FAILED
TARGETS:
  - Lambda notify-oncall (no idempotency check, no DLQ)
RETRY: defaults (185 attempts / 24h) — too aggressive for a notification
SAFETY: NO DLQ; idempotency NOT IMPLEMENTED (CodeBuild emits multiple state-change events per build); circular-dep check PASS.
AUDIT: NO CloudWatch alarm on DLQ.
VERDICT: MANUAL_STEP_REQUIRED
GAP: (1) No DLQ on Lambda target — failed invocations are silently dropped. (2) No idempotency — CodeBuild emits multiple state-change events per build (STARTED, IN_PROGRESS, FAILED), and each FAILED state can fire more than once during retries; the Lambda will post duplicate Slack notifications. (3) No CloudWatch alarm on DLQ. Implement dedup on detail.build-id + detail.build-status in DynamoDB before enabling.
TEMPLATE: (incomplete — fix GAPs first)
```
