# Eval: sam-transform-validation

**Difficulty:** medium
**Branch:** OPERATION_COMPLETED — SAM template expanded via sam translate, cfn-lint and cfn-nag run on expanded output, all pass

## Prompt

Validate my SAM template template-sam.yaml for stack
my-serverless-stack in us-east-1. It has Transform:
AWS::Serverless-2016-10-31 with two Serverless::Function
resources. Expand the transform first, then run cfn-lint and
cfn-nag on the expanded template.
