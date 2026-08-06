# Eval prompt: ok-closed-event

Audit the following AWS Health event for operational exposure. Emit the
standard VERDICT block (EVENT, VERDICT, REASON, FINDINGS, REMEDIATION).

Account posture:
  Support plan: Business
  AWS Region (API endpoint): us-east-1
  Health Organizational View: enabled
  EventBridge rule for aws.health: present

Event id: arn:aws:health:us-east-1::event/AWS_EC2/AWS_EC2_OPERATIONAL_ISSUE/ok-closed-event
Event metadata:
  eventTypeCategory: issue
  eventStatus: closed
  service: EC2
  eventTypeCode: AWS_EC2_OPERATIONAL_ISSUE
  region: us-east-1
  startTime: 2026-07-20T08:00:00Z
  lastUpdatedTime: 2026-07-20T11:30:00Z
  endTime: 2026-07-20T11:30:00Z
  eventScopeCode: ACCOUNT_SPECIFIC

Affected entities:
  - entityArn: arn:aws:ec2:us-east-1:111111111111:instance/i-ok-closed-event
    entityValue: i-ok-closed-event
    statusCode: RESOLVED
    region: us-east-1
