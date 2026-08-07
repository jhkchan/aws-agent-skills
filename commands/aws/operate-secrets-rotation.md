---
description: Operate AWS Secrets Manager rotation workflows — enable rotation, trigger manual rotation, diagnose failed rotations, recover stuck AWSPENDING versions, update rotation config — with deterministic pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
  - "enable secret rotation"
  - "rotate this secret"
  - "trigger rotation now"
  - "configure rotation Lambda"
  - "rotation Lambda setup"
  - "rotation failed"
  - "AWSPENDING stuck"
  - "credential mismatch after rotation"
  - "RDS password rotation"
  - "rotation schedule cron"
  - "cross-account rotation Lambda"
  - "diagnose rotation failure"
  - "Secrets Manager rotation"
  - "rotation Lambda timeout"
  - "rotation Lambda AccessDeniedException"
routes_to: secrets-rotation-operator
---

# /aws:operate-secrets-rotation

Activate the `secrets-rotation-operator` skill and plan/execute a Secrets
Manager rotation operation with deterministic pre-checks, CONFIRM gate,
and post-verification.

## What it does

Reads a secret configuration plus the intended operation and applies the
priority-ordered pre-check sequence:

1. Pre-flight secret metadata gate — short-circuit replica secrets,
   recovery-window secrets, and KMS key state.
2. Pre-check gate — BLOCKED if any check fails (Lambda deleted/inactive,
   execution-role permission chain broken, KMS decrypt denied, VPC ENI
   unreachable, AWSPENDING stuck with unknown live credential, reserved
   concurrency = 0).
3. READY — emit the exact CLI sequence with all flags populated, the
   expected side-effects (LastRotatedDate advances, new version ID in
   AWSCURRENT, old version moves to AWSPREVIOUS), and the CONFIRM gate
   prompt.
4. Execute behind CONFIRM gate — capture pre-state, execute the CLI,
   tail the Lambda CloudWatch Logs.
5. Post-verification — LastRotatedDate advanced, no version in
   AWSPENDING, target login succeeds, application metric dashboard clean.
   COMPLETED only if ALL post-verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <enable-rotation | trigger-rotation | diagnose-rotation | recover-pending | update-config>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <secret-id> (rotation Lambda: <arn-or-"none">)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait / monitoring command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <schedule, monitoring, caveats>
```

## When to invoke

Paste a secret configuration plus the intended operation, or just
describe the scenario and ask any of:

- "enable rotation on this secret"
- "trigger a manual rotation"
- "the rotation Lambda is timing out"
- "there's a version stuck in AWSPENDING"
- "rotation is failing with AccessDeniedException"
- "set up cross-account rotation Lambda access"
- "verify rotation succeeded"

A bare secret-id + any rotation verb ("rotate this secret", "diagnose
the rotation") also routes here via the orchestrator.

## Inputs

- Secret configuration (`describe-secret` JSON): `RotationEnabled`,
  `RotationLambdaARN`, `RotationRules`, `LastRotatedDate`,
  `VersionIdsToStages`, `KmsKeyId`, `PrimaryRegion`, `DeletedDate`.
- Lambda configuration (`get-function-configuration` JSON): `State`,
  `Timeout`, `VpcConfig`, `ReservedConcurrentExecutions`.
- Lambda resource-based policy (`get-policy` JSON) — verify
  `secretsmanager.amazonaws.com` principal.
- Lambda execution-role policies — verify the permission chain.
- For cross-account: secret resource policy (`get-resource-policy`) and
  KMS key policy.
- CloudWatch Logs error patterns (for diagnose-rotation).

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI sequence, expected duration, expected side-
  effects, and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the new
  AWSCURRENT version ID, application metric verification, monitoring
  recommendations.
- For BLOCKED: the specific failure reason and the remediation step
  (e.g., `lambda update-function-configuration --timeout 30`,
  `lambda put-function-concurrency --reserved-concurrent-executions 5`,
  `lambda add-permission --principal secretsmanager.amazonaws.com`).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 4 Operate specialist for Secrets Manager rotation).
- `/aws:audit-secretsmanager-rotation` for the audit-side counterpart —
  auditing rotation posture across many secrets without changing state.
- `/aws:deploy-secretsmanager-secret` for the deploy-side counterpart —
  provisioning new secrets with rotation pre-wired.
