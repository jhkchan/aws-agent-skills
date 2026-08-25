---
name: ec2-instance-recovery-operator
description: Operates EC2 instance recovery — system status check failure (hardware degradation, stop/start, EC2 recover action), CloudWatch alarm recovery (reboots on same host), instance replacement via Auto Scaling group health check, EBS volume detach/attach for data salvage, console output for OS-level diagnosis, SSM Session Manager for SSH-less live troubleshooting, AMI creation from a failing instance for forensic snapshot, instance stop/start to clear ephemeral issues, placement group recovery, EC2 automatic recovery, and Capacity Reservation preservation during recovery. Runs deterministic pre-checks (instance state, system status check, EBS attachment status, ASG membership, SSM agent reachability, CloudWatch alarm config, Capacity Reservation binding) behind a CONFIRM gate and emits a READY, BLOCKED, or COMPLETED verdict per recovery action. Use when an instance is impaired, hardware has degraded, an ASG is churning, or a forensic snapshot is needed before termination.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws ec2 describe-instance-status, describe-instances, stop-instances, start-instances, reboot-instances, describe-volumes, detach-volume, attach-volume, get-console-output, create-image, describe-instance-attribute, aws ssm start-session, describe-instance-information, aws cloudwatch describe-alarms, put-metric-alarm, and...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Recovering from an EC2 system status check failure (hardware degradation), configuring CloudWatch alarm recovery, replacing an instance via Auto Scaling group health check, detaching and reattaching EBS volumes to salvage data from an unhealthy instance, diagnosing OS-level issues via console output, accessing an impaired instance via SSM Session Manager, creating an AMI for forensic snapshot before termination, stop/starting an instance to clear ephemeral issues, recovering an instance in a placement group, or preserving a Capacity Reservation binding during recovery.
  activation_triggers: instance status check failed, system status check failed, instance impaired, hardware degradation, EC2 recover, CloudWatch recovery alarm, instance stop start, reboot instance, ASG instance replacement, Auto Scaling health check, EBS detach attach, console output, Session Manager access, AMI forensic snapshot, placement group recovery, Capacity Reservation, instance unreachable, EC2 automatic recovery
  invocation_schema: 'Input: either (a) an instance configuration (describe-instance-status, describe-instances) plus the intended operation (recover-instance, stop-start, reboot, replace-via-asg, detach-attach-ebs, forensic-ami, enable-recovery-alarm, diagnose-impaired), OR (b) an instance-id + operation for live-account execution. Output: deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY / NOTES block per recovery, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: EC2 instance recovery, system status check, instance status check, hardware degradation, stop/start instance, EC2 recover action, CloudWatch alarm recovery, Auto Scaling group replacement, ASG health check, EBS detach attach, console output, get-console-output, SSM Session Manager, AMI forensic snapshot, placement group recovery, Capacity Reservation, instance store, ephemeral storage, impaired instance, EC2 automatic recovery
  tags: aws, ec2, compute, recovery, ebs, ssm, cloudwatch, autoscaling, forensics, operate
---

# EC2 Instance Recovery Operator

## What this skill does

Executes EC2 instance recovery operations correctly and safely. Runs
deterministic pre-checks before any state-changing CLI (instance
state, system/instance status checks, EBS attachment status, ASG
membership, SSM agent reachability, CloudWatch alarm config, Capacity
Reservation binding, placement group state, instance-store warning),
executes the recovery behind a CONFIRM gate, and verifies the result
by confirming the instance returns to `running` with both status
checks `ok`. Every recover-instance surfaces the failure-mode table so
the operator knows whether to stop/start, reboot, replace via ASG, or
escalate to AWS Support. Every forensic-ami captures the snapshot
BEFORE the instance is terminated or replaced.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + pre-check priority | Before any operation |
| **§ Mindset** | Why recovery is a state-preserve-then-restore sequence, the instance-store trap | Understanding the safety model |
| **§ Pre-flight** | Instance metadata gate — state, status checks, ASG, Capacity Reservation | Before executing any CLI |
| **§ Process** | Per-operation planning: recover-instance, stop-start, reboot, replace-via-asg, detach-attach-ebs, forensic-ami, enable-recovery-alarm, diagnose-impaired | When choosing which operation to run |
| **§ Output format** | STRICT output contract — OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY/NOTES template | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that lose data or extend downtime | Review before risky operations |
| **§ Pre-flight safety** | Capture pre-state, AMI snapshot, EBS volume IDs, ASG suspend processes | Defense-in-depth |
| **§ Expert heuristic** | Stop/start relocates to new hardware; reboot stays on the same host | Choosing stop/start vs reboot |

