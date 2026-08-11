---
description: Provision a Lambda alias with production-grade defaults (published version targeting, traffic shifting, API Gateway stage integration, CloudWatch alarm per alias, provisioned concurrency, SnapStart). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create lambda alias"
  - "deploy lambda alias"
  - "lambda alias"
  - "weighted alias"
  - "traffic shift lambda"
  - "canary deployment lambda"
  - "provisioned concurrency alias"
  - "lambda snapstart alias"
  - "api gateway stage alias"
  - "lambda version alias"
  - "cloudwatch alarm per alias"
  - "lambda alias routing config"
  - "rollback lambda alias"
routes_to: lambda-alias-deployer
---

# /aws:deploy-lambda-alias

Activate the `lambda-alias-deployer` skill and provision a Lambda
alias with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Published version requirement
2. Alias creation (named pointer to version)
3. Traffic shifting (weighted aliases for canary/linear)
4. API Gateway stage integration (alias qualifier)
5. CloudWatch alarm per alias (Resource dimension)
6. Provisioned concurrency on alias
7. Lambda SnapStart (snapshot per version)
8. Recent features

## When to use

- You need to create a Lambda alias for a published version.
- You are shifting traffic between versions (canary or linear).
- You need API Gateway integration with a Lambda alias.
- You want CloudWatch alarms scoped to a specific alias.
- You need provisioned concurrency on an alias.
- You want to enable SnapStart with alias routing.

## When NOT to use

- **Lambda function creation** — use Lambda function deployers.
- **Lambda layer management** — not this skill.
- **EventBridge rule configuration** — use EventBridge operators.
- **Auditing existing Lambda aliases** — use Lambda auditors.

## How to invoke

### Slash command

```
/aws:deploy-lambda-alias
```

Then provide: function name, alias name, version number, traffic
weights (if shifting), API Gateway details, provisioned concurrency
count, SnapStart (yes/no), tags.

### Natural language

Any of these routes to the same skill:

- "create a prod alias for my-function version 5"
- "shift 10% traffic to version 6 on the prod alias"
- "set up provisioned concurrency on the prod alias"
- "enable snapstart and create a staging alias"
- "create a cloudwatch alarm scoped to the prod alias"

### CLI routing

```bash
node cli/bin/cli.js route "create a lambda alias"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps
pipeline. The orchestrator routes to it when the user wants to
create or modify Lambda aliases. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-lambda-alias

     Create a prod alias for my-function version 5. Shift 10%
     traffic to version 6 (canary). Set up provisioned
     concurrency at 10 on the alias. API Gateway abc123 stage
     prod. Account: 123456789012.

Skill:
  LAMBDA_ALIAS: my-function:prod (v5 90%, v6 10%)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Alias: prod → version 5 (90%) + version 6 (10%)
    [✓] Traffic shifting: canary
    [✓] Provisioned concurrency: 10 on alias prod
    [✓] API Gateway: abc123 stage prod → alias prod
  VERIFICATION_COMMANDS:
    aws lambda get-alias --function-name my-function --name prod
    aws lambda get-provisioned-concurrency-config --function-name my-function --qualifier prod
```

## References

- Skill definition: `skills/lambda-alias-deployer/SKILL.md`
- Traffic shifting and concurrency: `skills/lambda-alias-deployer/references/traffic-shifting-and-concurrency.md`
- Provisioning CLI commands: `skills/lambda-alias-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/lambda-alias-deployer/evals/evals.json`
