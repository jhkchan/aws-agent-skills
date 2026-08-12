# Eval prompt: tag-based-retention-prod

Design a tag-based CloudWatch Logs retention automation workflow for
the following environment. Emit the standard RETENTION block (POLICY,
TRIGGER, ARCHIVAL, VERDICT, TEMPLATE).

Design reference: tag-based-retention-prod
Account: 111111111111
Region: us-east-1

Log groups: 150 total, all tagged with Environment (prod=60, staging=40, dev=50)
Current state: all Never Expire
Desired retention: prod=90d, staging=30d, dev=7d
Tags are consistent — no untagged groups.
Pre-deployment validation: completed (5 groups tested per env).

Emit the standard RETENTION block including the tag-to-tier map,
the batch put-retention-policy pattern, and verification steps.
