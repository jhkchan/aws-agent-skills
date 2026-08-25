# Worked Examples (load on demand) — EC2 Rightsizing Optimizer

Secondary worked examples (already-optimal and NEED_MORE_INFO memory-missing) plus the Step 1 NEED_MORE_INFO emit template, moved verbatim from SKILL.md. The primary high-confidence Graviton downsize example stays in SKILL.md.


---

## Step 1 — NEED_MORE_INFO emit template (memory data missing) (moved from SKILL.md)

```text
TARGET: <instance-id>
VERDICT: NEED_MORE_INFO
REASON: MemoryUtilization metric is absent — CloudWatch Agent is not
  reporting mem_used_percent for this instance. Without memory data,
  a downsize recommendation is a guess, not an engineering decision.
RECOMMENDATION:
  1. Install the CloudWatch Agent on the instance with mem_used_percent
     enabled (see AWS docs: CWAgent installation guide).
  2. Wait 14-30 days for representative observation.
  3. Re-evaluate with CPU + Memory + Network + Disk data.
ESTIMATED_SAVINGS: $0 (cannot quantify without memory data)
MIGRATION_STEPS:
  - Install CWAgent (Linux): sudo yum install amazon-cloudwatch-agent
  - Configure mem_used_percent in the CWAgent config JSON
  - Validate: aws cloudwatch list-metrics --namespace CWAgent
    --metric-name mem_used_percent --dimensions Name=InstanceId,Value=<id>
```

## Worked example — already optimal (moved from SKILL.md)

```text
TARGET: i-0def456
VERDICT: ALREADY_OPTIMAL
REASON: c6i.4xlarge at 55% CPU / 65% Memory / 40% Network over 30 days
  is correctly sized for its workload. Already on a 3-year Compute
  Savings Plan covering 100% of the hourly spend. No Graviton
  opportunity (workload uses x86-specific SIMD intrinsics).
RECOMMENDATION:
  Current: c6i.4xlarge at 3-year Compute Savings Plan in us-east-1
  Proposed: no change
  Graviton: no (x86 SIMD intrinsics in compiled binary)
  Family change: no
  Confidence: HIGH — all utilization dimensions within healthy bands,
    Compute Optimizer finding Optimized, pricing model already optimized.
ESTIMATED_SAVINGS:
  Monthly (rightsize): $0
  Monthly (pricing model): $0
  Annual total: $0
MIGRATION_STEPS:
  - None required. Continue monitoring CloudWatch metrics monthly.
  - Re-evaluate at the Savings Plan renewal date (18 months out) for
    next-generation instance opportunities.
```

## Worked example — NEED_MORE_INFO (memory data missing) (moved from SKILL.md)

```text
TARGET: i-0ghi789
VERDICT: NEED_MORE_INFO
REASON: MemoryUtilization metric is absent (CloudWatch Agent not
  reporting mem_used_percent). CPU at 12% suggests Overprovisioned but
  cannot be confirmed without memory data — the workload may be memory-
  bound with an idle CPU (Step 1 data gate).
RECOMMENDATION:
  Current: m5.xlarge at On-Demand in us-east-1
  Proposed: pending data
  Graviton: unknown (depends on workload type)
  Family change: pending
  Confidence: LOW — single-dimension (CPU) data only.
ESTIMATED_SAVINGS:
  Monthly (rightsize): $0 (cannot quantify without memory data)
  Monthly (pricing model): pending
MIGRATION_STEPS:
  1. Install CloudWatch Agent:
     sudo yum install amazon-cloudwatch-agent
     sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl
       -a fetch-config -m ec2 -s -c file:config.json
     (config.json must include mem_used_percent)
  2. Wait 14-30 days for representative observation.
  3. Re-evaluate with CPU + Memory + Network + Disk data.
  Do NOT right-size based on CPU-only data.
```
