# Responders and Organizational View — Reference

This reference details the responder Lambda patterns (Slack, Jira, DR
failover, scale-out, key rotation) and the AWS Health organizational view
setup for multi-account orgs. Use alongside the Health Event Automator
SKILL.md.

## Responder 1 — Jira ticket create

```python
import json, os, urllib.request, boto3

JIRA_BASE = os.environ['JIRA_BASE']
JIRA_USER = os.environ['JIRA_USER']
JIRA_TOKEN = boto3.client('secretsmanager').get_secret_value(
    SecretId=os.environ['JIRA_SECRET_ID']
)['SecretString']

def lambda_handler(event, context):
    detail = event['detail']
    event_arn = detail['eventArn']
    # Dedup: check if a ticket with this eventArn exists
    # (simplified — use Jira JQL search in production)
    summary = f"AWS Health: {detail['eventTypeCategory']} - {detail['eventTypeCode']}"
    description = (
        f"Event ARN: {event_arn}\n"
        f"Service: {detail['service']}\n"
        f"Region: {event['region']}\n"
        f"Status: {detail.get('statusCode')}\n"
        f"Start: {detail.get('startTime')}\n\n"
        f"{detail.get('eventDescription', [{}])[0].get('latestDescription', '')}\n"
    )
    payload = {
        'fields': {
            'project': {'key': os.environ['JIRA_PROJECT']},
            'summary': summary,
            'description': description,
            'issuetype': {'name': 'Incident' if detail['eventTypeCategory'] == 'issue' else 'Task'},
            'labels': ['aws-health', detail['service'].lower(), detail['eventTypeCategory']]
        }
    }
    req = urllib.request.Request(
        f"{JIRA_BASE}/rest/api/3/issue",
        data=json.dumps(payload).encode(),
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Basic ' + __import__('base64').b64encode(
                f"{JIRA_USER}:{JIRA_TOKEN}".encode()).decode()
        }
    )
    resp = urllib.request.urlopen(req)
    return {'statusCode': 200, 'issue_key': json.loads(resp.read())['key']}
```

**Dedup pattern:** Use Jira JQL `labels = "<eventArn>"` before creating.
If a ticket exists, add a comment instead of creating a duplicate.

## Responder 2 — Auto Scaling scale-out

For EC2 host degradation events, scale out the ASG and (optionally) drain
the affected instances:

```python
import boto3, os

autoscaling = boto3.client('autoscaling')

def lambda_handler(event, context):
    detail = event['detail']
    region = event['region']
    # Map region + service to ASG name (via env var or config)
    asg_name = os.environ[f'ASG_NAME_{region.replace("-","_").upper()}']
    
    desc = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
    if not desc['AutoScalingGroups']:
        return {'statusCode': 404, 'error': 'ASG not found'}
    
    asg = desc['AutoScalingGroups'][0]
    current = asg['DesiredCapacity']
    max_cap = asg['MaxSize']
    new_desired = min(current + 2, max_cap)
    
    if new_desired == current:
        return {'statusCode': 200, 'message': 'Already at max capacity'}
    
    autoscaling.update_auto_scaling_group(
        AutoScalingGroupName=asg_name,
        DesiredCapacity=new_desired
    )
    return {'statusCode': 200, 'old_desired': current, 'new_desired': new_desired}
```

**Safety:** Check `MaxSize` headroom before scaling. If `new_desired ==
max_cap`, scale-out is a no-op — alert separately to raise the cap.

## Responder 3 — DR failover trigger (gated)

```python
import boto3, os

sfn = boto3.client('stepfunctions')
DR_STATE_MACHINE = os.environ['DR_STATE_MACHINE_ARN']

def lambda_handler(event, context):
    detail = event['detail']
    # Gate 1: only specific event codes
    if detail['eventTypeCode'] not in [
        'AWS_EC2_INSTANCE_DEGRADATION_REGION_WIDE',
        'AWS_S3_REGION_OUTAGE',
        'AWS_RDS_REGION_OUTAGE'
    ]:
        return {'statusCode': 200, 'skipped': 'event_code_not_regional'}
    # Gate 2: required number of affected entities
    health = boto3.client('health', region_name='us-east-1')
    entities = health.describe_affected_entities(
        filter={'eventArns': [detail['eventArn']]}
    )['entities']
    if len(entities) < int(os.environ['MIN_REGIONAL_ENTITY_THRESHOLD']):
        return {'statusCode': 200, 'skipped': 'below_regional_threshold'}
    # Trigger DR orchestrator
    sfn.start_execution(
        stateMachineArn=DR_STATE_MACHINE,
        input=__import__('json').dumps({
            'event_arn': detail['eventArn'],
            'region': event['region'],
            'affected_entities': [e['entityValue'] for e in entities],
            'trigger': 'health_event'
        })
    )
    return {'statusCode': 200, 'triggered': True, 'entity_count': len(entities)}
```

**Two gates are mandatory:** event code filter + entity count threshold.
A single degraded instance is not a regional outage.

