---
name: autoscaling-lifecycle-operator
description: >-
  Operates EC2 Auto Scaling lifecycle hook workflows end-to-end — launch
  lifecycle hook management (pending:wait transition, bootstrap
  registration, ELB target registration, custom action execution),
  terminate lifecycle hook management (terminating:wait transition, ELB
  deregistration, session drain, graceful shutdown), HeartbeatTimeout
  management (default 3600s, heartbeat extension via record-lifecycle-
  action-heartbeat), Lambda/EventBridge integration for lifecycle actions
  (complete-lifecycle-action invocation contract), warm pool configuration
  (MinSize, MaxGroupPreparedCapacity, pool state transitions), standby
  state and instance protection, CloudWatch alarm-based scaling policies,
  scheduled actions, capacity rebalance integration for Spot
  interruptions, and lifecycle hook notification targets (SNS/SQS/Lambda
  /EventBridge). Runs deterministic pre-checks (hook existence, IAM
  passrole, notification target ARN validity, HeartbeatTimeout bounds,
  Lambda complete-lifecycle-action IAM grant, warm pool capacity headroom)
  behind a CONFIRM gate and emits an OPERATION_COMPLETED or REVIEW_REQUIRED
  verdict per lifecycle operation. Use when adding launch/terminate hooks,
  debugging stuck lifecycle instances, configuring warm pools, wiring
  graceful-drain Lambdas, or integrating capacity rebalance.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan classification. Live-account
  operations use aws autoscaling describe-lifecycle-hooks, put-lifecycle-
  hook, delete-lifecycle-hook, complete-lifecycle-action, record-lifecycle-
  action-heartbeat, describe-warm-pool, put-warm-pool, describe-auto-
  scaling-groups, update-auto-scaling-group, set-instance-protection,
  enter-standby, exit-standby, put-scheduled-action, put-scaling-policy,
  aws lambda get-function-configuration, get-policy, aws sns get-topic-
  attributes, aws sqs get-queue-attributes, aws logs filter-log-events,
  and aws ec2 describe-instance-status (AWS CLI v2, SSO or key-based
  credentials).
keywords:
  - Auto Scaling
  - lifecycle hook
  - launch lifecycle hook
  - terminate lifecycle hook
  - HeartbeatTimeout
  - DefaultResult
  - CONTINUE
  - ABANDON
  - complete-lifecycle-action
  - record-lifecycle-action-heartbeat
  - pending:wait
  - Pending:Wait
  - Terminating:Wait
  - InService
  - warm pool
  - warm pool MinSize
  - MaxGroupPreparedCapacity
  - warm pool state
  - capacity rebalance
  - instance protection
  - standby
  - EnterStandby
  - ExitStandby
  - graceful drain
  - ELB deregistration
  - target group deregistration
  - connection drain
  - session drain
  - scheduled action
  - scaling policy
  - CloudWatch alarm
  - step scaling
  - target tracking
  - Spot Instance Interruption
  - SNS notification
  - SQS notification
  - EventBridge
  - lifecycle Lambda
  - bootstrap registration
