---
description: Deploy an AWS Lambda function with production-grade configuration (least-privilege role, supported runtime, right-sized memory, KMS encryption, VPC, destinations, concurrency, layers, logging, tracing). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create lambda function"
  - "deploy lambda function"
  - "lambda deployment"
  - "lambda configuration"
  - "lambda iam role"
  - "lambda runtime selection"
  - "lambda vpc configuration"
  - "lambda nat gateway"
  - "lambda dead letter queue"
  - "lambda on-failure destination"
  - "lambda provisioned concurrency"
  - "lambda layers"
  - "lambda code signing"
  - "lambda ecr image"
  - "lambda x-ray tracing"
  - "lambda snapstart"
  - "lambda web adapter"
routes_to: lambda-function-deployer
---

# /aws:deploy-lambda-function

Activate the `lambda-function-deployer` skill and deploy a Lambda function
with production-grade configuration.

## What it does

The skill walks a 13-step deployment procedure and emits a
READY_TO_DEPLOY checklist:

1. Execution IAM role (least-privilege, scoped to function resources)
2. Runtime selection (supported, not deprecated)
3. Memory + timeout (right-sized for workload)
4. Environment variables + KMS encryption
5. VPC configuration (private subnets, security group, NAT Gateway)
6. Dead-letter queue / on-failure destination
7. Concurrency (on-demand, reserved, or provisioned)
8. Layers (shared dependencies, max 5)
9. Code signing (regulated environments)
10. Packaging (zip vs ECR container image)
11. Logging (CloudWatch log group with retention)
12. Tracing (X-Ray Active mode)
13. Verification commands

## When to use

- You need to create a new Lambda function with production defaults.
- You are deploying a function to production and want to validate config.
- You need deployment CLI commands or Terraform/SAM templates.
- You want to check for deployment blockers (deprecated runtime, missing
  NAT Gateway, missing IAM role).

## How to invoke

### Slash command

```
/aws:deploy-lambda-function
```

Then provide: function name, runtime, handler, workload type, memory,
timeout, and any optional features (VPC, layers, concurrency, code
signing).

### Natural language

Any of these routes to the same skill:

- "create a Lambda function"
- "deploy a Lambda function to production"
- "set up a Lambda with VPC and NAT Gateway"
- "configure Lambda provisioned concurrency"
- "deploy a Java Lambda with SnapStart"

### CLI routing

```bash
node cli/bin/cli.js route "deploy a lambda function"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline. The
output checklist feeds into verification pipelines and audit skills
(lambda-runtime-deprecation-auditor for post-deployment runtime checks).

## Example

```
You: /aws:deploy-lambda-function

     Deploy a production Lambda "order-processor-prod" in us-east-1.
     Runtime: python3.12. Handler: app.handler. Memory: 512 MB,
     timeout 15s. VPC: subnet-aaa, subnet-bbb, sg-orders. Needs
     DynamoDB + SQS permissions. On-failure destination: order-dlq.
     X-Ray tracing. Log retention: 30 days. Account: 123456789012.

Skill:
  FUNCTION: order-processor-prod
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Execution IAM role — order-processor-exec (DynamoDB + SQS scoped)
    [✓]      Runtime — python3.12 (supported)
    [✓]      Memory — 512 MB
    [✓]      Timeout — 15s
    [✓]      VPC — Private subnets (subnet-aaa, subnet-bbb) + sg-orders
    [✓]      Destination — On-failure SQS (order-dlq)
    [✓]      Logging — /aws/lambda/order-processor-prod, retention 30 days
    [✓]      Tracing — X-Ray Active mode
  VERIFICATION_COMMANDS:
    aws lambda get-function-configuration --function-name order-processor-prod
    aws iam list-attached-role-policies --role-name order-processor-exec
    aws lambda get-function-event-invoke-config --function-name order-processor-prod
    aws logs describe-log-groups --log-group-name-prefix /aws/lambda/order-processor-prod
```

## References

- Skill definition: `skills/lambda-function-deployer/SKILL.md`
- Deployment CLI commands: `skills/lambda-function-deployer/references/deployment-cli-commands.md`
- Runtime and VPC guide: `skills/lambda-function-deployer/references/runtime-and-vpc-guide.md`
- Eval suite: `skills/lambda-function-deployer/evals/evals.json`
