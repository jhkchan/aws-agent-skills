# End-to-end usage scenario: compute-optimizer-findings-auditor

A walkthrough showing the skill auditing two Compute Optimizer findings on EC2
instances — one high-confidence OVERPROVISIONED finding (UNDERUTILIZED) and one
low-confidence finding with inferred memory (NOT_OPTIMIZED) — demonstrating the
confidence-gating logic that separates actionable cost waste from unreliable
noise.

## Input (user prompt)

> Review these Compute Optimizer findings before we approve the right-sizing
> batch. Instance A looks like clear waste, but Instance B has no memory
> data and I'm not sure if we should act on it.

### Instance A — high-confidence overprovisioned

```yaml
Resource type: EC2 instance
Instance ARN: arn:aws:ec2:us-east-1:111111111111:instance/i-prod-web-01
Current instance type: m5.2xlarge
Finding: Overprovisioned
Finding reasons: ["CPUOverprovisioned", "MemoryOverprovisioned"]
Utilization metrics:
  - name: CPU, statistic: Maximum, value: 8.0, source: CloudWatch
  - name: Memory, statistic: Maximum, value: 15.0, source: CloudWatchAgent
  - name: NetworkIn, statistic: Average, value: 0.05, source: CloudWatch
Recommendation options:
  - rank: 1, instanceType: t3.large, performanceRisk: 1
    savingsOpportunity: { savingsPercentage: 75.0, estimatedMonthlySavings: 150.0 }
  - rank: 2, instanceType: t3.medium, performanceRisk: 2
    savingsOpportunity: { savingsPercentage: 82.0, estimatedMonthlySavings: 165.0 }
Last refresh timestamp: 2026-07-28
```

### Instance B — low-confidence overprovisioned (no CWAgent)

```yaml
Resource type: EC2 instance
Instance ARN: arn:aws:ec2:us-east-1:111111111111:instance/i-prod-batch-02
Current instance type: m5.xlarge
Finding: Overprovisioned
Finding reasons: ["CPUOverprovisioned"]
Utilization metrics:
  - name: CPU, statistic: Maximum, value: 12.0, source: CloudWatch
  (Memory metric ABSENT — CloudWatch Agent not installed)
Recommendation options:
  - rank: 1, instanceType: t3.medium, performanceRisk: 4
    savingsOpportunity: { savingsPercentage: 70.0, estimatedMonthlySavings: 95.0 }
Last refresh timestamp: 2026-07-26
```

## Skill output

```text
RESOURCE: arn:aws:ec2:us-east-1:111111111111:instance/i-prod-web-01
VERDICT: UNDERUTILIZED
REASON: Finding is Overprovisioned with HIGH confidence — CPU 8%, Memory 15%
(both measured by CloudWatch Agent), performanceRisk 1 on recommendation.
Savings opportunity: $150/month.
RISK: HIGH
FINDINGS:
  - [HIGH] Overprovisioned: m5.2xlarge with CPU max 8% and Memory max 15% —
    both metrics measured by CWAgent. Recommended t3.large saves 75%
    ($150/month). performanceRisk 1 — safe to right-size (Step 4a).
REMEDIATION:
  1. Create a pre-rightsize AMI:
     aws ec2 create-image --instance-id i-prod-web-01 --name "pre-rightsize-$(date +%s)"
  2. Stop the instance: aws ec2 stop-instances --instance-ids i-prod-web-01
  3. Change type: aws ec2 modify-instance-attribute --instance-id i-prod-web-01
     --instance-type "{\"Value\": \"t3.large\"}"
  4. Start: aws ec2 start-instances --instance-ids i-prod-web-01
  5. Monitor CPU + Memory for 7 days. Roll back if CPU > 80% or Memory > 85%.

---

RESOURCE: arn:aws:ec2:us-east-1:111111111111:instance/i-prod-batch-02
VERDICT: NOT_OPTIMIZED
REASON: Finding is Overprovisioned but confidence is LOW — Memory metric is
absent (CloudWatch Agent not installed; memory inferred). performanceRisk 4
on recommended option. Cannot safely recommend right-sizing.
RISK: MEDIUM
FINDINGS:
  - [MEDIUM] Overprovisioned finding is low-confidence: CPU-only data (12%
    max). Memory utilization is inferred, not measured (Step 3, condition 1).
  - [MEDIUM] performanceRisk 4 on recommended t3.medium — right-sizing may
    cause performance regression (Step 3, condition 2).
REMEDIATION:
  1. Install the CloudWatch Agent on i-prod-batch-02 to report actual Memory
     utilization (mem_used_percent metric in CWAgent namespace).
  2. Wait 30 days for Compute Optimizer to analyse with real Memory data.
  3. Re-evaluate the finding once Memory metrics are present.
  4. Do NOT right-size based on this finding — it may be a false positive.
```

## What the skill caught that a generic assistant misses

1. **Confidence gating.** A generic assistant says "Instance B is
   overprovisioned, right-size it." The skill recognises that the Memory
   metric is absent (no CWAgent) — the finding is based on CPU-only data and
   memory is inferred. The recommendation carries performanceRisk 4. Both
   factors make the finding LOW confidence, so the verdict is NOT_OPTIMIZED
   (do not act), not UNDERUTILIZED (act now).

2. **performanceRisk interpretation.** A generic assistant ignores the
   performanceRisk score. The skill knows that Risk 4-5 means the
   recommended instance type might not handle the workload — it is
   speculative. Risk 1 on Instance A's recommendation means it is safe to
   act. This distinction drives the different verdicts.

3. **Per-resource remediation with CLI.** The skill provides exact CLI
   commands for Instance A (stop, modify, start) while explicitly telling
   the operator NOT to act on Instance B until CWAgent is installed and 30
   days of memory data are collected.

4. **Savings quantification.** Instance A's waste is quantified ($150/month)
   and risk-tiered HIGH (savings > $100). Instance B's theoretical savings
   ($95/month) are noted but NOT acted on — the finding is unreliable, so
   the savings estimate is unreliable too.

## Slash-command invocation

```
/aws:audit-compute-optimizer-findings
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit these compute optimizer findings before we batch right-size"
```

The orchestrator emits
`[Phase: Audit | Skills routed: compute-optimizer-findings-auditor]` and
hands off to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating Instance A, validate:

```bash
# Verify the instance type changed
aws ec2 describe-instances --instance-ids i-prod-web-01 \
  --profile default --query 'Reservations[0].Instances[0].InstanceType'

# Check 7-day CPU utilization trend post-change
aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
  --metric-name CPUUtilization --dimensions Name=InstanceId,Value=i-prod-web-01 \
  --start-time $(date -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date +%Y-%m-%dT%H:%M:%S) --period 3600 --statistics Average \
  --profile default
```

For Instance B, install CWAgent and wait for fresh data:

```bash
# Check if CWAgent is reporting memory metrics
aws cloudwatch get-metric-statistics --namespace CWAgent \
  --metric-name mem_used_percent \
  --dimensions Name=InstanceId,Value=i-prod-batch-02 \
  --start-time $(date -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Average \
  --profile default
```

If no data returns, CWAgent is not installed or not configured for memory
reporting. Install it via SSM and wait 30 days before re-evaluating.