tags: [aws, autoscaling, compute, lifecycle, ec2, warm-pool, spot, elb, lambda, eventbridge, operate]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "OPERATION_COMPLETED | REVIEW_REQUIRED"
  when_to_use: >-
    Adding or modifying launch/terminate lifecycle hooks, debugging stuck
    lifecycle instances (pending:wait or terminating:wait), configuring warm
    pools for faster scale-out, wiring graceful-drain Lambdas for ELB
    deregistration and session drain, setting instance protection or standby
    state, integrating capacity rebalance with Spot interruptions, creating
    scheduled actions or CloudWatch alarm-based scaling policies, or routing
    lifecycle notifications to SNS/SQS/Lambda.
  when_not_to_use: >-
    EC2 instance-level OS patching or application deployment (use an SSM or
    CodeDeploy skill), ECS/Fargate service autoscaling (use an ECS
    autoscaling skill), Auto Scaling group creation from scratch (use a
    provisioning skill), or cost optimization of EC2 fleets (use an EC2
    rightsizing skill). This skill focuses on lifecycle hook operations and
    warm pool management, not fleet provisioning or cost optimization.
  activation_triggers:
    - "add lifecycle hook"
    - "launch lifecycle hook"
    - "terminate lifecycle hook"
    - "lifecycle hook timeout"
    - "HeartbeatTimeout"
    - "complete-lifecycle-action"
    - "stuck lifecycle instance"
    - "pending wait stuck"
    - "terminating wait stuck"
    - "warm pool configuration"
    - "warm pool MinSize"
    - "capacity rebalance"
    - "graceful drain"
    - "ELB deregistration lifecycle"
    - "session drain"
    - "instance protection"
    - "standby state"
    - "enter standby"
    - "exit standby"
    - "scheduled action autoscaling"
    - "scaling policy"
    - "CloudWatch alarm scaling"
    - "Spot interruption lifecycle"
    - "SNS lifecycle notification"
    - "SQS lifecycle notification"
    - "EventBridge lifecycle"
    - "lifecycle Lambda"
    - "bootstrap on launch"
  invocation_schema: >-
    Input: either (a) an Auto Scaling group configuration (describe-auto-
    scaling-groups output) plus the intended operation (add-launch-hook,
    add-terminate-hook, modify-hook, delete-hook, configure-warm-pool,
    set-protection, enter-standby, exit-standby, add-scheduled-action,
    add-scaling-policy, enable-capacity-rebalance, diagnose-stuck), OR (b)
    an ASG name + operation for live-account execution. Output: a
    deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY /
    NOTES block per lifecycle operation, where VERDICT is one of
    OPERATION_COMPLETED, REVIEW_REQUIRED.
---

# Auto Scaling Lifecycle Hook Operator

## What this skill does

Executes EC2 Auto Scaling lifecycle hook operations correctly and safely.
Runs deterministic pre-checks before any state-changing CLI (hook existence,
HeartbeatTimeout bounds, notification target ARN validity, IAM passrole for
service-linked role, Lambda complete-lifecycle-action grant, warm pool
capacity headroom, ELB target group health), executes the operation behind
a CONFIRM gate, and verifies the result by confirming the hook is active,
lifecycle transitions complete within the expected window, and no instances
remain stuck in `Pending:Wait` or `Terminating:Wait`.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds + pre-check priority | Before any operation |
| **Mindset** | Why lifecycle hooks extend the transition, the stuck-instance trap | Understanding the safety model |
| **Pre-flight** | ASG metadata gate — hook config, warm pool state, notification targets | Before executing any CLI |
| **Process** | Per-operation planning: add-hook, warm-pool, diagnose-stuck | When choosing which operation |
| **Output format** | Structured OPERATION/VERDICT/PRE_CHECKS/STEPS template | Formatting the response |
| **Anti-Patterns** | NEVER list — common mistakes that strand instances | Review before risky operations |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `REVIEW_REQUIRED` | One or more pre-checks failed (hook missing required notification target, HeartbeatTimeout outside 30-7200s, Lambda lacks complete-lifecycle-action IAM grant, warm pool MaxGroupPreparedCapacity < MinSize, capacity rebalance conflicts with lifecycle hook) | List failures, do NOT execute |
| `OPERATION_COMPLETED` | Operation finished and post-verification passed (hook Active, lifecycle transition completed, warm pool at desired capacity, no instances stuck) | Emit verification results, monitoring plan |

**Priority order for pre-checks (apply in this sequence):**

1. **ASG existence and state** — group exists, not being deleted, has a
   launch template/version.
2. **Hook configuration** — no conflicting hook with the same name.
3. **HeartbeatTimeout bounds** — between 30 and 7200 seconds (default 3600).
4. **Notification target validity** — SNS/SQS/Lambda ARN exists and is
   active. SNS/SQS requires the ASG service-linked role to have
   `sns:Publish` or `sqs:SendMessage`.
5. **IAM passrole** — `AWSServiceRoleForAutoScaling` exists with required
   permissions.
6. **Lambda complete-lifecycle-action grant** — lifecycle Lambda execution
   role has `autoscaling:CompleteLifecycleAction` on the ASG ARN.
7. **Warm pool capacity** — `MaxGroupPreparedCapacity` >= `MinSize` and <=
   ASG `MaxSize`.
