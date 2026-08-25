# Diagnostic Commands — IAM Access Analyzer Finding Triage

Load-on-demand pre-flight and diagnostic CLI moved verbatim from SKILL.md.

## Pre-flight — verify finding freshness

- **Verify finding freshness:** re-run `aws accessanalyzer list-findings
  --analyzer-arn <arn> --filter '{"status":{"eq":["ACTIVE"]}}'` to confirm
  the finding is still ACTIVE before acting. Stale findings waste effort.

## Pre-flight policy-capture commands (per resource type)

  - S3: `aws s3api get-bucket-policy --bucket <name> --output json >
    /tmp/<name>-policy-backup-$(date +%s).json`
  - KMS: `aws kms get-key-policy --key-id <key-id> --policy-name default >
    /tmp/<key-id>-policy-backup-$(date +%s).json`
  - SQS: `aws sqs get-queue-attributes --queue-url <url>
    --attribute-names Policy --output json >
    /tmp/<queue>-policy-backup-$(date +%s).json`
  - Secrets Manager: `aws secretsmanager get-resource-policy
    --secret-id <id> > /tmp/<secret>-policy-backup-$(date +%s).json`
  - IAM role trust: `aws iam get-role --role-name <name> --query
    'Role.AssumeRolePolicyDocument' --output json >
    /tmp/<role>-trust-backup-$(date +%s).json`
