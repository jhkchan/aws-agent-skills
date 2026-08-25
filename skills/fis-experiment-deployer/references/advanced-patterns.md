# Advanced Patterns — FIS Experiment Deployer

Expert-heuristic deep dives and recent-feature notes, moved verbatim from SKILL.md. Load on demand.

## Expert heuristic: the permissive-target myth
The most common misconception: "the FIS action determines what gets
disrupted." It does not, by itself, decide the scope.

```text
Operator thinks:                  What actually happens:
"aws:ec2:stop-instances action    FIS stops every instance matching
on the template" -> safe,         the target filter. If the filter is
action-level scope.               resourceTags env=prod, that is
                                  every production instance. There is
                                  no action-level scoping in FIS; the
                                  target is the scope.
```

Target scoping is a deterministic resolution at experiment start: FIS
lists all resources matching the filter and applies the action to
each. With no stop condition, the experiment runs to budget. With an
over-scoped IAM role (`ec2:StopInstances: *`), there is no second line
of defense.

This applies equally to ECS, RDS, Aurora, Lambda, and network actions:
the target filter is the blast radius. The remedy is one tag reserved
for FIS targeting (e.g., `fis-target=true`), applied only to drill
resources, plus an IAM role scoped to that tag on every action.

## Expert heuristic: stop-condition silent no-op
A stop condition is an alarm ARN. FIS polls the alarm state during the
experiment and halts when it goes ALARM. The trap: FIS needs
`cloudwatch:DescribeAlarms` permission in its execution role for those
specific alarm ARNs. Without the permission, FIS cannot read the alarm
state — and it fails open (continues the experiment) rather than
aborting on the permission gap. There is no error and no log line that
says "stop condition disabled."

**Three invariants before any production-adjacent experiment:**

1. **The alarm exists and is monitored.** `aws cloudwatch describe-
   alarms --alarm-names <name>` returns the alarm.
2. **The FIS role has `cloudwatch:DescribeAlarms` on the alarm ARN.**
   Inspect the role policy; do not assume.
3. **A manual ALARM trigger halts a dry-run experiment.** Set the alarm
   to ALARM state (force-metric) and start a 60-second experiment; the
   experiment should halt within the polling interval.

## Expert heuristic: budgetDuration vs. action natural duration
`budgetDuration` is the upper bound on the experiment. It is NOT the
duration of the fault's effect. Each FIS action has its own model:

- `aws:ec2:stop-instances`: stops instances, then (on experiment end)
  attempts to start them. The instances are STOPPED for ~(budget -
  action-duration) minutes. If start fails, they stay stopped.
- `aws:ec2:send-api-error`: returns the configured error code for API
  calls made by the target IAM role for the duration. Effect ends when
  the action ends.
- `aws:ecs:stop-task`: stops the task. ECS reschedules per the service.
  No rollback — the task stays stopped and a new one starts (or
  doesn't, depending on deployment min/ideal).
- `aws:rds:failover-db-cluster`: triggers a failover; the failover
  itself takes 30-120 seconds. No rollback — the cluster stays
  promoted until the next failover.
- `aws:network:disrupt-connectivity` (SSM-based): injects iptables/tc
  rules; on action end, SSM removes them. If SSM agent is unreachable
  at end, the rules persist.
- `aws:lambda:invoke-async`: invokes the function with the payload,
  once or N times. Effect ends when invocation completes.

**Practical default:** set `budgetDuration` to 2x the action's
expected effect duration. A 1-minute stop-instances drill gets a
2-minute budget. A 5-minute network blackhole gets a 10-minute budget.
This bounds the failure-domain if rollback fails.

## Recent AWS features
- **Aurora failover action (`aws:rds:failover-db-cluster`):** FIS can
  trigger an Aurora writer failover as a managed action. The failover
  takes 30-120 seconds; FIS does NOT roll it back. Use for RTO
  validation with explicit promotion acceptance.
- **EKS pod disruption via SSM:** FIS does not have a native
  `aws:eks:*` action in all regions; the canonical pattern is an
  `aws:ssm:start-automation-execution` or `aws:ssm:send-command` that
  runs `kubectl delete pod` on the EKS worker node via SSM. Verify
  the worker node has the SSM agent and kubeconfig.
- **Network actions (blackhole / latency / loss):** via SSM Run
  Command on EC2 or ECS ENIs, injecting iptables/tc rules. The
  network action's rollback depends on the SSM agent being reachable
  at action end — if offline, the rules persist. Always pair with a
  stop condition and a manual rollback runbook.
- **`aws:ec2:send-api-error`:** injects API errors for an IAM role
  (e.g., ThrottlingException on ssm:GetParameters). Useful for
  testing client retry logic without taking down the dependency.
  Scope the target by IAM role, not by resource.
- **Experiment logging to CloudWatch Logs and S3 (logSchemaVersion
  2):** emits structured JSON per experiment step. Configure both
  destinations; S3 for long-term retention, CloudWatch Logs for
  near-real-time anomaly detection on experiment outcomes.
- **Cross-account FIS via Organizations:** the FIS service-linked
  role can be shared across accounts in an Organization for
  centralized chaos engineering. Verify the trust policy includes
  the organization ID condition.
