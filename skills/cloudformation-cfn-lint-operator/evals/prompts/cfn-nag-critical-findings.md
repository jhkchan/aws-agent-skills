# Eval: cfn-nag-critical-findings

**Difficulty:** easy
**Branch:** REVIEW_REQUIRED — cfn-nag finds 2 CRITICAL findings: IAM policy with Resource:* and S3 bucket without encryption; deployment blocked

## Prompt

Validate my CloudFormation template template.yaml for stack
my-app-stack in us-east-1. The template has an IAM role with
Resource: "*" in its managed policy and an S3 bucket without
encryption. Run cfn-lint, validate-template, and cfn-nag.
