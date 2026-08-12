# Eval prompt: eventbridge-auto-retention

Design an EventBridge-driven auto-retention workflow that catches new
CloudWatch Logs groups at creation time. Emit the standard RETENTION
block (POLICY, TRIGGER, ARCHIVAL, VERDICT, TEMPLATE).

Design reference: eventbridge-auto-retention
Account: 111111111111
Region: us-east-1

Requirement: auto-apply retention to every new CloudWatch Logs
group at creation time. Default for untagged: 14 days.
Existing log groups: 200 total, 120 Never Expire.
Lambda runtime: Python 3.12.
DLQ: SQS.

Emit the standard RETENTION block. Include the EventBridge rule
pattern, Lambda handler, and the default-first strategy for groups
that may not have tags at creation time.
