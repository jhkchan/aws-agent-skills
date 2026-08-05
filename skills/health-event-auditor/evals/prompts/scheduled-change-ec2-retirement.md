# Eval prompt: scheduled-change-ec2-retirement

Audit the following AWS Health event for operational exposure. Emit the
standard VERDICT block (EVENT, VERDICT, REASON, FINDINGS, REMEDIATION).

Account posture:
  Support plan: Enterprise
  AWS Region (API endpoint): us-east-1
  Health Organizational View: enabled
  EventBridge rule for aws.health: present

Event id: arn:aws:health:us-east-1::event/AWS_EC2_INSTANCE/AWS_EC2_INSTANCE_RETIREMENT_SCHEDULED/scheduled-change-ec2-retirement
Event metadata:
  eventTypeCategory: scheduledChange
  eventStatus: upcoming
  service: EC2
  eventTypeCode: AWS_EC2_INSTANCE_RETIREMENT_SCHEDULED
  region: us-east-1
  startTime: 2026-08-11T00:00:00Z
  lastUpdatedTime: 2026-08-01T12:00:00Z
  eventScopeCode: ACCOUNT_SPECIFIC

Affected entities:
  - entityArn: arn:aws:ec2:us-east-1:111111111111:instance/i-scheduled-change-ec2-retirement
    entityValue: i-scheduled-change-ec2-retirement
    statusCode: UNIMPAIRED
    region: us-east-1

Event description (en_US):
  Your instance i-scheduled-change-ec2-retirement is scheduled for
  retirement on 2026-08-11. The underlying host will be decommissioned.
  Action required: stop and start the instance to migrate it to a new
  host before the retirement window.
