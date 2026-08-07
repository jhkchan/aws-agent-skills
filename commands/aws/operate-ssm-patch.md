---
description: Operate SSM Patch Manager workflows — patch baseline authoring, Scan and Install operations, maintenance window task scheduling, and compliance reporting — with deterministic pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
  - "patch this instance"
  - "run AWS-RunPatchBaseline"
  - "scan for missing patches"
  - "install missing patches"
  - "create patch baseline"
  - "custom patch baseline rules"
  - "patch group tag"
  - "schedule patching maintenance window"
  - "diagnose NON_COMPLIANT patch"
  - "Operation=Install"
  - "Operation=Scan"
  - "rate-control patching"
  - "approve after days"
  - "NoReboot patch install"
  - "AWS-ApplyPatchBaseline"
routes_to: ssm-patch-operator
---

# /aws:operate-ssm-patch

Activate the `ssm-patch-operator` skill and plan/execute an SSM Patch
Manager operation with deterministic pre-checks, CONFIRM gate, and
post-verification.

## What it does

Reads an instance + patch-baseline + operation request and applies the
priority-ordered pre-check sequence:

1. Pre-flight instance metadata gate — short-circuit `stopped`/`shutting-
   down` states, `PingStatus: ConnectionLost`/`Inactive`, missing IAM
   instance profile, expired hybrid activation.
2. Pre-check gate — BLOCKED if any check fails (UNMANAGED instance, no
   effective baseline, free disk < 2 GB on root, baseline auto-approves
   more than expected, empty maintenance-window target, missing rate-
   control on fleet Installs).
3. READY — emit the exact `send-command` / `create-association` /
   `update-association` / `register-task-with-maintenance-window` CLI
   sequence with all flags populated, expected side-effects (reboot,
   compliance delta, `InstalledPending` count), and the CONFIRM gate
   prompt.
4. Execute behind CONFIRM gate — capture pre-patch snapshot, execute
   the CLI, poll `get-command-invocation` to completion.
5. Post-verification — `describe-patch-states`, `list-compliance-items`,
   host back online, `InstalledPending` reconciliation. COMPLETED only
   if ALL post-verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <scan | install | create-baseline | update-baseline | create-mw | register-mw-task>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <instance-id | tag:Patch Group,Values=<group> | baseline-id | window-id>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <poll command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
COMPLIANCE_DELTA: <before: missing X / after: missing Y>
REBOOT: <yes | no | deferred>
NOTES: <rate-control, snapshot, caveats, follow-ups>
```

## When to invoke

Paste an instance + baseline + operation request, or just describe the
scenario and ask any of:

- "scan this host for missing patches"
- "install the prod-linux-critical Security patches"
- "diagnose why this association is Success but compliance is NON_COMPLIANT"
- "create a custom baseline for Ubuntu 24.04"
- "register an Install task on the Saturday maintenance window"
- "switch our patch association from Scan to Install safely"

A bare instance-id + any operation verb ("patch this instance", "scan
this fleet") also routes here via the orchestrator.

## Inputs

- Operation: `scan`, `install`, `create-baseline`, `update-baseline`,
  `create-mw`, `register-mw-task`.
- Target: instance-id, tag-value (e.g., `prod-linux-critical`), or
  maintenance-window-id.
- Effective baseline (resolved via `get-patch-baseline-for-instance`):
  BaselineId, OperatingSystem, ApprovalRules.
- Reboot tolerance: `NoReboot=true|false`.
- Rate-control: `--max-concurrency` and `--max-errors` for fleet
  operations.
- Maintenance window context (if applicable): window-id, schedule,
  duration, cutoff, target membership.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI sequence, expected duration, expected side-
  effects, and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the
  compliance delta, the reboot status, and follow-up re-scan plan.
- For BLOCKED: the specific failure reason and the remediation step
  (e.g., tag the instance with `Patch Group`, free disk space, switch
  association Operation to Install).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 4 Operate specialist for SSM Patch Manager).
- `/aws:audit-ssm-managed-instance` for the upstream SSM fleet coverage
  audit — coverage must be healthy before this skill can patch.
- `/aws:audit-ec2-security-groups` to verify the `ssmmessages` VPC
  endpoint security group allows HTTPS/443 inbound from the instance
  subnet (required for private-subnet SSM).