8. **ELB integration** — target group deregistration delay compatible with
   terminate hook HeartbeatTimeout.
9. **Capacity rebalance** — if enabled, terminate hooks must complete within
   the Spot 2-minute rebalance window.

**Time baselines (2026):**

- Launch hook: adds `HeartbeatTimeout` seconds to `Pending:Wait` ->
  `InService`. With 300s hook and 60s bootstrap, total is 300s (bootstrap
  runs within the wait window).
- Terminate hook: adds `HeartbeatTimeout` seconds to `Terminating:Wait` ->
  `Terminated`. ELB deregistration drain runs concurrently with the hook.
- Warm pool: pre-booted `Stopped` instances resume to `Running` in ~10-30s
  (vs. 60-120s cold launch).
- Capacity rebalance: rebalance recommendation + 2-min interruption notice
  gives ~4 min total; terminate hook must complete within this window.

## Mindset

**One-line takeaway:** A lifecycle hook extends the instance state
transition by `HeartbeatTimeout` seconds. During this window, the instance
stays in `Pending:Wait` or `Terminating:Wait` and the action Lambda must
call `complete-lifecycle-action` before the timeout expires or the
`DefaultResult` (CONTINUE or ABANDON) determines the outcome.

- **A lifecycle hook is a timer, not a gate.** The hook gives a window to
  do work (bootstrap, drain) but does not block forever. If the Lambda
  never calls `complete-lifecycle-action`, the hook expires after
  `HeartbeatTimeout` and `DefaultResult` fires: CONTINUE (proceed) or
  ABANDON (for launch: terminate and replace; for terminate: terminate
  anyway). A Lambda that silently fails without completing is the #1 cause
  of stuck instances.

- **Warm pool changes the scale-out math.** Without a warm pool, a new
  instance takes 60-120 seconds (AMI boot + userdata + app startup). With
  a warm pool, pre-booted `Stopped` instances resume to `Running` in 10-30
  seconds. But the launch lifecycle hook still fires on every transition
  from warm pool to the ASG — the hook Lambda must handle warm-pool-
  sourced instances (they already have the OS booted).

- **Capacity rebalance + terminate hook is a race against the Spot clock.**
  When Spot capacity is at risk, EC2 sends a rebalance recommendation
  followed by a 2-minute interruption notice. The ASG (with capacity
  rebalance) launches a replacement and starts draining the old instance
  via the terminate hook. The terminate hook HeartbeatTimeout must be short
  enough to complete within the interruption window (default 3600s is too
  long for Spot — use 30-120s).

## Pre-flight: ASG metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `describe-auto-scaling-groups` paginates at 50/page.
`describe-lifecycle-hooks` returns all hooks in one call. `describe-warm-
pool` paginates at 100 instances/page.

**Live-account pre-flight (skip if offline plan audit):**
1. `describe-auto-scaling-groups --auto-scaling-group-names <asg>` —
   capture `MinSize`, `MaxSize`, `DesiredCapacity`, `LaunchTemplate`,
   `LoadBalancerNames`, `TargetGroupARNs`, `HealthCheckType`,
   `HealthCheckGracePeriod`, `ServiceLinkedRoleARN`, `MixedInstancesPolicy`.
2. `describe-lifecycle-hooks --auto-scaling-group-name <asg>` — capture
   existing hooks: `LifecycleHookName`, `LifecycleTransition`,
   `HeartbeatTimeout`, `DefaultResult`, `NotificationTargetARN`, `RoleARN`.
3. `describe-warm-pool --auto-scaling-group-name <asg>` — capture
   `PoolMinSize`, `MaxGroupPreparedCapacity`, `WarmPoolState`, instances.
4. `describe-notification-configurations` and `describe-scaling-policies`
   and `describe-scheduled-actions` — capture existing configs.
5. For lifecycle Lambdas: `get-function-configuration` and `get-policy` —
   confirm the Lambda exists and its role has
   `autoscaling:CompleteLifecycleAction`.
6. `describe-instance-status` — check for instances stuck in
   `Pending:Wait` or `Terminating:Wait`.
