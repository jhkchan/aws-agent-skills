---
description: Provision an AWS Lambda Layer (zip with dependencies) with production-grade defaults (compatible runtimes, compatible architectures, immutable versioning, cross-account sharing, Powertools / SDK layers). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create lambda layer"
  - "publish lambda layer"
  - "deploy lambda layer"
  - "lambda layer"
  - "lambda layer version"
  - "lambda layer zip"
  - "lambda powertools layer"
  - "lambda sdk layer"
  - "lambda layer compatible runtimes"
  - "lambda layer arm64"
  - "lambda layer cross-account"
  - "lambda layer sharing"
  - "provided.al2 layer"
  - "provided.al2023 layer"
  - "lambda dependencies layer"
routes_to: lambda-layer-deployer
---

# /aws:deploy-lambda-layer

Activate the `lambda-layer-deployer` skill and provision an AWS Lambda
Layer with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Layer vs container image vs function bundle (boundary call)
2. Compatible runtimes (nodejs, python, java, ruby, provided.al2, provided.al2023)
3. Compatible architectures (x86_64, arm64)
4. Layer zip structure (per-runtime path conventions)
5. Layer versioning (immutable versions, LatestVersionArn)
6. Cross-account sharing (resource-based policy)
7. Attaching layers to functions (version ARN)
8. AWS-provided layers (SDK, Powertools)
9. Recent features

## When to use

- You need to create or publish a new Lambda Layer.
- You are packaging dependencies for Lambda (zip with correct path).
- You need to share a layer across accounts.
- You need to pin a layer version to a function.
- You need to deploy AWS Powertools or AWS SDK layers.
- You need to specify compatible runtimes and architectures.
- You want to validate that a layer design meets production baseline.

## When NOT to use

- **Lambda function deployment** (function code, IAM role, triggers) —
  use `lambda-function-deployer` instead.
- **Container-based Lambda images** (ECR-hosted container images up to
  10 GB) — use container image workflows.
- **Auditing Lambda runtime deprecation** — use
  `lambda-runtime-deprecation-auditor`.
- **Lambda cost optimization** — use `lambda-cost-optimizer`.

## How to invoke

### Slash command

```
/aws:deploy-lambda-layer
```

Then provide: layer name, region, runtime(s), architecture(s),
dependencies, zip source, license info, sharing scope (same account
/ cross-account / Organization), and target function(s).

### Natural language

Any of these routes to the same skill:

- "create a Python Lambda Layer with Powertools"
- "publish a Node.js SDK layer for arm64"
- "share my Lambda Layer with another account"
- "set up a Powertools layer for my Lambda functions"
- "create a provided.al2023 layer for my Go binary"

### CLI routing

```bash
node cli/bin/cli.js route "create a lambda layer"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or publish
Lambda Layers. The output checklist feeds into verification pipelines
and downstream audit skills.

## Example

```
You: /aws:deploy-lambda-layer

     Create a Python Lambda Layer named "my-powertools-layer" in
     us-east-1. Include aws-lambda-powertools, boto3, and requests.
     Compatible with python3.10 through python3.13. arm64 only.
     License: MIT. Attach to my-api-fn. Account: 123456789012.

Skill:
  LAMBDA_LAYER: my-powertools-layer
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Layer name: my-powertools-layer (region: us-east-1)
    [✓] Zip structure: python/ (verified path convention)
    [✓] Compatible runtimes: python3.10, python3.11, python3.12, python3.13
    [✓] Compatible architectures: arm64
    [✓] Version: 1 (immutable ARN)
    [✓] Function attachment: my-api-fn → layer version 1
  VERIFICATION_COMMANDS:
    aws lambda get-layer-version --layer-name my-powertools-layer --version-number 1
    aws lambda get-function-configuration --function-name my-api-fn
```

## References

- Skill definition: `skills/lambda-layer-deployer/SKILL.md`
- Runtimes and architectures guide: `skills/lambda-layer-deployer/references/runtimes-and-architectures.md`
- Provisioning CLI commands: `skills/lambda-layer-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/lambda-layer-deployer/evals/evals.json`
