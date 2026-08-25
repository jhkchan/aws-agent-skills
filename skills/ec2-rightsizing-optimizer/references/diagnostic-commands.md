# Diagnostic Commands (load on demand) — EC2 Rightsizing Optimizer

Pre-flight data-source pulls, Compute Optimizer recommendation parsing, and the pre-flight safety checks, moved verbatim from SKILL.md.


---

## Pre-flight — required data sources (CWAgent memory, 14-30 day metrics, enrollment) (moved from SKILL.md)

```bash
# 1. Confirm CloudWatch Agent is reporting MemoryUtilization
aws ec2 describe-instances --instance-ids <id> --output json | \
  jq '.Reservations[].Instances[] | .InstanceId'

aws cloudwatch list-metrics --namespace CWAgent \
  --metric-name mem_used_percent \
  --dimensions Name=InstanceId,Value=<id> --output json

# 2. Pull 14-30 day utilization history
START=$(date -d '-30 days' +%FT%TZ)
END=$(date +%FT%TZ)

aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=<id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum,Minimum \
  --output json > cpu.json

aws cloudwatch get-metric-statistics --namespace CWAgent \
  --metric-name mem_used_percent \
  --dimensions Name=InstanceId,Value=<id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum,Minimum \
  --output json > mem.json

# 3. Confirm Compute Optimizer enrollment
aws compute-optimizer get-enrollment-status --output json
```

## Compute Optimizer recommendation parsing (moved from SKILL.md)

**Concrete parsing of `get-ec2-instance-recommendations` output:**

```bash
aws compute-optimizer get-ec2-instance-recommendations \
  --instance-arns arn:aws:ec2:us-east-1:<acct>:instance/<id> \
  --output json | jq '
    .instanceRecommendations[] | {
      instance_arn: .instanceArn,
      current_type: .currentInstanceType,
      finding: .finding,                  # Optimized | Underprovisioned | Overprovisioned
      finding_reasons: .findingReasonCodes,
      recommendations: [
        .recommendationOptions[] | {
          rank: .rank,                    # 1 = highest savings (may carry highest risk)
          type: .instanceType,
          performance_risk: .performanceRisk,  # 1 (safe) .. 5 (risky)
          vcpus: .instanceDigest.vCpu.vCpus,
          memory_gb: (.instanceDigest.instanceMemory.sizeInMiB / 1024),
          savings_pct: .savingsOpportunity.savingsPercentage,
          monthly_savings: .savingsOpportunity.estimatedMonthlySavings.amount
        }
      ],
      last_refresh: .lastRefreshTimestamp,
      utilization_metrics: .utilizationMetrics
    }'
```

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`stop-instances`, `modify-instance-attribute`, `run-instances`,
  `create-savings-plan`), emit and await operator approval. Do NOT
  execute the CLI until the operator confirms.

- **Snapshot before right-sizing.** Capture the current state:
  `aws ec2 create-image --instance-id <id> --name "pre-rightsize-$(date +%s)"`
  This provides a rollback path if the new type cannot handle the workload.

- **Verify the instance is `stopped` before type change.**
  `aws ec2 modify-instance-attribute --instance-type` requires the
  instance to be stopped. Attempting it on a running instance returns
  `IncorrectInstanceState`.

- **Right-size in off-peak hours for production.** Stop, modify, restart
  causes 2-10 minutes of downtime. Schedule outside peak traffic windows.

- **Prefer replacement to in-place modification for cross-family
  migrations.** Cross-family changes (m5 → t3, m5 → m7g) may require AMI
  changes (different architecture, different virtualization). Provision
  a new instance, validate, cutover, decommission the original — safer
  than in-place modification.

- **Savings Plan commitments are billing-account-level.** A Savings Plan
  applies to the entire payer account; committing $X/hour affects all
  instances in the account, not just the target. Surface this in the
  CONFIRMATION gate.

- **Bulk-operation safety limit.** Remediation across a fleet MUST
  follow this algorithm:
  1. Sort flagged instances by estimated savings (largest first).
  2. Slice into batches of at most 5 instances.
  3. For each batch: emit the per-instance MIGRATION_STEPS, then a
     single CONFIRM for the batch.
  4. After the operator confirms and the CLI runs, re-query with
     `aws ec2 describe-instances` and verify the new type landed
     before emitting the NEXT batch.
  5. Abort the sweep if any instance fails to restart or shows degraded
     performance in CloudWatch post-change.
  The skill MUST NOT emit remediation CLI for more than 5 instances in
  a single output block. Auto-applying across an entire fleet in one
  pass is forbidden: a single systematic misclassification cascades
  into mass disruption.

- **Verify Savings Plan coverage post-commitment.**
  `aws savingsplans describe-savings-plans --state ACTIVE` — confirm the
  commitment is active and the target instances are drawing from it.
  Savings Plans take up to 1 hour to fully propagate.
