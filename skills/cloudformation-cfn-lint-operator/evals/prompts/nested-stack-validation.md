# Eval: nested-stack-validation

**Difficulty:** medium
**Branch:** OPERATION_COMPLETED — parent and both child templates pass cfn-lint and validate-template independently

## Prompt

Validate my CloudFormation parent template parent-template.yaml
for stack my-platform-stack in us-east-1. It references two
nested stacks: child-network.yaml and child-database.yaml.
Run cfn-lint and validate-template on all three templates.
