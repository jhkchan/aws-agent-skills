# Eval: ou-share-with-delegated-admin

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — OU share with delegated admin and caller region cited

## Prompt

Provision portfolio "Data Products" by "Data Platform" in
us-east-1, account 111111111111. Product: "Aurora Reader
Endpoint" (CLOUD_FORMATION_TEMPLATE) from
https://s3.amazonaws.com/data-templates/aurora-reader.yaml
(validated). Version v2.1.0. Constraints: LAUNCH STACK-based
with sc-launch-aurora-role (exists, scoped to rds:*), TAG_UPDATE
NOT_ALLOWED. TagOptions: CostCenter=data-9999 at portfolio
level. Share with OU ou-abc1-abcdef (Organizations enabled,
delegated admin account 222222222222 enabled for
servicecatalog.amazonaws.com).