7. `logs filter-log-events` on the lifecycle Lambda log group — capture
   recent lifecycle action errors.

**Malformed input:** emit `VERDICT: ERROR` with `REASON: ASG/operation
configuration is not valid JSON or is missing required fields` and
`REMEDIATION: Re-fetch with aws autoscaling describe-auto-scaling-groups
--auto-scaling-group-names <name> --output json`.

| ASG attribute | Effect on operation |
|---|---|
| ASG not found | All operations BLOCKED. |
| `MixedInstancesPolicy` with Spot | Capacity rebalance likely enabled; terminate hooks must be short (30-120s). |
| No lifecycle hooks configured | Add-hook operations proceed; diagnose-stuck returns "no hooks". |
| Existing hook with same name | Add-hook BLOCKED; use modify-hook. |
| `HeartbeatTimeout` outside 30-7200 | Invalid; put-lifecycle-hook will fail. |
| `NotificationTargetARN` null or invalid | Lambda never invoked; hook is a no-op timer. |
| Warm pool `MaxGroupPreparedCapacity` < `PoolMinSize` | Invalid configuration. |
| `TargetGroupARNs` present | ELB deregistration delay interacts with terminate hook timeout. |
| `HealthCheckType: ELB` with short `HealthCheckGracePeriod` | Launch hook must complete before grace period or ELB marks instance unhealthy. |
| `CapacityRebalance: true` | Terminate hook fires on rebalance + interruption; must complete within Spot 2-min notice. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious Auto Scaling lifecycle behaviors

- **The lifecycle hook extends the transition by HeartbeatTimeout.**
  Without a hook, `Pending` -> `InService` is immediate. With a launch
  hook, the instance enters `Pending:Wait` for up to `HeartbeatTimeout`
  (default 3600s). The action must call `complete-lifecycle-action` to
  release the instance early, or wait for timeout + `DefaultResult`.

- **complete-lifecycle-action is the release valve.** The Lambda receives
  an EventBridge/SNS event with `LifecycleActionToken`,
  `LifecycleHookName`, `AutoScalingGroupName`, `EC2InstanceId`, and
  `LifecycleTransition`. It must call `aws autoscaling
  complete-lifecycle-action --lifecycle-hook-name <hook>
  --auto-scaling-group-name <asg> --lifecycle-action-token <token>
  --lifecycle-action-result CONTINUE|ABANDON`. Missing or failed = stuck.

- **HeartbeatTimeout default (3600s) is almost always too long.** A
  bootstrap that takes 60 seconds will leave the instance stuck for the
  remaining 3540 seconds if the Lambda crashes. Set HeartbeatTimeout to
  2-3x the expected action duration.

- **record-lifecycle-action-heartbeat extends the timeout.** For long-
  running actions (large artifact downloads), the Lambda can call this to
  reset the timer. This is how you handle multi-step bootstraps.

- **DefaultResult controls what happens on timeout.** `CONTINUE` proceeds
  (instance enters InService or gets terminated). `ABANDON` for launch
  hooks terminates the instance and triggers replacement; for terminate
  hooks, the instance dies regardless. Use `CONTINUE` for most launch hooks
  (fail-open); `ABANDON` only if failed bootstrap should trigger replacement.

- **Warm pool instances enter `Pending:Wait` when claimed.** The hook
  fires the same as a cold launch. The Lambda should detect warm-pool-
  sourced instances (already booted) and skip redundant bootstrap.

- **Warm pool state: Stopped vs Running.** `Stopped` keeps instances booted
  to OS but stopped (cheaper, EBS only). `Running` keeps them ready (faster
  but costs compute). Most use cases want `Stopped` — resume takes 10-30s.

- **MaxGroupPreparedCapacity caps the warm pool.** Each warm pool instance
  incurs EBS + (if Running) compute charges. If not set, defaults to ASG
  `MaxSize`.

- **Instance protection prevents ASG termination but not Spot
  interruption.** Use for stateful workloads during normal scaling; use
  terminate hooks for graceful drain during Spot events.

- **Standby removes from service without terminating.** `enter-standby`
  moves an instance to `Standby` — no traffic, not counted toward
  DesiredCapacity, but stays running. `exit-standby` returns it.

