# Error Handling (load on demand) — EC2 Rightsizing Optimizer

CLI and data-source failure modes for CloudWatch, Compute Optimizer, and the EC2 API, plus per-verdict remediation guidance, moved verbatim from SKILL.md.


---

## CLI and data-source failures — CloudWatch, Compute Optimizer, EC2 API (moved from SKILL.md)

The workflow depends on three live data sources (CloudWatch, Compute
Optimizer, EC2 API). Each can fail independently. Handle every branch
explicitly; silent failures produce misclassifications.

### CloudWatch metric failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-metric-statistics` returns empty `Datapoints` array for CPUUtilization | `len(Datapoints) == 0` | Verdict: `BLOCKED`. Reason: "CloudWatch returned no CPU data for <id> over <window>. The instance may have been stopped for the entire window, or IAM denies cloudwatch:GetMetricStatistics." Recommendation: re-pull with `--start-time` shifted 1 day forward; verify IAM policy includes `cloudwatch:GetMetricStatistics` for `AWS/EC2`. |
| `mem_used_percent` absent from CWAgent namespace | `list-metrics` returns no match | Verdict: `NEED_MORE_INFO` per Step 1. Never downgrade to `OPPORTUNITY_FOUND` on CPU-only data. |
| Datapoints present but `SampleCount < 168` (less than 7 days of hourly data) | `len(Datapoints) < window_days * 24 * 0.7` | Verdict: `NEED_MORE_INFO`. Reason: "Insufficient samples (<70% of expected hourly datapoints) — observation window is not representative." |
| CloudWatch API throttling (`Throttling` error) | Exit code non-zero, stderr contains "Throttling" | Retry with exponential backoff (`--max-attempts 5`). If still failing, fall back to a 7-day window and flag the result as LOW-confidence. |

### Compute Optimizer failures

| Failure mode | Detection | Handling |
|---|---|---|
| Enrollment `Inactive` | `get-enrollment-status` returns `"status": "Inactive"` | Compute Optimizer findings are unavailable. Proceed with CloudWatch-only analysis; mark `compute_optimizer_cross_check: unavailable` in the output. Do NOT block the workflow. |
| `get-ec2-instance-recommendations` returns empty `recommendations` array | `len(recommendations) == 0` | Either the instance is Optimal (no findings) or Compute Optimizer has not yet analyzed it. Cross-check `lastRefreshTimestamp`; if > 30 days old, treat as stale and rely on CloudWatch. If recent, treat as `Optimized` from Compute Optimizer's perspective. |
| Compute Optimizer finding present but `performanceRisk` missing | Field absent in JSON | Reject the finding as LOW-confidence. Fall back to CloudWatch thresholds; do not blindly apply the recommendation. |
| `AccessDeniedException` for `compute-optimizer:*` | Exit code non-zero | Compute Optimizer is not enabled in the account or the role lacks permissions. Proceed with CloudWatch-only; surface the gap in the output. |

### EC2 API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-instance-types` returns `UnknownInstanceType` | API error | The target type (e.g., next-gen not yet rolled out in this region) is unavailable. Fall back to a documented alternative from the references/instance-selection-reference.md table. |
| `describe-instances` shows instance `Terminated` | `State.Name == "terminated"` | Skip the instance entirely. Emit no verdict; note in the fleet rollup as "terminated during evaluation." |
| `modify-instance-attribute` fails with `IncorrectInstanceState` | Instance not stopped | Stop the instance first (`stop-instances`), wait for `State.Name == "stopped"`, retry. Surface the stop/start sequence in MIGRATION_STEPS. |
| `purchase-reserved-instances-offering` fails with `InvalidParticle` | Offering ID stale or already fulfilled | Re-query `describe-reserved-instances-offerings --offering-class <standard|convertible> --instance-type <type>` to fetch a fresh offering-id. |

### Aggregate behavior

If ANY data source fails with a transient error (throttling, network),
retry up to 3 times with exponential backoff before emitting `BLOCKED`.
For persistent failures (IAM denial, terminated instance, enrollment
Inactive), emit the appropriate gating verdict and proceed with the
remaining dimensions — do not abort the entire evaluation on a single
source failure.

## Remediation guidance by verdict (moved from SKILL.md)

### For OPPORTUNITY_FOUND — downsize

1. Snapshot the current instance:
   `aws ec2 create-image --instance-id <id> --name "pre-rightsize-<timestamp>"`.
2. Stop the instance: `aws ec2 stop-instances --instance-ids <id>`.
3. Change the type: `aws ec2 modify-instance-attribute --instance-id <id>
   --instance-type "{\"Value\": \"<new-type>\"}"`.
4. Start: `aws ec2 start-instances --instance-ids <id>`.
5. Monitor CPU + Memory for 7 days. Roll back if CPU > 80% or Memory > 85%.

### For OPPORTUNITY_FOUND — upsize

Same as downsize, but with a larger instance type. For memory-bound
upsizes, prefer the r-family (more memory per vCPU) over m-family if
the workload is genuinely memory-pressured.

### For OPPORTUNITY_FOUND — Graviton migration

1. Provision a new instance with an arm64 AMI:
   `aws ec2 run-instances --image-id <ami-arm64> --instance-type <new-type>`.
2. Migrate application code/data.
3. Validate for 24-48 hours (memory leaks, JIT behaviour, GC pauses).
4. Cutover DNS / load balancer.
5. Decommission the original x86 instance.

### For OPPORTUNITY_FOUND — t-family architecture change

- **Enable Unlimited mode**: `aws ec2 modify-instance-credit-specification
  --instance-id <id> --cpu-credits unlimited`. Immediate effect, no
  restart required.
- **Migrate to m-family**: same as cross-family migration (above).

### For OPPORTUNITY_FOUND — pricing model

- **Reserved Instance (Standard)**: `aws ec2 purchase-reserved-instances-offering
  --reserved-instances-offering-id <id> --instance-count 1`. Apply for
  steady-state workloads with predictable usage.
- **Reserved Instance (Convertible)**: same CLI, different offering class.
  Apply for workloads with growth uncertainty.
- **Compute Savings Plan**: `aws savingsplans create-savings-plan
  --savings-plan-offering-id <id> --commitment "<amount>"`. Apply for
  mixed fleets with flexible instance mix.
- **Spot Instances**: launch with `--instance-market-options
  "MarketType=spot,SpotOptions={SpotInstanceType=persistent,
  InstanceInterruptionBehavior=stop}"`. Apply only for fault-tolerant
  workloads.

### For ALREADY_OPTIMAL or OPTIMIZED

1. No remediation required for the current posture.
2. Recommend quarterly review of CloudWatch metrics and Compute Optimizer
   findings — workloads drift.
3. For Savings Plan renewals, re-evaluate at the renewal date for next-
   generation instance opportunities (e.g., m6i → m7i may offer 15-25%
  performance improvement at the same price).
