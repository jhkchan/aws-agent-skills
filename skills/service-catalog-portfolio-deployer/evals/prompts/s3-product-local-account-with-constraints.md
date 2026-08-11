# Eval: s3-product-local-account-with-constraints

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — STACK-based LAUNCH constraint with sc-launch-s3-role, all constraints and TagOptions configured, local account only

## Prompt

Create a Service Catalog portfolio "Curated S3 Products" by
ProviderName "Platform Governance" in us-east-1,
account 111111111111. Product: "Curated S3 Bucket"
(CLOUD_FORMATION_TEMPLATE) loaded from
https://s3.amazonaws.com/platform-templates-us-east-1/s3-bucket.yaml
(validated, accessible). Version v1.0.0. Constraints: LAUNCH
STACK-based with role sc-launch-s3-role (exists, scoped to s3:*
with iam:PassRole tag condition), TAG_UPDATE NOT_ALLOWED,
NOTIFICATION to SNS topic
arn:aws:sns:us-east-1:111111111111:sc-launch-events (exists).
TagOptions: CostCenter=platform-1234 + Owner=platform-governance
bound at portfolio level. Local account only (no share).
