---
name: troubleshoot-ecs-task
description: >-
  Slash command for the ecs-task-troubleshooter skill. Diagnoses why
  AWS ECS tasks fail to start, transition to STOPPED immediately, fail
  health checks, crash-loop, cannot pull container images, or fail
  placement — via the symptom-to-cause decision tree covering ENI
  attachment, exit codes, memory/OOM, ALB/target-group health check
  config, application errors in CloudWatch Logs, ECR repo policy, and
  capacity/attribute constraints. Emits ROOT_CAUSE_FOUND |
  NEED_MORE_INFO | ESCALATE with the specific failure category and
  offending config element.
skill: ecs-task-troubleshooter
family: Compute
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
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
- An ECS task fails ALB or ECS health checks.
- An ECS task keeps restarting (crash loop).
- An ECS task cannot pull a container image (`CannotPullContainerError`).
- An ECS service reports it "was unable to place a task" or
  "No ContainerInstances were found".
- The deployment circuit breaker has fired and you need the underlying
  cause.

## Invocation

```
/aws:troubleshoot-ecs-task <cluster / service / symptom description>
```

The skill will:

1. Identify the symptom category (PROVISIONING_STUCK,
   ESSENTIAL_CONTAINER_EXIT, OOM, HEALTH_CHECK, CRASH_LOOP,
   IMAGE_PULL, PLACEMENT).
2. Request the failing task ARN and `describe-tasks` output.
3. Walk the category-specific diagnostic tree.
4. Cross-reference with CloudWatch Logs, `describe-task-definition`,
   `describe-target-health`, and `describe-container-instances` as
   required by the category.
5. Map to the common root-cause catalog (8 patterns covering ~90% of
   ECS failures).
6. Verify the proposed fix with a one-off task or simulator run before
   applying.
7. Emit the standard VERDICT block.

## Output shape

```text
INCIDENT: <cluster / service / task ARN>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <category name> — <specific failing config element>
EVIDENCE:
  - <describe-tasks signal>: <value>
  - <CloudWatch Logs / describe-services / describe-target-health signal>: <value>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION: <specific config change + verification command>
```

## Pre-flight

The skill requires the task ARN (or service+cluster name so it can be
located), the task's last observed state, and ideally the
`stoppedReason` and `containers[].exitCode` / `containers[].reason`
from `describe-tasks`. If the task ARN is unknown, the skill will run
`aws ecs list-tasks` to surface recently-stopped tasks for the
service. If the user provides only a vague symptom with no identifying
info, the skill emits `NEED_MORE_INFO`.

## References

- Skill: `skills/ecs-task-troubleshooter/SKILL.md`
- Reference: `skills/ecs-task-troubleshooter/references/failure-decision-tree.md`
- Reference: `skills/ecs-task-troubleshooter/references/diagnostic-commands.md`
- AWS docs: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/troubleshooting.html
