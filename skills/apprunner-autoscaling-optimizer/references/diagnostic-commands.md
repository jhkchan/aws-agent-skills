# Diagnostic Commands (load on demand) — App Runner Autoscaling Optimizer

Pre-flight command listings and safety checks moved verbatim from SKILL.md. Loaded on demand.

---

## Live-account pre-flight — service metadata gate (moved from SKILL.md)

1. `aws apprunner describe-service --service-arn <arn>` — capture
   `ServiceName`, `Status`, `InstanceConfiguration` (Cpu, Memory),
   `HealthCheckConfiguration` (Protocol, Interval, Timeout,
   HealthyThreshold, UnhealthyThreshold, Path), `NetworkConfiguration`
   (EgressConfiguration for VPC), `AutoScalingConfigurationSummary`
   (AutoScalingConfigurationArn).
2. Resolve the auto-scaling configuration:
   `aws apprunner describe-auto-scaling-configuration \
   --auto-scaling-configuration-arn <arn>` — capture `MinSize`, `MaxSize`,
   `Concurrency`.
3. `aws cloudwatch get-metric-statistics` for the service over the last
   14-30 days:
   - `RequestCount` (sum, 5-minute period) — traffic pattern
   - `InstanceCount` (average, 5-minute period) — actual provisioned count
   - `CPUUtilization` (average, 5-minute period) — instance sizing signal
   - `MemoryUtilization` (average, 5-minute period) — concurrency sizing signal
   - `4xxResponseCount` and `5xxResponseCount` (sum, 5-minute period) — health
   - `Latency` p50/p95/p99 (average, 5-minute period) — concurrency sizing
4. `aws ce get-cost-and-usage` — filter by `Service=App Runner` and the
   specific service tag or resource ARN for the last 30 days.
5. `aws ce get-usage-forecast` — project next 30 days based on historical
   patterns.

---

## Pre-flight safety checks (run before any optimization CLI) (moved from SKILL.md)

- **CONFIRMATION GATE.** Before any state-changing operation
  (`update-service`, `pause-service`, `resume-service`, `create-auto-scaling-
  configuration`, `delete-auto-scaling-configuration`), emit:
  `CONFIRM: About to <operation> on <service-name> in account <account>
  region <region>. This will <consequence>. Proceed? (yes/no)`.

- **Capture pre-state.** Before changing the auto-scaling configuration:
  `aws apprunner describe-service --service-arn <arn> --output json >
  /tmp/<service>-pre-$(date +%s).json` AND
  `aws apprunner describe-auto-scaling-configuration --auto-scaling-
  configuration-arn <arn> --output json > /tmp/<service>-asg-$(date +%s).json`.

- **Verify the service is not mid-deployment.** `aws apprunner describe-
  service --service-arn <arn> --query 'Status'` — confirm `RUNNING` (not
  `OPERATION_IN_PROGRESS`).

- **Verify the new auto-scaling configuration exists before applying.**
  `aws apprunner describe-auto-scaling-configuration --auto-scaling-
  configuration-arn <new-arn>` — confirm it exists and has the correct
  MinSize/MaxSize/Concurrency.

- **Monitor post-change.** For 7 days after a concurrency or instance type
  change, monitor:
  - `Latency` p95 (CloudWatch)
  - `5xxResponseCount` (CloudWatch)
  - `InstanceCount` (should decrease for concurrency increase)
  - `CPUUtilization` and `MemoryUtilization` (should increase per instance)