## STRICT output contract

EVERY response MUST end with a single fenced text block in this exact
shape (the operator's downstream tooling greps for it). No deviations:

```text
OPERATION: <recover-instance | stop-start | reboot | replace-via-asg | detach-attach-ebs | forensic-ami | enable-recovery-alarm | diagnose-impaired>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <instance-id> (state: <state>, system-status: <status>, instance-status: <status>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated, or "(none — pre-checks failed)">
  2. <wait / monitoring command>
POST_VERIFY:
  - [PASS] <verification description> | (pending execution)
  - [FAIL] <verification description> — <reason>
NOTES: <data-preservation, monitoring, caveats>
```

Rules of the contract:

- VERDICT is exactly one of `READY`, `BLOCKED`, `COMPLETED`. No other
  values. `READY` means pre-checks passed and a CONFIRM gate is
  pending; `BLOCKED` means at least one pre-check failed — do NOT
  emit STEPS that mutate state; `COMPLETED` means post-verification
  passed after the recovery action.
- If PRE_CHECKS has any `[FAIL]`, VERDICT MUST be `BLOCKED` and STEPS
  MUST be `(none — pre-checks failed)`.
- If VERDICT is `READY`, STEPS[1] MUST be the CONFIRM prompt and
  STEPS[2] MUST be the actual CLI.
- If VERDICT is `COMPLETED`, POST_VERIFY MUST contain at least one
  `[PASS]` and no `[FAIL]`.
- Never wrap the block in JSON, never abbreviate the field names,
  never omit a section. If a section is empty, write `(none)`.

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (instance in `terminated` state, instance-store volumes will be lost on stop/start, ASG will immediately replace before recovery completes, Capacity Reservation binding lost on stop, CloudWatch recovery alarm already configured and firing, SSM agent offline for session access) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Recovery finished AND post-verification passed (instance `running`, both status checks `ok`, application healthy, EBS volumes reattached if detach/attach) | Emit verification results, monitoring plan |

**Priority order for pre-checks (apply in this sequence, all must
pass for READY):**

1. **Instance reachability.** Instance exists and is NOT in
   `terminated` state. `shutting-down` waits; `stopped` requires
   start only.
2. **Status check classification.** `SystemStatus` impaired →
   hardware/host issue, recover via stop/start or CloudWatch recover.
   `InstanceStatus` impaired → OS/application issue, recover via
   reboot or SSM access.
3. **Instance-store warning.** If `RootDeviceType: instance-store` OR
   any block device mapping has `Ebs: No`, stop/start and recover
   LOSE ephemeral data. BLOCK unless the operator acknowledges.
4. **ASG membership.** If the instance is in an ASG, stop/start may
   trigger a health-check replacement. Suspend `HealthCheck` /
   `AlarmNotification` processes before stopping, or use the ASG's
   managed replacement flow.
5. **EBS attachment.** Capture all volume IDs and attachment state
   before any recovery. If the instance is unreachable but EBS is
   healthy, detach + attach to a recovery instance is the safest
   data-salvage path.
6. **Capacity Reservation binding.** If the instance has a Capacity
   Reservation target, stop/start may release the binding. Use
   `describe-instance-attribute --attribute capacity-reservation-target`,
   and explicitly re-target on start.
7. **Placement group.** Stop/start on a `cluster` placement group
   instance may fail to restart if the group lacks capacity. Consider
   reboot (same host) for placement-group recovery.
8. **SSM agent reachability (for session access).** `describe-instance-
   information` shows `PingStatus: Online` for SSM-managed instances.
   Offline SSM means Session Manager will not work; fall back to EC2
   Serial Console or console output.
9. **CloudWatch recovery alarm.** If a recovery alarm is already
   configured and the instance is in `running` after a recover action,
   the alarm may have already fired — do NOT double-recover.

**Cost/time baselines (2026):**

- Stop/start: 2-5 minutes total (stop ~30s, start ~60s, boot varies).
- Reboot: 1-3 minutes (stays on same host, faster than stop/start).
- CloudWatch EC2 recover action: 1-5 minutes from alarm breach to
  recover (same-host reboot, preserves EBS and instance store).
- ASG replacement: 3-10 minutes (launch + boot + health check + ELB).
- EBS detach/attach: 30-60 seconds per volume (same AZ only).
- AMI creation for forensic snapshot: 5-30 minutes depending on EBS
  size (AMI + snapshots are async).

## Mindset

**One-line takeaway:** `Status: running` is a process claim, not a
health claim. An instance is only "recovered" when both status checks
return `ok` AND the application responds to its health check. Driven
by three EC2 realities:

- **Stop/start is destructive for instance-store volumes.** Stop
  releases the host; start lands on a different physical machine.
  Any data on `instance-store` volumes is gone. EBS-backed volumes
  persist. Many operators learn this only after the first recovery.
- **ASG-managed instances have their own recovery loop.** When a
  health check fails, the ASG marks the instance `Unhealthy` and
  launches a replacement. Stopping manually without suspending
  `HealthCheck` causes the ASG to terminate it. Always check ASG
  membership before manual recovery.
- **The CloudWatch EC2 recover action is a same-host reboot, NOT a
  stop/start.** It preserves the host, EBS, and instance-store data,
  but only fixes hardware issues detectable by the status check.

## Pre-flight: instance metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `describe-instance-status` paginates at 1,000
instances per call; drain `--next-token` for fleet-wide audits. For a
single instance, `--instance-ids <id>` returns one result.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws ec2 describe-instance-status --instance-ids <id> --include-all-
   instances` — capture `InstanceState`, `SystemStatus.Status`,
   `InstanceStatus.Status`, `Events` (scheduled maintenance).
2. `aws ec2 describe-instances --instance-ids <id>` — capture
   `InstanceType`, `Placement` (Affinity, GroupName, Tenancy),
   `RootDeviceType`, `BlockDeviceMappings`, `StateTransitionReason`,
   `CapacityReservationId`, `CapacityReservationSpecification`.
3. `aws autoscaling describe-auto-scaling-instances --instance-ids
   <id>` — capture ASG membership, `LifecycleState`, `HealthStatus`.
4. `aws ec2 describe-volumes --filters Name=attachment.instance-id,
   Values=<id>` — capture all EBS volume IDs and attachment state for
   rollback.
5. `aws ssm describe-instance-information --filters Key=InstanceIds,
   Values=<id>` — capture `PingStatus`, `AgentVersion`,
   `PlatformName`.
6. `aws cloudwatch describe-alarms-for-metric --namespace
   AWS/EC2 --metric-name StatusCheckFailed_System --dimensions
   Name=InstanceId,Value=<id>` — capture any existing recovery alarm.
7. `aws ec2 get-console-output --instance-id <id> --latest` — capture
   the last boot's console log for OS-level diagnosis.

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Instance/operation
configuration is not valid JSON or is missing required fields — cannot
plan.` and `REMEDIATION: Re-fetch with aws ec2 describe-instance-status
--instance-ids <id> --include-all-instances --output json and re-plan.`

| Instance attribute | Effect on operation |
|---|---|
| `State: terminated` | BLOCKED. Route to EBS-based recovery (launch from snapshot/AMI). |
| `State: shutting-down` | Wait. Poll every 30s until `stopped` or `terminated`. |
| `SystemStatus: impaired` | Hardware/host. Stop/start relocates; recover reboots same host. |
| `InstanceStatus: impaired` | OS/app. Reboot or SSM session. Stop/start rarely helps. |
| `Events: instance-stop` (scheduled) | AWS will stop on scheduled date. Plan recovery before window. |
| `Events: system-reboot` (scheduled) | AWS will reboot. Do NOT manually reboot. |
| `RootDeviceType: instance-store` | Stop/start LOSES root volume. BLOCK unless acknowledged. |
| ASG `HealthStatus: Unhealthy` | ASG will terminate+replace. Suspend `HealthCheck` first. |
| `CapacityReservationId` set | Stop may release binding. Re-target on start. |
| `Placement.GroupName` set (cluster) | Stop/start may fail restart. Prefer reboot. |
| `Placement.Tenancy: host` | Stop releases dedicated host. Verify availability. |
| Existing recovery alarm | Alarm may have fired. Check history; do NOT double-recover. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious EC2 recovery behaviors

- **Stop/start vs. reboot is the most important decision.** Stop/start
  RELOCATES the instance to a new physical host (clears hardware
  issues, loses instance-store data, releases dedicated host and
  Capacity Reservation binding). Reboot STAYS on the same host
  (preserves everything, but does not clear host-level hardware
  issues). For `SystemStatus: impaired`, stop/start is the fix; for
  `InstanceStatus: impaired`, reboot or SSM access is the fix.

- **The CloudWatch EC2 recover action is an API-driven same-host
  reboot.** Triggered by `StatusCheckFailed_System > 0 for N
  datapoints`. It only helps for recoverable transient hardware
  issues. For persistent issues, AWS schedules a `system-reboot` or
  `instance-stop` event — recover masks the symptom.

- **ASG health check replacement is usually preferred over manual
  recovery.** The ASG's built-in recovery (launch replacement, drain
  old, terminate) is more reliable than manual stop/start. Manually
  recovering an ASG instance risks termination during recovery.
  Suspend `HealthCheck` if manual recovery is required.

