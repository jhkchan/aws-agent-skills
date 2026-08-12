# Example usage: ec2-instance-rightsizer

A walkthrough showing the skill right-sizing an overprovisioned m5.2xlarge
web server, demonstrating the utilization-driven decision matrix (CPU +
CWAgent memory cross-check), the Compute Optimizer recommendation cross-
check, the dollar savings math, and the staged stop-modify-start workflow
with post-change monitoring.

## Input (user prompt)

> Review this EC2 instance before our Q3 FinOps review. It's a web
> server that feels overprovisioned. Help me right-size it.

```text
InstanceId: i-web-prod-01
InstanceType: m5.2xlarge
Architecture: x86_64
Region: us-east-1
Pricing: On-Demand (no Savings Plan coverage)
TerminationProtection: false

Metrics (last 14 days):
  - CPUUtilization avg: 3.2%, p95: 7.1%
  - MemoryUtilization avg: 28% (CWAgent mem_used_percent)
  - NetworkIn avg: 12 MB/h
  - NetworkOut avg: 8 MB/h
  - DiskReadOps avg: 150/s
  - DiskWriteOps avg: 45/s

Compute Optimizer finding: Overprovisioned
Recommendation options:
  - rank: 1, instanceType: m5.large, performanceRisk: 1
  - rank: 2, instanceType: m5.xlarge, performanceRisk: 1

Workload context: Nginx web server serving static content and
reverse-proxying to an API. Stateless. 2 vCPU minimum for HA.
```

## Skill output

```text
TARGET: i-web-prod-01 (m5.2xlarge)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: m5.2xlarge averaging 3.2% CPU and 28% memory (CWAgent confirmed)
  over 14 days is significantly overprovisioned. Compute Optimizer
  cross-check agrees (Overprovisioned, recommends m5.large at
  performanceRisk 1). Web server workload is stateless and tolerates
  downsize. Downsizing from m5.2xlarge to m5.large saves 75% of compute
  cost while projected CPU stays under 15%.
RECOMMENDATION:
  Current: m5.2xlarge, x86_64, On-Demand, us-east-1
  Proposed: m5.large, x86_64, On-Demand, us-east-1
  Dimensions changed: cpu-mem (downsize)
  Dimensions checked: idle ✓ (>5% CPU, has traffic)  cpu-mem → (3.2%/28%)
    family ✓ (m5 is current enough, no gen upgrade needed)
    graviton ✓ (x86 web server, Nginx has arm64 but no Graviton push here)
    burstable ✓ (not t-family)  workload ✓ (web server, downsize-safe)
    pricing ✓ (On-Demand, no SP to account for)  spot ✓ (production, not Spot)
  Confidence: HIGH — CWAgent memory confirms 28%; Compute Optimizer
    agrees; web server workload tolerates downsize; 14-day window.
ESTIMATED_SAVINGS:
  Current monthly: $280.32
    m5.2xlarge: $0.384/h × 730 = $280.32
  Projected monthly: $70.08
    m5.large: $0.096/h × 730 = $70.08
  Monthly saving: $210.24 (75%)
    ($280.32 − $70.08 = $210.24 ✓)
  Annual saving: $2,522.88
MIGRATION_STEPS:
  1. Stop the instance:
     aws ec2 stop-instances --instance-ids i-web-prod-01
  2. Change instance type:
     aws ec2 modify-instance-attribute --instance-id i-web-prod-01 \
       --instance-type "{\"Value\": \"m5.large\"}"
  3. Start and verify:
     aws ec2 start-instances --instance-ids i-web-prod-01
  4. Monitor CPUUtilization and MemoryUtilization for 7 days:
     aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
       --metric-name CPUUtilization \
       --dimensions Name=InstanceId,Value=i-web-prod-01 \
       --start-time $(date -d '-7 days' +%FT%TZ) \
       --end-time $(date +%FT%TZ) --period 3600 \
       --statistics Average,Maximum --output json
CONFIRM: About to modify-instance-attribute on i-web-prod-01
  (m5.2xlarge → m5.large). Monthly saving $210.24 (75%); projected CPU
  under 15%. Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **CWAgent memory is the load-bearing metric for downsizing.** A
   generic assistant downsizes on CPU alone. The skill confirms CWAgent
   `mem_used_percent` = 28% before recommending the downsize. Without
   memory data, a downsize is MEDIUM confidence at best — the workload
   may be memory-bound (JVM heap, in-memory cache) regardless of low
   CPU.

2. **Compute Optimizer is a cross-check, not the sole signal.** The
   skill pulls Compute Optimizer recommendations AND raw CloudWatch
   metrics. When they agree (both say overprovisioned), confidence is
   HIGH. When they disagree, workload context is the tiebreaker.

3. **Termination protection is checked before any stop/modify.** The
   skill verifies `disableApiTermination` before recommending stop. A
   generic assistant goes straight to `stop-instances` without checking
   protection status.

4. **All dimensions are listed in `Dimensions checked`.** The skill
   evaluates idle, cpu-mem, family, graviton, burstable, workload,
   pricing, and spot — each marked ✓ or →. A generic assistant focuses
   on only the headline dimension and misses compounding opportunities
   (e.g., a generation upgrade or Graviton migration that stacks on top
   of the downsize).

5. **Web server workload context gates the downsize.** The skill notes
   "2 vCPU minimum for HA" — it does NOT recommend downsizing below
   m5.large (2 vCPU) even though a t3.micro would be cheaper. A generic
   assistant may recommend the absolute cheapest type without workload
   constraints.

6. **Cost arithmetic is shown explicitly.** The skill shows the formula
   ($0.384/h × 730 = $280.32 → $0.096/h × 730 = $70.08) so the operator
   can verify. A generic assistant says "this should save money" without
   showing the math.

## Slash-command invocation

```
/aws:optimize-ec2-instance-rightsizer
```

Or via the orchestrator:

```
/aws:pipeline
You: "right-size our EC2 fleet for the Q3 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: ec2-instance-rightsizer]` and hands
off to this skill for the right-sizing block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new configuration:

