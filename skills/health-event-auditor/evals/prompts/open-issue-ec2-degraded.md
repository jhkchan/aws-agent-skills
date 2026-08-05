# Eval prompt: open-issue-ec2-degraded

Audit the following AWS Health event for operational exposure. Emit the
standard VERDICT block (EVENT, VERDICT, REASON, FINDINGS, REMEDIATION).

Account posture:
  Support plan: Business
  AWS Region (API endpoint): us-east-1
  Health Organizational View: enabled
  EventBridge rule for aws.health: present

Event id: arn:aws:health:us-east-1::event/AWS_EC2_INSTANCE/AWS_EC2_INSTANCE_DEGRADED_PERFORMANCE/open-issue-ec2-degraded
Event metadata:
  eventTypeCategory: issue
  eventStatus: open
  service: EC2
  eventTypeCode: AWS_EC2_INSTANCE_DEGRADED_PERFORMANCE
  region: us-east-1
  startTime: 2026-08-04T09:00:00Z
  lastUpdatedTime: 2026-08-05T03:30:00Z
  eventScopeCode: ACCOUNT_SPECIFIC

Affected entities:
  - entityArn: arn:aws:ec2:us-east-1:111111111111:instance/i-open-issue-ec2-degraded-1
    entityValue: i-open-issue-ec2-degraded-1
    statusCode: IMPAIRED
    region: us-east-1
  - entityArn: arn:aws:ec2:us-east-1:111111111111:instance/i-open-issue-ec2-degraded-2
    entityValue: i-open-issue-ec2-degraded-2
    statusCode: IMPAIRED
    region: us-east-1