- **Capacity rebalance + terminate hooks interact.** When rebalance fires,
  the ASG launches a replacement and puts the old instance into
  `Terminating:Wait`. The hook fires with the rebalance context. Must
  complete before the 2-minute interruption notice force-terminates.

- **Multiple hooks on the same transition fire in sequence.** Each must
  complete before the next. Total transition time = sum of all
  HeartbeatTimeouts.

- **HealthCheckGracePeriod interacts with launch hooks.** If
  `HealthCheckType: ELB` and the grace period is shorter than the hook
  timeout, the ELB health check runs on an instance still in
  `Pending:Wait`, marks it unhealthy, and the ASG replaces it.

- **SNS/SQS notification targets deliver a JSON payload.** Contains
  `LifecycleActionToken`, `LifecycleHookName`, `LifecycleTransition`,
  `EC2InstanceId`, etc. Use `NotificationMetadata` to pass context to the
  action Lambda.

- **Scheduled actions override DesiredCapacity at a specific time.**
  Scale-out triggers launch hooks, scale-in triggers terminate hooks.

- **CloudWatch alarm-based scaling uses metric alarms + policies.** Target
  tracking adjusts DesiredCapacity to maintain a metric target (e.g.,
  CPUUtilization). Step scaling adjusts by a fixed amount per alarm.

### Step 1: Pre-check gate — REVIEW_REQUIRED if any check fails

**For ALL operations:** ASG exists, has a launch template, not being
deleted.

**For add-launch-hook:** No existing hook with same name.
`HeartbeatTimeout` in [30, 7200]. `DefaultResult` is CONTINUE or ABANDON.
`NotificationTargetARN` is valid and active. If SNS/SQS: service-linked
role has `sns:Publish` or `sqs:SendMessage`. If Lambda: execution role has
`autoscaling:CompleteLifecycleAction`. If ELB: `HealthCheckGracePeriod`
>= expected bootstrap duration. `RoleARN` has trust policy for
`autoscaling.amazonaws.com`.

**For add-terminate-hook:** Same as launch plus: if capacity rebalance
enabled, `HeartbeatTimeout` <= 120. If ELB target groups:
`deregistration_delay.timeout_seconds` <= `HeartbeatTimeout`.

**For modify-hook:** Hook exists. New `HeartbeatTimeout` in [30, 7200].
New notification target passes validity checks.

**For delete-hook:** Hook exists. No instances currently in
`Pending:Wait` or `Terminating:Wait` for this hook.

**For configure-warm-pool:** `PoolMinSize` >= 0.
`MaxGroupPreparedCapacity` >= `PoolMinSize` and <= ASG `MaxSize`.
`DesiredCapacity` + `PoolMinSize` does not exceed account vCPU limits or
subnet IP availability. Launch template supports Stop/Start.

**For set-protection:** Instances are members of the ASG and `InService`.

**For enter-standby / exit-standby:** Instances are members; for enter:
`InService` with `ShouldDecrementDesiredCapacity` specified; for exit: in
`Standby`.

**For add-scheduled-action:** No existing action with same name. `Recurrence`
is valid cron. `MinSize` <= `DesiredCapacity` <= `MaxSize`.

**For add-scaling-policy:** No existing policy with same name. Target
tracking: `TargetValue` > 0. Step scaling: alarm exists or will be created.

**For enable-capacity-rebalance:** ASG has Spot instances. Existing
terminate hooks have `HeartbeatTimeout` <= 120.

**For diagnose-stuck (read-only):** Read hook state, CloudWatch Logs, and
the stuck-instance table to identify root cause.

**Stuck-instance failure-mode table:**

