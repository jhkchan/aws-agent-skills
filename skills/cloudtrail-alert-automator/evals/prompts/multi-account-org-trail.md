# Eval prompt: multi-account-org-trail

Design a multi-account CloudTrail alerting automation via Organizations
trail. Emit the standard ALERT block (RULE, ENRICHMENT, ROUTING, DEDUP,
SUPPRESSION, VERDICT, TEMPLATE).

Design reference: multi-account-org-trail
Organization management account: 111111111111
Member accounts: 222222222222, 333333333333
Region: us-east-1

CloudTrail: Organizations trail in management account, all regions.
Events: root login (all accounts), IAM policy changes (all accounts),
        CloudTrail tampering (all accounts).
Notification targets: per-account SNS routing via cross-account forwarding.
Security Hub: enabled in management account, member accounts via aggregation.
Suppression: per-account CI/CD roles.