- **EBS detach/attach is the safest data-salvage path.** If an
  instance is unreachable but EBS volumes are healthy, detach the
  root volume, attach to a rescue instance in the same AZ, fix the
  issue, detach, re-attach to the original. Preserves all data.

- **AMI creation is non-blocking.** `create-image --no-reboot`
  captures WITHOUT a clean shutdown (best-effort consistency).
  `create-image` (default) does a clean shutdown first. For forensic
  snapshots of a hung instance, use `--no-reboot`.

- **EC2 Serial Console (2024+) provides OS-level access without
  network.** If SSH, SSM, and the network are all down, the EC2
  Serial Console provides a tty to the instance's serial port. This
  requires explicit enablement per instance (`--enable-api-serial-
  console` at the account level + per-instance).

- **Capacity Reservation binding is volatile on stop.** When an
  instance with `CapacityReservationSpecification.TargetCapacity=
  ReservationId` stops, the binding is released. On start, the
  instance launches only if the reservation still has capacity. To
  preserve: re-specify the reservation at start, or use an open
  reservation in the same AZ.

- **Instance-store (ephemeral) volumes are NEVER recoverable after
  stop.** The data lives on the physical host. Stop releases the
  host. Start lands elsewhere. EBS-backed volumes (including EBS
  snapshots) are independent of the host.