| Symptom | Root cause | Fix |
|---|---|---|
| `Pending:Wait` > HeartbeatTimeout | Lambda never called complete-lifecycle-action | Check Lambda logs; call complete manually |
| `Pending:Wait`, Lambda `AccessDenied` on `CompleteLifecycleAction` | Lambda role missing permission | Add `autoscaling:CompleteLifecycleAction` to role |
| `Terminating:Wait` > HeartbeatTimeout | Same as above for terminate | Same fix |
| `Pending:Wait`, Lambda never invoked | EventBridge rule missing or SNS unconfirmed | Check rule pattern; confirm SNS subscription |
| `Pending:Wait`, event missing `LifecycleActionToken` | EventBridge rule wrong detail type | Match `EC2 Instance-launch Lifecycle Action` |
| Warm pool instance stuck in `Pending:Wait` | Lambda not designed for warm pool | Update Lambda to detect warm-pool instances |
| Instance terminated despite terminate hook | Spot force-kill; HeartbeatTimeout was 3600s | Reduce to <= 120 for Spot ASGs |
| `put-lifecycle-hook` `ValidationError` | HeartbeatTimeout outside 30-7200 or malformed ARN | Correct parameters |
| Multiple hooks, instance stuck between hooks | Each hook must complete before next | Reduce hooks or shorten timeouts |

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI sequence
and CONFIRM gate. The plan includes the exact CLI command, expected
duration, side-effects, CONFIRM prompt, and monitoring step.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`put-lifecycle-hook`, `delete-lifecycle-hook`, `complete-lifecycle-
  action`, `put-warm-pool`, `set-instance-protection`, `enter-standby`,
  `exit-standby`, `put-scheduled-action`, `put-scaling-policy`,
  `update-auto-scaling-group`), emit `CONFIRM: About to <operation> on
  <asg-name> in account <account> region <region>. This will
  <consequence>. Proceed? (yes/no)`.
- Capture pre-state: `describe-lifecycle-hooks` and `describe-auto-scaling-
  groups` output saved to `/tmp/<asg>-*-$(date +%s).json`.
- Execute the CLI. For `put-lifecycle-hook`, the hook is immediately active.
- For hooks with a Lambda: `aws logs tail /aws/lambda/<lifecycle-lambda>
  --follow --since 5m`.

### Step 4: Post-verification — OPERATION_COMPLETED

ALL checks must pass for `OPERATION_COMPLETED`:
1. `describe-lifecycle-hooks` confirms hook with correct configuration.
2. For add/modify-hook: test scale-out confirms instance enters
   `Pending:Wait`, Lambda fires, transitions to `InService`.
3. For configure-warm-pool: `describe-warm-pool` confirms correct
   `PoolMinSize`, `MaxGroupPreparedCapacity`, instances present.
4. For set-protection/standby: confirm instance state via
   `describe-auto-scaling-groups`.
5. CloudWatch shows no lifecycle timeout errors (15-min sample).

If ANY verification fails, emit `VERDICT: ERROR` — route to diagnose-stuck.

## Output format (per operation)

```text
OPERATION: <add-launch-hook | add-terminate-hook | modify-hook | delete-hook | configure-warm-pool | set-protection | enter-standby | exit-standby | add-scheduled-action | add-scaling-policy | enable-capacity-rebalance | diagnose-stuck>
VERDICT: OPERATION_COMPLETED | REVIEW_REQUIRED
TARGET: <asg-name> (hook: <hook-name-or-"none">)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait / monitoring command>
POST_VERIFY:
  - [PASS] <verification description>
NOTES: <monitoring, caveats, warm pool state>
```

### Worked example — add-launch-hook (bootstrap registration)

```text
OPERATION: add-launch-hook
VERDICT: OPERATION_COMPLETED
TARGET: prod-web-asg (hook: web-bootstrap-hook)
PRE_CHECKS:
  - [PASS] ASG exists, DesiredCapacity: 4, MaxSize: 20
  - [PASS] No existing hook named web-bootstrap-hook
  - [PASS] HeartbeatTimeout: 300 (in [30, 7200])
  - [PASS] DefaultResult: CONTINUE
  - [PASS] Lambda web-lifecycle-action State: Active
  - [PASS] Lambda role has autoscaling:CompleteLifecycleAction
  - [PASS] HealthCheckGracePeriod: 600 >= bootstrap 120s
STEPS:
  1. CONFIRM: About to add launch lifecycle hook web-bootstrap-hook
     on prod-web-asg with HeartbeatTimeout 300s, DefaultResult CONTINUE,
     Lambda web-lifecycle-action. New instances enter Pending:Wait for
     up to 300s during bootstrap. Proceed? (yes/no)
  2. aws autoscaling put-lifecycle-hook \
       --lifecycle-hook-name web-bootstrap-hook \
       --auto-scaling-group-name prod-web-asg \
       --lifecycle-transition autoscaling:EC2_INSTANCE_LAUNCHING \
       --heartbeat-timeout 300 \
       --default-result CONTINUE \
       --notification-target-arn arn:aws:lambda:us-east-1:111111111111:function:web-lifecycle-action
POST_VERIFY:
  - [PASS] describe-lifecycle-hooks: web-bootstrap-hook active
  - [INFO] Test scale-out: instance entered Pending:Wait, Lambda invoked,
    transitioned to InService in 87s
NOTES:
  - If Lambda crashes, instance stays in Pending:Wait for 300s, then
    DefaultResult CONTINUE fires. Monitor Lambda errors.
  - For warm-pool instances, Lambda detects already-booted OS and
    skips AMI-level bootstrap.
```

