# Eval prompt: security-hub-missing

Design a CloudTrail alerting automation that integrates with Security Hub.
Emit the standard ALERT block (RULE, ENRICHMENT, ROUTING, DEDUP,
SUPPRESSION, VERDICT, TEMPLATE).

Design reference: security-hub-missing
Account: 111111111111
Region: us-east-1

CloudTrail: management-events trail, multi-region, enabled.
Events: AttachRolePolicy, CreateAccessKey (HIGH severity).
Notification targets: SNS (HIGH tier), Security Hub, Slack #security.
Security Hub status: NOT ENABLED (securityhub describe-hub returns ResourceNotFoundException).
Enrichment: lookup-events configured.
Dedup: 5 minutes.
Suppression: CI/CD role only.
