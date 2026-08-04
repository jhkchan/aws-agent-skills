---
description: Audit an ECS task definition for privileged containers, plaintext secrets in environment variables, host network mode, root-user execution, and missing resource limits (CPU, memory, logging).
nl_triggers:
  - "audit this ECS task definition"
  - "check ECS task for privileged container"
  - "ECS secrets in environment variables"
  - "ECS host network mode"
  - "is my container running as root"
  - "ECS resource limits missing"
  - "harden my Fargate task"
  - "ECS container security audit"
  - "privileged ECS container"
  - "ECS task definition review"
  - "check ECS task for secrets leak"
  - "ECS non-root user"
  - "readonlyRootFilesystem ECS"
  - "ECS linux capabilities"
routes_to: ecs-task-definition-auditor
---

# /aws:audit-ecs-task-definition

Activate the `ecs-task-definition-auditor` skill and audit one or more ECS
task definitions for security exposure.

## What it does

Reads an ECS task definition JSON (containerDefinitions + networkMode +
launch-type metadata) and applies the ordered classification logic:

1. Pre-flight metadata gate — short-circuit Fargate-only tasks (privileged
   is ignored), validate network-mode compatibility.
2. Privileged mode — `privileged: true` on EC2 is PRIVILEGED (full host
   kernel access). On Fargate it is CONFIG_GAP (silent no-op).
3. Secret leak — scan `environment` array for secret-pattern keys
   (PASSWORD, SECRET, TOKEN, API_KEY, etc.) that should be in the
   `secrets` array (Secrets Manager / SSM SecureString).
4. Insecure configuration — `networkMode: host` (no network isolation),
   `user: root` / omitted user (runs as UID 0), dangerous capabilities
   (SYS_ADMIN, NET_ADMIN, SYS_PTRACE), writeable root filesystem.
5. Config gap — missing resource limits (task/container-level CPU/memory),
   missing logConfiguration, missing executionRoleArn.
6. Aggregation — worst verdict wins (PRIVILEGED > SECRET_LEAK >
   INSECURE > CONFIG_GAP > OK).

Emits a deterministic VERDICT per task definition:

```text
TASK: <family:revision>
VERDICT: PRIVILEGED | SECRET_LEAK | INSECURE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step>
FINDINGS:
  - [PRIVILEGED] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an ECS task definition JSON and ask any of:

- "audit this ECS task definition"
- "is my ECS container privileged?"
- "check for secrets in environment variables"
- "is my container running as root?"
- "ECS resource limits missing"
- "harden my Fargate task"

A bare task definition family name or ARN + any audit verb ("audit this
task", "check this task definition") also routes here via the orchestrator.

## Inputs

- An ECS task definition document (JSON), pasted inline or referenced by
  file path. Include `containerDefinitions`, `networkMode`, `family`, and
  `requiresCompatibilities` at minimum.
- For live-account audits: a task definition family name or ARN. The skill
  will use `aws ecs describe-task-definition` to fetch the canonical JSON.

## Outputs

- One VERDICT block per task definition (multiple findings aggregate to
  the worst severity).
- Enumerated FINDINGS list with per-finding verdict and step citation.
- Specific remediation: set privileged: false, move secrets to secrets
  array, change network mode, set non-root user, add resource limits,
  register new revision.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for ECS compute security).
- `/aws:audit-iam-least-privilege` for IAM policy analysis of the task
  role and execution role attached to ECS tasks.
