---
name: troubleshoot-ecs-task
description: >-
  Slash command for the ecs-task-troubleshooter skill. Diagnoses why
  AWS ECS tasks fail to start, transition to STOPPED immediately, fail
  health checks, crash-loop, cannot pull container images, or fail
  placement — via the stoppedReason-first decision tree covering ENI
  attachment, exit codes, memory/OOM, ALB/target-group health check
  config, application errors in CloudWatch Logs, ECR repo policy, and
  capacity/attribute constraints. Emits ROOT_CAUSE_IDENTIFIED |
  INSUFFICIENT_DATA with the specific failure category and offending
  config element.
skill: ecs-task-troubleshooter
family: Compute
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:troubleshoot-ecs-task

Invoke the `ecs-task-troubleshooter` skill to diagnose an ECS task
lifecycle failure.

Read the skill at `skills/ecs-task-troubleshooter/SKILL.md` and follow
its diagnostic procedure to identify the root cause.

## When to use

- An ECS task stays in PROVISIONING / PENDING forever.
- An ECS task transitions to STOPPED immediately after RUNNING.
- An ECS task reports `ResourceInitializationError` (ENI / subnet IP).
- An ECS task reports `CannotPullContainerError` (ECR auth / endpoint /
  size).
- An ECS task reports `EC2InstanceStateError` (deregistered instance).
- An ECS task fails ALB or ECS health checks.
- An ECS task keeps restarting (crash loop).
- An ECS service reports it "was unable to place a task" or
  "No ContainerInstances were found".
- The deployment circuit breaker has fired and you need the underlying
  cause.

## Invocation

```
/aws:troubleshoot-ecs-task <cluster / service / symptom description>
```

The skill will:

1. Read the `stoppedReason` and `containers[].reason` from
   `describe-tasks` — these strings route to the diagnostic branch.
2. Request the failing task ARN and `describe-tasks` output if missing.
3. Walk the category-specific diagnostic tree (10 steps covering ENI /
   subnet IP, ECR auth / endpoint / size, capacity / placement,
   essential-container exit + exit-code analysis, task role vs
   execution role, health check, circuit breaker, platform version,
   definition validation).
4. Cross-reference with CloudWatch Logs, `describe-task-definition`,
   `describe-target-health`, `describe-container-instances`,
   `describe-capacity-providers`, and `describe-vpc-endpoints` as
   required by the category.
5. Verify the proposed fix with a one-off task or simulator run before
   applying.
6. Emit the standard diagnostic block.

## Output shape

```text
TARGET: <cluster / service / task ARN or unknown>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
ROOT_CAUSE: <category name — RESOURCE_INIT_ENI / RESOURCE_INIT_SUBNET_IP /
  IMAGE_PULL_AUTH / IMAGE_PULL_ENDPOINT / IMAGE_PULL_SIZE /
  CAPACITY_PLACEMENT / CAPACITY_DEREGISTERED / CONFIG_TASK_ROLE /
  CONFIG_EXECUTION_ROLE / CONFIG_DEFINITION_INVALID / HEALTH_CHECK /
  OOM / CIRCUIT_BREAKER / PLATFORM_VERSION / UNKNOWN>
REASON: <1-3 sentences naming the failing config element + the probe
  that proves it>
EVIDENCE:
  - <observed signal — stoppedReason / containers[].reason / exitCode
    / service event / metric>
  - <failing probe — CLI command and the specific output line>
  - <passing probes — categories ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before any state-changing CLI, emit and await operator
  approval.
```

## Pre-flight

The skill requires the task ARN (or service+cluster name so it can be
located), the task's last observed state, and ideally the
`stoppedReason` and `containers[].exitCode` / `containers[].reason`
from `describe-tasks`. If the task ARN is unknown, the skill will run
`aws ecs list-tasks` to surface recently-stopped tasks for the
service. If the user provides only a vague symptom with no identifying
info, the skill emits `INSUFFICIENT_DATA`.

## References

- Skill: `skills/ecs-task-troubleshooter/SKILL.md`
- Reference: `skills/ecs-task-troubleshooter/references/failure-decision-tree.md`
- Reference: `skills/ecs-task-troubleshooter/references/diagnostic-commands.md`
- AWS docs: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/troubleshooting.html
