---
description: Provision Step Functions Express Workflows with Express-vs-Standard decision, sync vs async invocation, CloudWatch Logs configuration (level + includeExecutionData), IAM execution role, EventBridge scheduling, Distributed Map, .sync / AWS SDK integrations, idempotency for at-least-once, observability (X-Ray, alarms). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create express workflow"
  - "provision express workflow"
  - "express state machine setup"
  - "step functions express"
  - "sync express execution"
  - "async express workflow"
  - "express workflow logging"
  - "step functions cloudwatch logs"
  - "include_data"
  - "exclude_data"
  - "eventbridge step functions"
  - "distributed map express"
  - "inline map express"
  - "standard to express migration"
  - "at least once step functions"
  - "express idempotency"
  - "sync integration express"
  - "aws sdk integration step functions"
  - "xray tracing step functions"
routes_to: stepfunctions-express-deployer
---

# /aws:deploy-stepfunctions-express

Activate the `stepfunctions-express-deployer` skill and provision
Step Functions Express Workflows and their dependent primitives
with production-grade defaults.

## What it does

The skill walks a 9-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Confirm Express-vs-Standard decision (5-min cap, at-least-once, cost model)
2. Verify workflow duration fits in the 5-minute Express cap
3. Verify all service integrations are Express-compatible (NO `.waitForTaskToken`)
4. Define the ASL with Express-compatible patterns (Distributed Map, .sync, AWS SDK)
5. Create the IAM execution role with least-privilege
6. Configure logging (CloudWatch Logs + level + INCLUDE_DATA / EXCLUDE_DATA)
7. Choose sync (RequestResponse) vs async invocation mode
8. Configure EventBridge scheduling + observability (X-Ray, CloudWatch alarms)
9. Verify every configuration item against actual state

## When to use

- You need an Express workflow (high-volume, < 5 min, at-least-once acceptable).
- You are migrating a Standard workflow to Express (compatibility check).
- You must configure CloudWatch Logs at the correct level for async Express.
- You are fronting an Express workflow with API Gateway sync.
- You are scheduling recurring Express executions via EventBridge.
- You want Distributed Map or Inline Map fan-out on Express.
- You need idempotency for at-least-once delivery on side-effecting integrations.

## How to invoke

### Slash command

```
/aws:deploy-stepfunctions-express
```

Then provide: workflow name, ASL definition (or requirements),
sync/async invocation mode, logging level, and any optional
integrations (Distributed Map, EventBridge schedule, API Gateway).

### Natural language

Any of these routes to the same skill:

- "create an Express workflow"
- "migrate Standard workflow to Express"
- "configure sync Express with API Gateway"
- "attach CloudWatch Logs to async Express"
- "schedule an Express workflow with EventBridge"

### CLI routing

```bash
node cli/bin/cli.js route "create express workflow"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps
pipeline. The orchestrator routes to it when the user wants to
create or harden an Express workflow. The output checklist feeds
into verification pipelines and audit skills
(stepfunctions-execution-troubleshooter for diagnosing execution
failures, stepfunctions-statemachine-auditor for posture review).

## Example

```
You: /aws:deploy-stepfunctions-express

     Provision an Express workflow order-processor in us-east-1,
     account 123456789012. Distributed Map reading from
     my-bucket/input.json, Lambda process-item per item,
     MaxConcurrency 1000. CloudWatch Logs ALL with
     includeExecutionData. IdempotencyKey from $$.Execution.Id.
     EventBridge rate(5 minutes) + alarm on ExecutionsFailed.

Skill:
  EXPRESS_WORKFLOW: order-processor
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Express-vs-Standard decision: EXPRESS (Distributed Map, high-volume)
    [✓] Duration budget: per-item < 1s, MaxConcurrency 1000 fits in 5-min cap
    [✓] No .waitForTaskToken in ASL: verified
    [✓] ASL definition validated: Distributed Map + Lambda + S3 ItemReader
    [✓] IAM execution role: scoped
    [✓] Logging: /aws/states/order-processor, level ALL, includeExecutionData=true
    [✓] Invocation mode: async (EventBridge)
    [✓] EventBridge schedule + alarm: rate(5 minutes) + ExecutionsFailed alarm
    [✓] Idempotency: IdempotencyKey.$: $$.Execution.Id
  VERIFICATION_COMMANDS:
    aws stepfunctions describe-state-machine --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:order-processor
    aws logs describe-log-groups --log-group-name-prefix /aws/states/order-processor
    ...
```

## References

- Skill definition: `skills/stepfunctions-express-deployer/SKILL.md`
- ASL patterns: `skills/stepfunctions-express-deployer/references/express-asl-patterns.md`
- IAM and logging templates: `skills/stepfunctions-express-deployer/references/iam-and-logging-templates.md`
- Eval suite: `skills/stepfunctions-express-deployer/evals/evals.json`
