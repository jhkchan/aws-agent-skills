# Worked Examples — CloudTrail Alert Automation

Load-on-demand artifacts accompanying the primary root-login worked example in
SKILL.md.

Slack webhook payload (sent by SQS-buffered consumer Lambda):

```json
{
  "attachments": [{
    "color": "#FF0000",
    "title": "[CRITICAL] CloudTrail Alert",
    "fields": [
      {"title": "Event", "value": "ConsoleLogin (root)", "short": true},
      {"title": "Actor", "value": "arn:aws:iam::111111111111:root", "short": true},
      {"title": "Source IP", "value": "203.0.113.42", "short": true},
      {"title": "Severity", "value": "CRITICAL", "short": true},
      {"title": "Recent Activity", "value": "3 API calls in last 15 min: ListBuckets, GetUser, ListRoles", "short": false}
    ]
  }]
}
```

Lambda enrichment function (deployed at
`arn:aws:lambda:us-east-1:111111111111:function:cloudtrail-enrichment`):

```python
import json, hashlib, boto3
from datetime import datetime, timedelta, timezone

cloudtrail = boto3.client('cloudtrail')
sns = boto3.client('sns')

SEVERITY_TOPIC = {
    'CRITICAL': 'arn:aws:sns:us-east-1:111111111111:cloudtrail-critical',
    'HIGH': 'arn:aws:sns:us-east-1:111111111111:cloudtrail-high',
    'MEDIUM': 'arn:aws:sns:us-east-1:111111111111:cloudtrail-medium',
    'LOW': 'arn:aws:sns:us-east-1:111111111111:cloudtrail-low',
}

def lambda_handler(event, context):
    detail = event['detail']
    event_name = detail['eventName']
    actor_arn = detail.get('userIdentity', {}).get('arn', 'unknown')

    # CRITICAL: root events are never deduplicated or suppressed
    severity = 'CRITICAL' if detail.get('userIdentity', {}).get('type') == 'Root' else 'HIGH'

    # Enrich with 15-min lookup-events context
    lookback = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    enrichment = {'recent_events': []}
    try:
        resp = cloudtrail.lookup_events(
            LookupAttributes=[{'AttributeKey': 'Username',
                'AttributeValue': detail['userIdentity'].get('userName', 'root')}],
            StartTime=lookback, MaxResults=20)
        enrichment['recent_events'] = [
            {'eventName': e['EventName'], 'eventTime': e['EventTime'].isoformat()}
            for e in resp.get('Events', [])]
    except Exception as e:
        enrichment['lookup_error'] = str(e)

    enrichment.update(severity=severity,
        source_ip=detail.get('sourceIPAddress', 'unknown'),
        region=detail.get('awsRegion', 'unknown'),
        account_id=detail.get('recipientAccountId', detail.get('accountId')))

    topic = SEVERITY_TOPIC[severity]
    msg = json.dumps({'event_name': event_name, 'severity': severity,
        'actor': actor_arn, 'enrichment': enrichment, 'raw_event': detail},
        default=str)[:250000]  # SNS 256 KB cap safety
    sns.publish(TopicArn=topic, Message=msg, Subject=f'[{severity}] {event_name}')
    return {'status': 'alerted', 'severity': severity}
```