- **Placement group recovery is constrained.** A `cluster` placement
  group instance stopped may not be able to restart if the group
  lacks free capacity (the cluster relies on low-latency interconnect
  between specific hosts). Prefer reboot (same host) for placement-
  group members.

- **`StatusCheckFailed_System` and `StatusCheckFailed_Instance` are
  separate CloudWatch metrics.** A recovery alarm on
  `StatusCheckFailed_System` triggers the EC2 recover action (same-
  host reboot). A recovery alarm on `StatusCheckFailed_Instance` does
  nothing useful — recover only addresses hardware. For instance-
  status issues, use a Lambda-backed custom alarm that triggers SSM
  or reboot.

- **EC2 automatic recovery (2024-2025 GA) is AWS-managed.** AWS can
  now automatically recover an instance on detected hardware failure
  WITHOUT a customer-configured CloudWatch alarm. This is enabled by
  default for most instance types. The instance reboots on the same
  host; EBS and instance-store data are preserved. If automatic
  recovery does not fire, the manual CloudWatch alarm + recover
  action is the fallback.

- **`get-console-output` returns the LAST boot only.** Each
  `stop/start` or `reboot` clears the prior console log. For
  historical diagnosis, capture the output BEFORE rebooting.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks for the chosen operation. If ANY fails, the verdict
is BLOCKED with the failed checks in PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Instance exists and is NOT `terminated`.
2. If `State: shutting-down`, BLOCK (wait for transition).
3. Capture all EBS volume IDs (for rollback).
4. Capture `RootDeviceType` (instance-store warning).
5. Capture ASG membership (suspend processes if applicable).

**For recover-instance (CloudWatch recover action):**
6. `SystemStatus: impaired` (recover only helps hardware).
7. No existing recovery alarm already firing (check alarm history).
8. No scheduled `instance-stop` event pending (let AWS handle it).

**For stop-start (relocate to new host):**
6. `RootDeviceType: ebs` (instance-store loses data).
7. No `instance-store` block devices (or operator acknowledged).
8. ASG `HealthCheck` suspended (if applicable).
9. Capacity Reservation target captured for re-binding.
10. Placement group has free capacity for restart (cluster groups).

**For reboot (same host):**
6. No pending `system-reboot` scheduled event (let AWS handle it).
7. Instance is `running` (reboot on `stopped` is a no-op).

**For replace-via-asg:**
6. Instance is in an ASG.
7. ASG `HealthCheck` process is `Resumed` (not suspended).
8. ASG `MinSize` >= 1 (so the replacement launches).
9. ELB/target group health check configured (so the new instance
   registers).

