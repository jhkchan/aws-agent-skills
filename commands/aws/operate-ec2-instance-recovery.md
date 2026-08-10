---
description: Operate AWS EC2 instance recovery — system status check failure, CloudWatch recover action, ASG replacement, EBS detach/attach salvage, console output diagnosis, SSM Session Manager access, forensic AMI, stop/start, placement group recovery, Capacity Reservation preservation — with deterministic pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
  - "instance status check failed"
  - "system status check failed"
  - "instance impaired"
  - "hardware degradation"
  - "EC2 recover"
  - "CloudWatch recovery alarm"
  - "instance stop start"
  - "reboot instance"
  - "ASG instance replacement"
  - "Auto Scaling health check"
  - "EBS detach attach"
  - "console output"
  - "Session Manager access"
  - "AMI forensic snapshot"
  - "placement group recovery"
  - "Capacity Reservation"
  - "instance unreachable"
  - "EC2 automatic recovery"
  - "kernel panic recovery"
routes_to: ec2-instance-recovery-operator
---

# /aws:operate-ec2-instance-recovery

Activate the `ec2-instance-recovery-operator` skill and plan/execute
an EC2 instance recovery operation with deterministic pre-checks,
CONFIRM gate, and post-verification.

## What it does

Reads an instance configuration (status checks, placement, EBS,
ASG membership, Capacity Reservation) plus the intended operation
and applies the priority-ordered pre-check sequence:

1. Pre-flight instance metadata gate — short-circuit terminated
   instances, pending scheduled events, wrong-operation routing.
2. Pre-check gate — BLOCKED if any check fails (instance-store root
   volume will lose data on stop, ASG will terminate during stop,
   pending scheduled events, OS-level issue with stop/start, SSM
   offline for session access).
3. READY — emit the exact CLI sequence with all flags populated, the
   expected downtime, the expected side-effects (host relocation,
   data loss risk, Capacity Reservation release), and the CONFIRM
   gate prompt.
4. Execute behind CONFIRM gate — capture pre-state (describe-instances,
   describe-volumes, get-console-output), execute the CLI, poll
   describe-instance-status until running + ok.
5. Post-verification — both status checks ok, application health,
   EBS volumes reattached, Capacity Reservation re-bound. COMPLETED
   only if ALL post-verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <recover-instance | stop-start | reboot | replace-via-asg | detach-attach-ebs | forensic-ami | enable-recovery-alarm | diagnose-impaired>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <instance-id> (state: <state>, system-status: <status>, instance-status: <status>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait / monitoring command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <data-preservation, monitoring, caveats>
```

## When to invoke

Paste an instance configuration plus the intended operation, or just
describe the scenario and ask any of:

- "instance has a failing system status check"
- "hardware degradation on this instance"
- "instance is unreachable, need to recover"
- "set up a CloudWatch recovery alarm"
- "ASG is churning, instances keep failing"
- "detach EBS volume for data salvage"
- "create a forensic AMI before recovery"
- "connect via Session Manager to troubleshoot"
- "instance-store data will be lost on stop?"

A bare instance-id + recovery verb ("recover this instance", "stop
start to clear hardware") also routes here via the orchestrator.

## Inputs

- Instance configuration: `describe-instance-status` (state, system
  status, instance status, events), `describe-instances` (instance
  type, root device type, block device mappings, placement, capacity
  reservation), `describe-auto-scaling-instances` (ASG membership).
- EBS volumes: `describe-volumes` (volume IDs, attachment state,
  DeleteOnTermination).
- SSM status: `describe-instance-information` (PingStatus, agent
  version).
- Console output: `get-console-output --latest`.
- Existing alarms: `describe-alarms-for-metric` on
  `StatusCheckFailed_System`.
- For detach/attach: rescue instance details (same AZ).

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI sequence, expected downtime, expected
  side-effects (host change, data loss risk, Capacity Reservation
  release), and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, both
  status checks ok, application health verification, EBS volume
  integrity, monitoring recommendations.
- For BLOCKED: the specific failure reason and the remediation step
  (e.g., `suspend-processes --scaling-processes HealthCheck`,
  `modify-instance-capacity-reservation-attributes`, capture console
  output before reboot).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for EC2 instance recovery).
- `/aws:audit-autoscaling-group` for the audit-side counterpart —
  auditing ASG health check configuration without changing state.
- `/aws:troubleshoot-iam-permission` for diagnosing SSM Session
  Manager access issues (IAM role, trust policy).
- `/aws:operate-ec2-backup` for the backup-side counterpart —
  creating EBS snapshots and AMIs as a routine backup (this skill
  handles the emergency/forensic snapshot before recovery).
