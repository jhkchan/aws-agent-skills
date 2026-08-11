---
name: operate-appconfig-deployment
description: >-
  Slash command for the appconfig-deployment-operator skill.
  Operates AWS AppConfig deployment lifecycles safely — creates
  applications, environments, and configuration profiles
  (freeform and feature-flag); defines deployment strategies
  (linear or all-at-once, growth factor, deployment duration,
  bake time); starts, monitors, and completes deployments;
  rolls back on CloudWatch alarm; and integrates AppConfig
  Lambda extensions for runtime feature flags and dynamic
  configuration. Runs deterministic pre-checks (application /
  environment existence, profile schema validity, strategy
  sanity, alarm health, IAM), emits the exact start-deployment
  / stop-deployment / rollback CLI behind a CONFIRM gate, and
  emits READY | BLOCKED | COMPLETED with the exact CLI sequence
  and post-verification.
skill: appconfig-deployment-operator
family: Management
task_type: operate
verdict_shape: "READY | BLOCKED | COMPLETED"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:operate-appconfig-deployment

Invoke the `appconfig-deployment-operator` skill to plan or execute
an AppConfig deployment operation.

Read the skill at
`skills/appconfig-deployment-operator/SKILL.md` and follow its
procedure to plan and execute the operation.

## When to use

- Create an AppConfig application, environment, or configuration
  profile (freeform or feature-flag).
- Define a deployment strategy (linear, all-at-once, growth
  factor, deployment duration, bake time, replica multiplier).
- Start, monitor, stop, or roll back a deployment.
- Wire CloudWatch alarms for automatic rollback.
- Adopt the AppConfig Lambda extension for runtime feature flags
  / dynamic configuration without redeploy.
- Integrate AppConfig with CodeDeploy (`AppConfig.50Percent`,
  `AppConfig.Linear20PercentEvery30Minutes`,
  `WITH_TRAFFIC_CONTROL`).
- Diagnose a deployment stuck in `DEPLOYING`, `ROLLING_BACK`,
  `ROLLED_BACK`, or `TERMINATED`.

## Invocation

```
/aws:operate-appconfig-deployment <application / environment / deployment / symptom>
```

The skill will:

1. Capture the operation target (operation type, application id,
   environment id, configuration profile id, strategy id,
   deployment number, region).
2. Run pre-flight: confirm application / environment / profile
   existence, configuration schema validity, deployment strategy
   sanity, rollback alarm health, IAM permissions, KMS
   decryptability, no active `DEPLOYING` deployment.
3. Emit the CLI sequence with all flags populated (start-deployment,
   stop-deployment, create-deployment-strategy,
   create-configuration-profile, Lambda extension layer wiring).
4. Monitor `State` transitions via `get-deployment` at each step
   boundary.
5. On `COMPLETED`, verify `PercentageComplete: 100.00`, rollback
   alarms healthy, and runtime convergence (Lambda extension
   poll, agent poll, or direct `GetConfiguration`).
6. On `ROLLING_BACK` / `ROLLED_BACK` / `TERMINATED`, read
   `EventLog` for the trigger and emit `BLOCKED` with the
   remediation.
7. Emit the standard VERDICT block.

## Output shape

```text
OPERATION: <create-application | create-environment | create-profile | define-strategy | start-deployment | stop-deployment | rollback | describe>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <application-id / environment-id / deployment-number, region>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command>
  2. <poll command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <DEPLOYING | BAKING | COMPLETED | ROLLING_BACK | ROLLED_BACK | TERMINATED>
PERCENTAGE_COMPLETE: <0.00 - 100.00>
```

## Pre-flight

The skill requires the operation type and the application /
environment / configuration profile identifiers. If only a partial
configuration is provided, the skill runs
`aws appconfig list-applications` and
`aws appconfig list-environments` to surface existing resources,
or emits `BLOCKED` with the list of missing inputs for a new
operation.

## References

- Skill: `skills/appconfig-deployment-operator/SKILL.md`
- Reference: `skills/appconfig-deployment-operator/references/deployment-strategies-and-rollback.md`
- Reference: `skills/appconfig-deployment-operator/references/lambda-extension-and-runtime-integration.md`
- AWS docs: https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html