**For detach-attach-ebs (data salvage):**
6. Rescue instance exists in the same AZ.
7. EBS volume is `in-use` (attached to the unhealthy instance).
8. `DeleteOnTermination: false` for the volume (otherwise the source
   instance's termination deletes it).
9. Rescue instance has the volume slot free (no name conflict on the
   device name).

**For forensic-ami (snapshot before termination):**
6. Instance is NOT `terminated` (AMI cannot capture a terminated
   instance).
7. EBS-backed root volume (instance-store root cannot be snapshotted).
8. AMI name does not collide with an existing AMI.

**For enable-recovery-alarm:**
6. No existing recovery alarm on the same metric (avoid duplicate
   actions).
7. `InstanceType` supports the EC2 recover action (all current-gen
   types; some previous-gen types do not).
8. `InstanceStatus: ok` (do not set a recovery alarm during a known
   OS issue — the alarm fires on `StatusCheckFailed_System` only,
   but verify the operator understands this).

**For diagnose-impaired (read-only, no BLOCKED gate):**
6. Read the failure-mode table and console output to identify the
   root cause.

**Failure-mode table (use during diagnose-impaired):**

| Symptom | Root cause | Fix |
|---|---|---|
| `SystemStatus: impaired`, `InstanceStatus: ok` | Host hardware degradation | Stop/start OR CloudWatch recover |
| `InstanceStatus: impaired`, `SystemStatus: ok` | OS / filesystem / kernel hang | Reboot; if unreachable, SSM or Serial Console |
| Both `impaired` | Network / VPC / ENI reachability loss | Check route table, ENI; stop/start if ENI re-attach needed |
| `State: running`, no SSH, SSM `Online` | Security group / IAM role issue | SSM Session Manager; verify SG ingress + SSM role |
| `State: running`, no SSH, SSM `ConnectionLost` | SSM agent hung or OS network down | Reboot; if persistent, EBS detach/attach for repair |
| Console: kernel panic | Kernel module or boot config | Stop/start; if persistent, EBS detach/attach to revert module |
| Console: `No space left on device` | Disk full | SSM session to clean up; or expand EBS volume |
| Console: `Failed to mount root filesystem` | Corrupted root EBS | Detach root, attach to rescue, `fsck`, reattach |
| ASG churn (rapid launch/terminate) | Launch config / AMI / health check | Diagnose via ASG activity; freeze ASG to stop churn |
| `State: stopped` immediately after launch | User-data script failure | Check console output; fix user-data; restart |

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI
sequence and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated from the
  instance metadata.
- The expected duration (stop/start 2-5 min; reboot 1-3 min; AMI
  5-30 min depending on EBS size).
- The expected side-effects (instance-store data lost on stop/start;
  Capacity Reservation binding released; ASG health-check paused).
- The CONFIRM gate prompt.
- The monitoring commands (poll `describe-instance-status`, check
  application health endpoint).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before `stop-instances`,
  `start-instances`, `reboot-instances`, `detach-volume`,
  `attach-volume`, `create-image`, `terminate-instances`,
  `cloudwatch put-metric-alarm`, `autoscaling suspend-processes` /
  `resume-processes`, emit: `CONFIRM: About to <operation> on
  <instance-id> in account <account> region <region>. This will
  <consequence>. Proceed? (yes/no)`. Do NOT execute until the
  operator confirms.
- Capture pre-state: `aws ec2 describe-instances --instance-ids <id>
  --output json > /tmp/<id>-pre-$(date +%s).json` AND `aws ec2
  describe-volumes --filters Name=attachment.instance-id,Values=<id>
  --output json > /tmp/<id>-volumes-$(date +%s).json`.
- For forensic-ami: ALWAYS run AMI creation BEFORE any stop/start or
  terminate. The AMI is the point-in-time snapshot.
- For stop/start: poll `describe-instance-status` every 30 seconds
  until `State: running` and both status checks return `ok`.

### Step 4: Post-verification — COMPLETED

After the recovery finishes, run post-verification. ALL checks must
pass for `COMPLETED`.

1. `describe-instance-status --instance-ids <id>` — confirm
   `State: running`, `SystemStatus.Status: ok`,
   `InstanceStatus.Status: ok`.
2. No scheduled `Events` pending (or, if scheduled, surface them).
3. For stop-start: confirm EBS volumes reattached and `DeleteOn-
   Termination` preserved.
4. For stop-start with Capacity Reservation: confirm binding re-
   established (`describe-instances --query Reservations[0].Instances
   [0].CapacityReservationId`).
5. For ASG replacement: confirm the new instance is `InService` and
   passes the ELB / target group health check.
6. For EBS detach/attach: confirm the volume is `in-use` on the
   target instance at the expected device name.
7. For forensic-ami: confirm the AMI is `available` and all snapshots
   are `completed`.
8. Application health: hit the instance's health-check endpoint or
   CloudWatch metric; confirm the workload recovered.

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim COMPLETED.

## Output format (per operation)

See § STRICT output contract above. The block MUST appear exactly in
that shape at the end of the response.

### Worked example — recover-instance (stop/start)

```text
OPERATION: stop-start
VERDICT: READY
TARGET: i-0abcdef1234567890 (state: running, system-status: impaired,
        instance-status: ok)
PRE_CHECKS:
  - [PASS] Instance exists, not terminated
  - [PASS] SystemStatus impaired (host issue), InstanceStatus ok
  - [PASS] RootDeviceType: ebs (no data loss on stop)
  - [PASS] No instance-store block devices
  - [PASS] ASG: not a member (no suspend needed)
  - [PASS] Capacity Reservation: not bound
  - [PASS] Placement: default (no cluster constraint)
STEPS:
  1. CONFIRM: About to stop and start i-0abcdef1234567890 in account
     111111111111 region us-east-1. This will RELOCATE to a new host
     (clears hardware impairment), cause 2-5 min downtime, preserve
     EBS. Proceed? (yes/no)
  2. aws ec2 stop-instances --instance-ids i-0abcdef1234567890
  3. Poll describe-instance-status every 30s until stopped
  4. aws ec2 start-instances --instance-ids i-0abcdef1234567890
  5. Poll describe-instance-status every 30s until running + ok
POST_VERIFY:
  - (pending execution)
NOTES:
  - Stop/start is correct for SystemStatus impaired. Reboot would
    keep the instance on the same impaired host.
  - Set up a CloudWatch recovery alarm for auto-recovery:
    aws cloudwatch put-metric-alarm --alarm-name recover-i-0abcdef
      --metric-name StatusCheckFailed_System --namespace AWS/EC2
      --dimensions Name=InstanceId,Value=i-0abcdef1234567890
      --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold
      --period 60 --evaluation-periods 2
      --alarm-actions arn:aws:automate:us-east-1:ec2:recover
```

### Worked example — detach-attach-ebs (data salvage, COMPLETED)

```text
OPERATION: detach-attach-ebs
VERDICT: COMPLETED
TARGET: i-0abcdef1234567890 (volume vol-0abc to rescue i-0rescue9999)
PRE_CHECKS:
  - [PASS] Source instance unreachable but not terminated
  - [PASS] EBS volume vol-0abc attached, DeleteOnTermination: false
  - [PASS] Rescue instance i-0rescue9999 in same AZ (us-east-1a)
  - [PASS] Device name /dev/sdf free on rescue instance
STEPS:
  1. (executed) aws ec2 detach-volume --volume-id vol-0abc
     --instance-id i-0abcdef1234567890 --force
  2. (executed) aws ec2 attach-volume --volume-id vol-0abc
     --instance-id i-0rescue9999 --device /dev/sdf
  3. (executed) Operator reverted bad config, unmounted, detached
  4. (executed) aws ec2 attach-volume --volume-id vol-0abc
     --instance-id i-0abcdef1234567890 --device /dev/xvda
POST_VERIFY:
  - [PASS] Volume vol-0abc in-use on i-0abcdef1234567890 at /dev/xvda
  - [PASS] Instance boots; nginx config valid; application responds
NOTES:
  - EBS detach/attach preserved all data on the root volume without
    a stop/start. Safest path when OS is reachable from a rescue
    instance but not from the original.
```

### Worked example — diagnose-impaired (BLOCKED with remediation)

```text
OPERATION: diagnose-impaired
VERDICT: BLOCKED
TARGET: i-0abcdef1234567890 (state: running, system-status: ok,
        instance-status: impaired)
PRE_CHECKS:
  - [PASS] Instance exists, not terminated
  - [PASS] InstanceStatus impaired (OS-level, not hardware)
  - [PASS] SSM PingStatus: ConnectionLost (agent hung)
  - [FAIL] Console output: kernel panic in module xyz-driver
    (OS unresponsive; SSH/SSM unavailable)
STEPS: (none — root cause is kernel panic)
POST_VERIFY: (none)
NOTES:
  - Root cause: kernel panic from xyz-driver. The instance is running
    but the OS is hung — SSH and SSM are both down.
  - Fix options:
    A) EBS detach/attach to rescue, remove the driver, reattach.
    B) stop/start if instance-store data is expendable.
  - Capture console output BEFORE any recovery action:
    aws ec2 get-console-output --instance-id i-0abcdef1234567890
      --latest > /tmp/i-0abcdef-console-$(date +%s).txt
```

## Anti-Patterns — NEVER

- NEVER stop an instance with `RootDeviceType: instance-store`
  without explicitly warning that the root volume and all instance-
  store volumes will be LOST. Stop releases the host; no recovery
  path for ephemeral data.

- NEVER manually stop an ASG-managed instance without first
  suspending `HealthCheck`. The ASG detects the stop, marks it
  `Unhealthy`, and terminates it — destroying in-flight work.

- NEVER use the EC2 recover action for `InstanceStatus: impaired`.
  Recover only addresses `SystemStatus` (hardware). For OS issues,
  recover does nothing and the alarm keeps firing.

- NEVER reboot an instance with a pending `system-reboot` scheduled
  event. The scheduled event runs automatically; a manual reboot
  masks the hardware issue and prevents AWS from applying the fix.

- NEVER create a forensic AMI AFTER stopping or terminating the
  instance. AMI creation captures the running state. Stop clears
  in-memory state; terminate destroys the instance. AMI FIRST.

- NEVER detach the root volume of a running instance without
  stopping it (use `--force` only if the instance is hung and stop
  is not completing). Forced detach can corrupt the filesystem.

- NEVER assume `State: running` means the application is healthy.
  Verify the application's health check, not just EC2 status
  checks. A hung process keeps the instance `running` while idle.

- NEVER forget to re-bind the Capacity Reservation on start. Stop
  releases the binding; start without `--capacity-reservation-
  specification` loses the reservation.

- NEVER rely on `get-console-output` for historical diagnosis after
  a reboot. Each boot clears the prior log. Capture to a local
  file BEFORE any recovery action.

- NEVER use `create-image --no-reboot` for production AMIs. It
  captures the filesystem in a potentially inconsistent state. Use
  ONLY for forensic snapshots of hung instances.

- NEVER double-recover. If a CloudWatch recovery alarm already fired,
  check alarm history before triggering another recovery. Double-
  recovery extends downtime without fixing anything.

- NEVER terminate an instance to "force recovery" without first
  detaching EBS volumes and capturing an AMI. Termination is
  irreversible.

- NEVER auto-execute a state-changing EC2 recovery CLI without the
  CONFIRM gate. Stop, reboot, detach, terminate, and AMI creation
  all extend downtime or destroy data.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation, emit the CONFIRM prompt. Do NOT execute until the
  operator confirms.

- **Capture pre-state for rollback.** Before any recovery:
  `aws ec2 describe-instances --instance-ids <id> --output json >
  /tmp/<id>-pre-$(date +%s).json` AND `aws ec2 describe-volumes
  --filters Name=attachment.instance-id,Values=<id> --output json >
  /tmp/<id>-volumes-$(date +%s).json` AND `aws ec2 get-console-output
  --instance-id <id> --latest > /tmp/<id>-console-$(date +%s).txt`.

- **Forensic AMI first.** If there is ANY chance the recovery could
  fail or the instance could be terminated, create an AMI first.
  The AMI is the point-in-time rollback.

- **EBS volume inventory.** Capture all volume IDs and attachment
  state. For detach/attach, verify the device name is free on the
  target instance.

- **ASG process suspension.** For manual recovery of ASG instances:
  `aws autoscaling suspend-processes --auto-scaling-group-name <asg>
  --scaling-processes HealthCheck AlarmNotification`. Resume after
  recovery completes.

- **Capacity Reservation re-targeting.** Capture
  `CapacityReservationId` before stop. On start:
  `aws ec2 modify-instance-capacity-reservation-attributes
  --instance-id <id> --capacity-reservation-specification
  'CapacityReservationTarget={CapacityReservationId=<id>}'`.

- **Placement group capacity check.** For cluster placement group
  instances, verify free capacity before stop/start. Prefer reboot
  if capacity is uncertain.

## Expert heuristic: stop/start vs. reboot

The single highest-leverage decision in EC2 recovery is:

> **Stop/start relocates the instance to a new physical host. Reboot
> stays on the same host.** Match the operation to the impairment:
> `SystemStatus: impaired` → stop/start (host is bad). `InstanceStatus:
> impaired` → reboot or SSM access (host is fine, OS is not). Never
> use reboot for a hardware impairment — the instance stays on the
> broken host and the impairment persists.

**Why this matters:** Operators frequently confuse reboot with
stop/start. Both appear to "restart" the instance, but they have
opposite effects on the physical host. A reboot on an impaired host
extends the outage. A stop/start on an OS issue adds 2-5 minutes of
downtime without fixing anything.

**Decision matrix:**

| Symptom | Operation | Why |
|---|---|---|
| `SystemStatus: impaired`, `InstanceStatus: ok` | Stop/start OR CloudWatch recover | Host hardware bad |
| `InstanceStatus: impaired`, `SystemStatus: ok` | Reboot OR SSM session | OS hung |
| Both `impaired` | Diagnose first (console, ENI) | Could be network/ENI |
| `State: running`, no SSH/SSM | EBS detach/attach for filesystem repair | OS unreachable |
| ASG-managed, health checks failing | ASG-managed replacement | ASG is the recovery loop |
| Pending `system-reboot` event | Wait for AWS | Manual reboot masks the issue |
| Pending `instance-stop` event | Stop/start BEFORE the window | Proactively relocate |

**Surface in the output:** for any recovery, include
`HOST_CHANGE: <yes | no>` and `DATA_LOSS_RISK: <yes | no>`. If
`DATA_LOSS_RISK: yes` and the operator has not acknowledged, BLOCK.

**Verification protocol (apply on every recovery):**

1. **Status check restoration:** `describe-instance-status` — both
   `SystemStatus` and `InstanceStatus` return `ok`.
2. **Application health:** hit the workload's health endpoint. EC2
   status checks do not verify the application.
3. **EBS integrity:** `describe-volumes` — all volumes `in-use`.
4. **Capacity Reservation:** confirm the binding (if applicable).
5. **Console output:** capture post-recovery console log.

## Recent AWS features (2024-2026)

- **EC2 automatic recovery (2024-2025 GA):** AWS automatically
  recovers instances on detected hardware failure without a customer-
  configured alarm. Same-host reboot, preserves EBS and instance-
  store. Manual CloudWatch recover is the fallback.

- **EC2 Serial Console (2024 GA):** OS-level tty access via the
  serial port, independent of SSH/SSM/network. Requires account-
  level enablement and per-instance opt-in. Use when SSH and SSM
  are both down.

- **Capacity Reservation preservation on stop/start (2024-2025):**
  New APIs allow preserving the binding through stop/start when the
  reservation has capacity. Use
  `modify-instance-capacity-reservation-attributes` to re-bind.

- **ASG Capacity Rebalance (2024-2025):** Proactively replaces
  instances at risk of interruption (Spot) or hardware degradation
  (on-demand). Configure via `--capacity-rebalance`.

- **Application Recovery Controller (2024-2026):** Zonal shift
  (evacuate an AZ) and routing control (kill switch) for coordinated
  regional failover beyond single-instance recovery.

- **SSM Session Manager port forwarding (2024):** SSH-less access to
  databases and internal services via the impaired instance's SSM
  agent. Useful for live troubleshooting without SSH keys.

- **EBS Fast Snapshot Restore (2024-2025):** Eliminates first-read
  I/O latency for recovery launches from a snapshot. Enable on the
  snapshot before launching the recovery instance.

- **EC2 Operating System Log (2025):** The console captures pre-
  reboot OS-level diagnostic logs, reducing reliance on
  `get-console-output` for post-recovery forensics.

## Domain

AWS CloudOps / EC2 Instance Recovery, Compute Resilience, and
Forensic Preservation.

## AWS documentation

- **EC2 User Guide — Recover your instance** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-recover.html
- **Status checks** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-system-instance-status-check.html
- **CloudWatch recover action** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/UsingAlarmActions.html
- **EC2 Serial Console** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-serial-console.html
- **SSM Session Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html
- **ASG health checks** — https://docs.aws.amazon.com/autoscaling/ec2/userguide/healthcheck.html
- **EBS volumes** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-attaching-volume.html
- **Capacity Reservations** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/capacity-reservations-using.html
- **Placement groups** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html
- **EC2 API Reference** — https://docs.aws.amazon.com/AWSEC2/latest/APIReference/
