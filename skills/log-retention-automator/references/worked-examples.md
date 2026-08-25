# Worked examples — log-retention-automator

Code patterns and example outputs moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Step 3: batch apply with rate limiting (Python)

Batch automation pattern (with rate limiting — CloudWatch Logs
throttles at ~5-10 put-retention-policy/sec):

```python
import boto3, time

logs = boto3.client('logs')

def apply_retention(log_group_name, retention_days):
    try:
        logs.put_retention_policy(
            logGroupName=log_group_name,
            retentionInDays=retention_days
        )
        print(f"OK: {log_group_name} -> {retention_days}d")
    except logs.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ThrottlingException':
            time.sleep(2)
            apply_retention(log_group_name, retention_days)
        else:
            print(f"ERROR: {log_group_name} -> {e}")

# Iterate with pagination
paginator = logs.get_paginator('describe_log_groups')
for page in paginator.paginate():
    for lg in page['logGroups']:
        name = lg['logGroupName']
        tags = logs.list_tags_log_group(logGroupName=name).get('tags', {})
        env = tags.get('Environment', 'untagged')
        tier = TIER_MAP.get(env, DEFAULT_RETENTION)
        apply_retention(name, tier)
        time.sleep(0.2)  # Stay under throttle limit
```

## Step 4: auto-retention Lambda handler

Lambda handler (auto-retention on CreateLogGroup):

```python
import boto3, json, os

logs = boto3.client('logs')

TIER_MAP = json.loads(os.environ['TIER_MAP'])
DEFAULT_RETENTION = int(os.environ['DEFAULT_RETENTION'])

def lambda_handler(event, context):
    # Extract log group name from CloudTrail event
    log_group_name = event['detail']['requestParameters']['logGroupName']

    # Check for tags (may not be set yet — CreateLogGroup may not include tags)
    try:
        tags_resp = logs.list_tags_log_group(logGroupName=log_group_name)
        env = tags_resp['tags'].get('Environment', 'untagged')
    except Exception:
        env = 'untagged'

    retention = TIER_MAP.get(env, DEFAULT_RETENTION)

    logs.put_retention_policy(
        logGroupName=log_group_name,
        retentionInDays=retention
    )

    print(f"Applied {retention}d retention to {log_group_name} (env={env})")
    return {'statusCode': 200, 'logGroup': log_group_name, 'retention': retention}
```

## Step 8: daily sweep rule and Lambda

```bash
aws events put-rule \
  --name daily-retention-sweep \
  --schedule-expression "rate(1 day)" \
  --region us-east-1
```

```python
# Lambda: sweep for Never Expire groups
def sweep_handler(event, context):
    paginator = logs.get_paginator('describe_log_groups')
    for page in paginator.paginate():
        for lg in page['logGroups']:
            if lg.get('retentionInDays') is None:
                name = lg['logGroupName']
                logs.put_retention_policy(
                    logGroupName=name,
                    retentionInDays=DEFAULT_RETENTION
                )
                print(f"Sweep: applied {DEFAULT_RETENTION}d to {name}")
                time.sleep(0.2)
```

## Worked example — REVIEW_REQUIRED, missing tag schema

```text
RETENTION: staging-retention-setup
LOG_GROUP: account-wide (80 groups)
POLICY:
  - Tag map: Environment=staging -> 30d (but 52 of 80 groups lack the Environment tag)
  - Tier: 30 (allowed)
  - Default: TBD — no account-level default configured
TRIGGER:
  - Existing: NONE
  - New: EventBridge CreateLogGroup rule not yet deployed
ARCHIVAL: NONE
VERDICT: REVIEW_REQUIRED
GAP: 52 of 80 log groups lack the Environment tag. The tag-based retention map will miss them. Options: (1) tag all groups first (aws logs tag-log-group), (2) set an account-level default (14d recommended) that applies to untagged groups. Also, the EventBridge CreateLogGroup rule is not deployed — new groups will still default to Never Expire.
TEMPLATE: (deploy after tag coverage is resolved)
```
