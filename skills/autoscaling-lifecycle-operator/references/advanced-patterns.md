# Auto Scaling Lifecycle Hook Operator — Advanced Patterns

Expert-knowledge deep dives and recent-feature notes moved from SKILL.md.
Load on demand before complex hook or warm-pool decisions.


## Step 0: Expert knowledge — non-obvious Auto Scaling lifecycle behaviors (moved from SKILL.md)

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


## Recent AWS features (2024-2026) (moved from SKILL.md)

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
