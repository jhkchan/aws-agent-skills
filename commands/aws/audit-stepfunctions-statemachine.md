---
description: Audit a Step Functions state machine for execution logging coverage (level ALL + includeExecutionData), X-Ray tracing enablement (including the Express-workflow no-op trap), execution-role blast radius (wildcard actions, states:StartExecution chaining, iam:PassRole), and ASL definition validation (missing Catch/Retry on fallible Tasks, missing TimeoutSeconds, unreachable states, cyclic references).
nl_triggers:
  - "audit this state machine"
  - "check Step Functions logging"
  - "is X-Ray tracing enabled"
  - "state machine execution role too broad"
  - "validate ASL definition"
  - "missing Catch block"
  - "Express workflow tracing"
  - "state machine error handling"
  - "unreachable states in ASL"
  - "Step Functions blast radius"
  - "state machine logging gap"
  - "Step Functions observability"
  - "hardening state machine"
  - "ASL audit"
routes_to: stepfunctions-statemachine-auditor
---

# /aws:audit-stepfunctions-statemachine

Activate the `stepfunctions-statemachine-auditor` skill and audit one or
more Step Functions state machine configurations for observability,
security, and ASL correctness.

## What it does

Reads a state machine configuration (Type, LoggingConfiguration,
TracingConfiguration, RoleArn, role policy, and ASL Definition) and
applies the ordered classification logic:

1. Pre-flight type gate — Standard vs Express (affects X-Ray and logging
   semantics; Express silently ignores TracingConfiguration).
2. Logging configuration — `level: ALL` + `includeExecutionData: true`
   is the only passing posture; `OFF`, `ERROR`, or missing execution
   data → NO_LOGGING.
3. Tracing configuration — `enabled: true` on STANDARD is OK; false/absent
   → NO_TRACING; EXPRESS is always NO_TRACING (no-op).
4. IAM execution role blast radius — `Action "*"` on `Resource "*"` is
   admin-equivalent; service wildcards, `states:StartExecution` on `*`,
   and `iam:PassRole` on `*` are OVERPERMISSIVE_ROLE.
5. ASL definition validation — fallible Tasks without Catch/Retry,
   missing TimeoutSeconds, unreachable states, cyclic references without
   exit, Choice without Default → CONFIG_GAP.
6. Aggregation — worst finding wins by precedence:
   OVERPERMISSIVE_ROLE > NO_LOGGING > NO_TRACING > CONFIG_GAP > OK.

Emits a deterministic VERDICT per state machine:

```text
STATE_MACHINE: <arn>
TYPE: STANDARD | EXPRESS
VERDICT: NO_LOGGING | NO_TRACING | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step>
FINDINGS:
  - [NO_LOGGING] <finding description (Step 1)>
  - [OK] <dimensions that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a state machine configuration and ask any of:

- "audit this state machine"
- "is Step Functions logging configured correctly?"
- "is X-Ray tracing actually working?"
- "is the execution role too broad?"
- "validate this ASL definition"
- "does this Task have error handling?"
- "is this Express workflow traced?"

A bare state-machine ARN + any audit verb ("audit this state machine",
"check Step Functions logging") also routes here via the orchestrator.

## Inputs

- A state machine configuration: Type (STANDARD | EXPRESS),
  LoggingConfiguration (level, includeExecutionData), TracingConfiguration
  (enabled), RoleArn, the role's identity policy (and trust policy if
  available), and the ASL Definition.
- For live-account audits: a state-machine ARN. The skill walks
  `aws stepfunctions describe-state-machine` +
  `aws iam get-role-policy` to assemble the inputs above.

## Outputs

- One VERDICT block per state machine (multiple findings aggregate to
  the worst severity by precedence).
- Enumerated FINDINGS list with per-finding verdict token and step
  citation.
- Specific remediation: set logging to ALL with includeExecutionData,
  enable tracing (Standard only), scope the role, add Catch/Retry/Timeout,
  fix unreachable states.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Step Functions observability and security).
- `/aws:audit-iam-least-privilege` for deep analysis of the execution
  role's identity-based policy in isolation.
- `/aws:audit-kms-key-policy` when the state machine interacts with
  encrypted resources (DynamoDB with SSE-KMS, S3 SSE-KMS objects).
