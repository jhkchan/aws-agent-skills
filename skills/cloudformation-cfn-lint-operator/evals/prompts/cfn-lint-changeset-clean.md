# Eval: cfn-lint-changeset-clean

**Difficulty:** hard
**Branch:** OPERATION_COMPLETED — cfn-lint passes, validate-template passes, cfn-nag passes (0 critical), ChangeSet shows 1 Add + 2 Modify with no replacements

## Prompt

Validate my CloudFormation template template.yaml for stack
my-app-stack in us-east-1. Run cfn-lint, validate-template,
cfn-nag, and create a ChangeSet. The template creates an S3
bucket with encryption enabled and a DynamoDB table. No wildcard
IAM. Stack policy protects RDS and S3.
