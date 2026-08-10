---
name: deploy-stepfunctions-statemachine
description: >-
  Slash command for the stepfunctions-statemachine-deployer skill. Provisions
  production-grade AWS Step Functions state machines with correct type
  selection (Standard vs Express), ASL definitions, service integrations
  (Lambda, DynamoDB, SQS, ECS, Glue, Bedrock), Retry/Catch error handling,
  Inline vs Distributed Map, IAM least-privilege role, and Express logging.
  Emits READY_TO_DEPLOY | PREREQUISITES_MISSING.
skill: stepfunctions-statemachine-deployer
family: AppIntegration
task_type: deploy
verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
---

# /aws:deploy-stepfunctions-statemachine

Invoke the `stepfunctions-statemachine-deployer` skill to produce a
deployment plan for a production-grade AWS Step Functions state machine.

## When to use

- Provisioning a new Standard or Express state machine.
- Choosing between Standard (exactly-once, ≤1yr, per-transition billing)
  and Express (at-least-once, ≤5min, per-invocation billing).
- Designing an ASL definition with service integrations.
- Building a Distributed Map for large-scale fan-out (S3/DynamoDB
  ItemReader, ItemBatcher, ToleratedFailurePercentage).
- Configuring Retry/Catch error handling for fallible Tasks.
- Scoping the IAM execution role to specific resource ARNs.
- Choosing between sync (`.sync`) and callback (`.waitForTaskToken`)
  integration patterns.
- Wiring an Express sync workflow behind API Gateway.

## Invocation

```
/aws:deploy-stepfunctions-statemachine <deployment specification>
```

The skill will:

1. Validate the deployment spec (name, type, definition, roleArn,
   loggingConfiguration). Emit PREREQUISITES_MISSING on missing required
   fields.
2. Walk the ten-step architecture planning: workflow type selection → ASL
   definition → service integrations → sync/callback pattern → Map state
   design → error handling (Retry + Catch) → input/output processing →
   IAM role scope → logging/tracing → Express invocation mode.
3. Derive the IAM identity policy per-Task by mapping each Resource ARN
   to the corresponding named actions on specific ARNs.
4. Emit a READY_TO_DEPLOY checklist, cost estimate, and ordered
   `aws stepfunctions create-*` + `aws iam *` deploy commands.

## Output shape

```text
STATE_MACHINE_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Name / Type / Definition / Service integrations / Map states /
  Error handling / IAM role / Logging / Tracing
CHECKLIST:
  [x] Workflow type chosen deliberately
  [x] ASL definition validated
  [x] Every fallible Task has Retry AND Catch
  [x] Every Task has explicit TimeoutSeconds
  [x] Resource ARN suffixes match desired semantics
  [x] IAM role scoped to named actions on specific ARNs
  ...
FINDINGS:
  - [INFO] Estimated monthly cost: <breakdown>
  - [WARN] <non-blocking concerns>
DEPLOY_COMMANDS:
  <ordered list of aws stepfunctions + aws iam commands>
```

## Pre-flight

The skill requires the execution role's ARN (with verified trust for
`states.amazonaws.com`) before emitting `READY_TO_DEPLOY`. If the role is
not created, the skill emits `PREREQUISITES_MISSING` rather than
fabricating a role ARN.

## References

- Skill: `skills/stepfunctions-statemachine-deployer/SKILL.md`
- Reference: `skills/stepfunctions-statemachine-deployer/references/asl-states-reference.md`
- Reference: `skills/stepfunctions-statemachine-deployer/references/service-integration-patterns.md`
- AWS docs: https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html