### Worked example — diagnose-stuck (REVIEW_REQUIRED)

```text
OPERATION: diagnose-stuck
VERDICT: REVIEW_REQUIRED
TARGET: prod-api-asg (hook: api-bootstrap-hook)
PRE_CHECKS:
  - [PASS] ASG exists, DesiredCapacity: 6
  - [PASS] Hook api-bootstrap-hook exists (HeartbeatTimeout 3600)
  - [FAIL] Instance i-xxx stuck in Pending:Wait for 42 minutes
  - [FAIL] Lambda timed out after 30s — bootstrap takes ~45s
STEPS: (none — root cause is Lambda timeout too short)
NOTES:
  - Fix: increase Lambda timeout to 60s, then manually complete:
    aws lambda update-function-configuration --function-name api-lifecycle-action --timeout 60
    aws autoscaling complete-lifecycle-action \
      --lifecycle-hook-name api-bootstrap-hook --auto-scaling-group-name prod-api-asg \
      --lifecycle-action-token <token> --lifecycle-action-result CONTINUE
  - Also reduce HeartbeatTimeout from 3600 to 300.
```

## Anti-Patterns — NEVER

- NEVER set HeartbeatTimeout to 3600 (the default) without calculating the
  expected action duration. Set to 2-3x the expected bootstrap/drain time.

- NEVER deploy a lifecycle Lambda without
  `autoscaling:CompleteLifecycleAction` in its execution role. Without it,
  the Lambda cannot release the instance — the #1 cause of stuck instances.

- NEVER delete a lifecycle hook while instances are in `Pending:Wait` or
  `Terminating:Wait` for that hook. Deleting strands those instances.

- NEVER use a terminate hook with HeartbeatTimeout > 120 on a Spot ASG with
  capacity rebalance. The Spot 2-minute interruption notice force-terminates
  regardless of hook state.

- NEVER configure `deregistration_delay.timeout_seconds` higher than the
  terminate hook HeartbeatTimeout. The instance is terminated before drain
  completes.

- NEVER set `DefaultResult: ABANDON` on a launch hook without a replacement
  strategy. ABANDON terminates on timeout and the ASG launches a
  replacement — which fires the same hook. Broken bootstrap = launch loop.
  Use CONTINUE (fail-open).

- NEVER set `HealthCheckGracePeriod` shorter than the launch hook
  HeartbeatTimeout with `HealthCheckType: ELB`. The ELB health check runs
  on an instance still in `Pending:Wait`, marks it unhealthy, ASG replaces.

- NEVER assume warm pool instances skip the launch lifecycle hook. They
  enter `Pending:Wait` when claimed — the hook fires. The Lambda must
  handle warm-pool-sourced instances.

- NEVER set `MaxGroupPreparedCapacity` below `PoolMinSize` — invalid,
  `put-warm-pool` returns `ValidationError`.

- NEVER use `enter-standby` without specifying
  `ShouldDecrementDesiredCapacity`. Without it the ASG launches a
  replacement for the standby instance.

- NEVER assume `set-instance-protection` protects against Spot
  interruptions. Protection only prevents ASG-initiated scale-in. Spot
  interruptions and capacity rebalance bypass it.

