# Eval prompt: open-issue-partial-resolution

Audit the following AWS Health event for operational exposure. Emit the
standard VERDICT block (EVENT, VERDICT, REASON, FINDINGS, REMEDIATION).

Account posture:
  Support plan: Enterprise
  AWS Region (API endpoint): us-east-1
  Health Organizational View: enabled
  EventBridge rule for aws.health: present

Event id: arn:aws:health:us-east-1::event/AWS_RDS/AWS_RDS_OPERATIONAL_EVENT/open-issue-partial-resolution
Event metadata:
  eventTypeCategory: issue
  eventStatus: open
  service: RDS
  eventTypeCode: AWS_RDS_OPERATIONAL_EVENT
  region: us-east-1
  startTime: 2026-08-04T22:00:00Z
  lastUpdatedTime: 2026-08-05T02:45:00Z
  eventScopeCode: ACCOUNT_SPECIFIC

Affected entities:
  - entityValue: db-open-issue-partial-resolution-a
    statusCode: RESOLVED
    region: us-east-1
  - entityValue: db-open-issue-partial-resolution-b
    statusCode: RESOLVED
    region: us-east-1
  - entityValue: db-open-issue-partial-resolution-c
    statusCode: IMPAIRED
    region: us-east-1
