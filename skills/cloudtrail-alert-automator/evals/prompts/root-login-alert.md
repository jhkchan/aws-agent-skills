# Eval prompt: root-login-alert

Design a CloudTrail alerting automation for root console login detection.
Emit the standard ALERT block (RULE, ENRICHMENT, ROUTING, DEDUP,
SUPPRESSION, VERDICT, TEMPLATE).

Design reference: root-login-alert
Account: 111111111111
Region: us-east-1

CloudTrail: management-events trail, multi-region, enabled.
Event to alert on: ConsoleLogin by root user (successful only).
Notification targets: SNS (CRITICAL tier), Security Hub, Slack #sec-incidents.
Suppression: root events must NEVER be suppressed.
Dedup window: 0 minutes (every root login independently alerted).
