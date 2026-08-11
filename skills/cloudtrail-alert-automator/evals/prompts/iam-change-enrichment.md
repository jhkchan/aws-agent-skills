# Eval prompt: iam-change-enrichment

Design a CloudTrail alerting automation for security-critical IAM changes
with lookup-events enrichment. Emit the standard ALERT block (RULE,
ENRICHMENT, ROUTING, DEDUP, SUPPRESSION, VERDICT, TEMPLATE).

Design reference: iam-change-enrichment
Account: 111111111111
Region: us-east-1

CloudTrail: management-events trail, multi-region, enabled.
Events to alert on: AttachRolePolicy, DetachRolePolicy, CreatePolicyVersion.
Notification targets: SNS (HIGH tier), Security Hub, Slack #security.
Enrichment: lookup-events for 15-min actor context.
Dedup window: 5 minutes.
Suppression: cicd-deploy-role, CloudFormation StackSet role.