## Responder 4 — Access key rotation (for credential-exposed notifications)

```python
import boto3, os

iam = boto3.client('iam')

def lambda_handler(event, context):
    detail = event['detail']
    if detail['eventTypeCode'] != 'AWS_ACCOUNT_NOTIFICATION_CREDENTIAL_EXPOSED':
        return {'statusCode': 200, 'skipped': 'not_credential_event'}
    # Parse the username from the event description
    desc = detail.get('eventDescription', [{}])[0].get('latestDescription', '')
    # In production, parse username from desc; here we use an env var
    username = os.environ['TARGET_IAM_USER']
    
    keys = iam.list_access_keys(UserName=username)['AccessKeyMetadata']
    deactivated = []
    for k in keys:
        iam.update_access_key(
            UserName=username,
            AccessKeyId=k['AccessKeyId'],
            Status='Inactive'
        )
        deactivated.append(k['AccessKeyId'])
    new_key = iam.create_access_key(UserName=username)['AccessKey']
    # Alert the owner with the new key (via SNS, not in the response body)
    return {'statusCode': 200, 'deactivated': deactivated, 'new_key_id': new_key['AccessKeyId']}
```

**Safety:** Deactivate (not delete) the exposed key. Create a replacement
and notify the owner via a separate secure channel. Never log the secret.

## Responder 5 — Scheduled change lead-time action

For `scheduledChange` events, compute the lead-time action time and create
an EventBridge Scheduler one-time schedule:

```python
import boto3, os, json
from datetime import datetime, timedelta, timezone

scheduler = boto3.client('scheduler')
health = boto3.client('health', region_name='us-east-1')

LEAD_DAYS = int(os.environ['LEAD_DAYS'])  # e.g., 7

def lambda_handler(event, context):
    detail = event['detail']
    if detail['eventTypeCategory'] != 'scheduledChange':
        return {'statusCode': 200, 'skipped': 'not_scheduled_change'}
    
    scheduled_end = detail['scheduledEndTime']
    end_dt = datetime.fromisoformat(scheduled_end.replace('Z', '+00:00'))
    action_time = end_dt - timedelta(days=LEAD_DAYS)
    if action_time < datetime.now(timezone.utc):
        action_time = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    schedule_name = f"health-leadtime-{detail['eventTypeCode']}-{detail['eventArn'][-12:]}"
    scheduler.create_schedule(
        Name=schedule_name,
        ScheduleExpression=f"at({action_time.strftime('%Y-%m-%dT%H:%M:%S')})",
        FlexibleTimeWindow={'Mode': 'OFF'},
        Target={
            'Arn': os.environ['LEADTIME_TARGET_LAMBDA'],
            'RoleArn': os.environ['SCHEDULER_ROLE_ARN'],
            'Input': json.dumps({'event_arn': detail['eventArn']})
        },
        StartDate=datetime.now(timezone.utc),
        EndDate=end_dt
    )
    return {'statusCode': 200, 'action_time': action_time.isoformat()}
```

## Organizational view — full setup

### Step 1: Enable from the management account

```bash
aws health enable-health-service-access-for-organization \
  --profile management-profile
```

### Step 2: Delegate administrator

```bash
aws organizations register-delegated-administrator \
  --account-id 222222222222 \
  --service-principal health.amazonaws.com \
  --profile management-profile
```

### Step 3: In the delegated admin, deploy the org-view rule

```bash
aws events put-rule --name health-org-all \
  --event-pattern '{"source": ["aws.health"]}' \
  --state ENABLED \
  --profile delegated-admin-profile

aws events put-targets --rule health-org-all \
  --targets '[{"Id":"HealthTopic","Arn":"arn:aws:sns:us-east-1:222222222222:health-org-alerts"}]' \
  --profile delegated-admin-profile
```

### Step 4: Verify

```bash
aws health describe-health-service-status --profile delegated-admin-profile
aws health describe-events-for-organization \
  --filter 'eventTypeCategories=[issue]' \
  --query 'events[*].[arn,awsAccountId,service,region]' \
  --output table --profile delegated-admin-profile
```

### Required IAM policy for the delegated admin

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "health:DescribeEventsForOrganization",
        "health:DescribeAffectedEntitiesForOrganization",
        "health:DescribeEntityAggregatesForOrganization",
        "health:DescribeAffectedAccountsForOrganization"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["organizations:Describe*"],
      "Resource": "*"
    }
  ]
}
```

## Common pitfalls

- **Org view is not retroactive.** Events that fired before enablement are
  not visible. Allow ~24h for the first org-view events to appear.
- **Delegated admin must be in us-east-1.** The org-view Health API endpoint
  is `us-east-1` only.
- **EventBridge org rules fire only in the delegated admin.** Member
  accounts still see their own events on their own default bus — pick one
  ingestion path to avoid double-processing.
- **Scheduler max is 1 year.** Long deprecation windows (e.g., API shutdown
  in 18 months) need a recurring schedule or a different mechanism.