```bash
# Confirm the new instance type landed
aws ec2 describe-instances --instance-ids i-web-prod-01 \
  --query 'Reservations[0].Instances[0].{InstanceType,State,Architecture}' \
  --output json

# Monitor CPUUtilization for 7 days post-change
aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-web-prod-01 \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json

# Monitor MemoryUtilization (CWAgent) for 7 days post-change
aws cloudwatch get-metric-statistics --namespace CWAgent \
  --metric-name mem_used_percent \
  --dimensions Name=InstanceId,Value=i-web-prod-01 \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json
```

If CPU spikes above 80% sustained or memory exceeds 85%, roll back by
reverting to the original instance type:

```bash
aws ec2 stop-instances --instance-ids i-web-prod-01
aws ec2 modify-instance-attribute --instance-id i-web-prod-01 \
  --instance-type "{\"Value\": \"m5.2xlarge\"}"
aws ec2 start-instances --instance-ids i-web-prod-01
```

## Fleet-wide extension

For a fleet of N EC2 instances, run the skill in batch mode:

1. Pull all running instances with `aws ec2 describe-instances
   --filters Name=instance-state-name,Values=running`.
2. Filter to instances with > $50/month on-demand spend (cost relevance).
3. Pull 14-30 day CloudWatch + CWAgent metrics for each.
4. Classify each instance through the decision tree.
5. Sort by estimated monthly savings (largest first).
6. Slice into batches of 5 instances.
7. For each batch: emit per-instance MIGRATION_STEPS, then a single
   CONFIRM for the batch.
8. Verify each batch before proceeding to the next.
9. After the utilization sweep, evaluate Graviton migration eligibility
   for the remaining x86 instances.
10. After Graviton, evaluate Spot migration for fault-tolerant workloads.