- NEVER create multiple hooks with long HeartbeatTimeouts on the same
  transition without calculating the total. Two 300s hooks = up to 600s in
  `Pending:Wait`.

- NEVER configure a lifecycle hook with no notification target. Without it,
  no action receives the event, and the instance sits until HeartbeatTimeout.
  This is a no-op hook that only adds latency.

- NEVER assume the lifecycle event always contains `LifecycleActionToken`.
  EventBridge retries or SNS misconfiguration may omit it. The Lambda
  should handle missing tokens gracefully.

- NEVER auto-execute a state-changing Auto Scaling CLI without the CONFIRM
  gate. These operations have production-wide side effects.

- NEVER use a lifecycle hook as a deployment mechanism. Hooks are for
  instance-level initialization and drain, not application deployment. Use
  CodeDeploy, SSM, or a deployment pipeline.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit the CONFIRM prompt. Do NOT execute until confirmed.
- **Capture pre-state for rollback.** Save `describe-lifecycle-hooks` and
  `describe-auto-scaling-groups` output before changes.
- **Verify Lambda state.** `get-function-configuration` — confirm `State:
  Active` and `Timeout` >= expected action duration.
- **Verify Lambda execution role.** Confirm
  `autoscaling:CompleteLifecycleAction` on the ASG ARN.
- **Verify notification target.** SNS: topic exists with confirmed
  subscriptions. SQS: queue exists with policy allowing
  `autoscaling.amazonaws.com`. Lambda: EventBridge invocation permission.
- **Verify warm pool headroom.** `describe-subnets` for IP availability;
  `get-service-quota` for vCPU limits.
- **Verify capacity rebalance interaction.** If enabled, terminate hooks
  must have HeartbeatTimeout <= 120.
- **Prefer additive changes.** Adding hooks, configuring warm pools, and
  setting protection are reversible. Deleting a hook with active lifecycle
  actions is destructive.

## Recent AWS features (2024-2026)

- **Warm pool instance reuse (2024):** Instances returning to the warm
  pool on scale-in preserve state. The launch hook can detect previously-
  warmed instances and skip redundant setup.
- **Capacity rebalance + lifecycle hook (2024-2025):** Terminate hook fires
  on the rebalance recommendation (before the 2-min interruption notice),
  giving a head start on drain.
- **EventBridge lifecycle event enrichment (2024):** Events include
  `NotificationMetadata` for passing context (e.g., config endpoint) to the
  action Lambda.
- **Spot allocation strategies (2024-2025):** `capacity-optimized` and
  `price-capacity-optimized` reduce Spot interruptions, reducing terminate
  hook frequency.
- **Instance maintenance policy (2025):** `MaxHealthyPercentage` /
  `MinHealthyPercentage` for ASG replacement during maintenance. Replacement
  instances fire the launch hook.
- **Predictive scaling + warm pools (2025):** Predictive scaling pre-scales
  before demand spikes. Combined with warm pools, achieves near-instant
  scale-out.
- **EventBridge to Step Functions (2024):** Route lifecycle events to a
  state machine for multi-step orchestration. The state machine calls
  `complete-lifecycle-action` at the final step.

## Domain

AWS CloudOps / EC2 Auto Scaling Lifecycle Hook Management, Warm Pool
Configuration, and Capacity Rebalance Integration.

## AWS documentation

- **Auto Scaling User Guide — Lifecycle hooks** — https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html
- **Lifecycle hook overview** — https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks-overview.html
- **Tutorial: Lambda lifecycle hook** — https://docs.aws.amazon.com/autoscaling/ec2/userguide/tutorial-lifecycle-hook-lambda.html
- **Warm pools** — https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-warm-pools.html
- **Capacity rebalance** — https://docs.aws.amazon.com/autoscaling/ec2/userguide/capacity-rebalance.html
- **Auto Scaling API Reference** — https://docs.aws.amazon.com/autoscaling/ec2/APIReference/Welcome.html
- **Auto Scaling CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/autoscaling/
- **Scheduled actions** — https://docs.aws.amazon.com/autoscaling/ec2/userguide/schedule_time.html
- **Target tracking scaling** — https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html
- **Instance protection** — https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-instance-protection.html
