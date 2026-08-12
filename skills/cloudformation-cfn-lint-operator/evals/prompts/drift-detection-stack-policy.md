# Eval: drift-detection-stack-policy

**Difficulty:** medium
**Branch:** OPERATION_COMPLETED — drift detection returns IN_SYNC, stack policy enforced protecting RDS and S3 resources

## Prompt

Run drift detection on my CloudFormation stack my-infra-stack
in us-east-1. Also enforce a stack policy that protects
AWS::RDS::DBInstance and AWS::S3::Bucket resources from
updates. The stack has no drift.
