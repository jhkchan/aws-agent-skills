# Example usage: ec2-rightsizing-optimizer

A walkthrough showing the skill optimizing a Java application on an
overprovisioned m5.2xlarge, demonstrating the decision matrix (CPU +
Memory thresholds), the Graviton compatibility check, the pricing-model
layering (rightsize + Savings Plan), and the staged migration with a
rollback plan.

## Input (user prompt)

> Review these EC2 instances before our Q3 FinOps review. The Java app on
> i-prod-app-01 looks like clear waste; help me size it correctly and
> capture the savings.

```text
InstanceId: i-prod-app-01
Current instance type: m5.2xlarge
Region: us-east-1
Pricing: On-Demand (no RI/Savings Plan)

Utilization metrics (last 30 days, CWAgent reporting):
  - CPUUtilization: avg=8%, max=15% (CloudWatch)
  - MemoryUtilization: avg=22%, max=30% (CloudWatchAgent)
  - NetworkIn: avg=0.05 MB/s, max=0.1 MB/s
  - DiskReadOps+DiskWriteOps: avg=10/s, max=20/s

Compute Optimizer finding: Overprovisioned
Finding reasons: ["CPUOverprovisioned", "MemoryOverprovisioned"]
Recommendation options:
  - rank: 1, instanceType: t3.large, performanceRisk: 1,
    savingsOpportunity: {savingsPercentage: 75, estimatedMonthlySavings: 150}
Last refresh: 2026-07-25

Workload context: Java 17 Spring Boot application, containerized via
Docker multi-arch image (arm64 manifest entry present). Steady-state
24/7. Small memory footprint; mostly idle between batch jobs.
```

## Skill output

```text
TARGET: i-prod-app-01
VERDICT: OPPORTUNITY_FOUND
REASON: m5.2xlarge at 8% CPU / 22% Memory / low Network+Disk over 30 days
  is a clear downsize candidate. Graviton-compatible workload (Java 17,
  multi-arch Docker image); m7g.large captures the rightsize savings
  plus 20% additional Graviton price-performance. Adding a 3-year
  Compute Savings Plan captures 40% on the residual spend (Step 4 +
  Step 7 + Step 8).
RECOMMENDATION:
  Current: m5.2xlarge at On-Demand in us-east-1
  Proposed: m7g.large at 3-year Compute Savings Plan in us-east-1
  Graviton: yes (Java 17 + multi-arch Docker image with arm64 manifest)
  Family change: yes (m5 → m7g, cross-generation + cross-architecture)
  Confidence: HIGH — Memory metric present (CWAgent), CPU+Memory both
    well below thresholds, Compute Optimizer cross-check agrees
    (Overprovisioned, performanceRisk 1 on recommended t3.large).
ESTIMATED_SAVINGS:
  Monthly (rightsize): $232.32  (m5.2xlarge $0.384/h → m7g.large $0.0644/h;
                                 730h × $0.3196 delta)
  Monthly (pricing model): $35.96  (40% off m7g.large On-Demand via
                                    3-yr Compute Savings Plan)
  Annual total: $3,219.84
  Assumptions: 730h/month, us-east-1 On-Demand pricing as of 2026-08-07,
    workload steady-state, no significant growth expected.
MIGRATION_STEPS:
  1. Snapshot the current instance (for rollback):
     aws ec2 create-image --instance-id i-prod-app-01
       --name "pre-rightsize-$(date +%s)"
  2. Provision the new instance with an arm64 AMI:
     aws ec2 run-instances --image-id <ami-arm64>
       --instance-type m7g.large --key-name <key>
       --security-group-ids <sg> --subnet-id <subnet>
       --tag-specifications "ResourceType=instance,Tags=[{Key=Name,
       Value=i-prod-app-01-m7g}]"
  3. Validate the application on m7g.large for 24-48 hours (focus on
     memory leaks, JIT behaviour, GC pauses under load, and end-to-end
     smoke tests of the Spring Boot endpoints).
  4. Cutover DNS / load balancer to the new instance.
  5. Purchase a 3-year Compute Savings Plan for the m7g.large commit:
     aws savingsplans create-savings-plan --savings-plan-offering-id <id>
       --commitment "<hourly-amount>"
  6. Verify Savings Plan coverage:
     aws savingsplans describe-savings-plans --state ACTIVE
  7. Decommission i-prod-app-01 once the new instance is verified.
CONFIRM: Before provisioning the new instance, emit and await:
  "CONFIRM: About to run-instances m7g.large in us-east-1 for rightsize
   of i-prod-app-01. This will incur ~$47/month On-Demand until the
   Savings Plan is in place. Proceed? (yes/no)"
  Do NOT run the CLI until the operator confirms.
```

## What the skill caught that a generic assistant misses

1. **Memory data is the load-bearing signal.** A generic assistant says
   "CPU is at 8%, right-size it." The skill confirms CWAgent is reporting
   MemoryUtilization (avg 22%, max 30%) before recommending a downsize —
   without memory data, a downsize is a guess. The skill explicitly cites
   the Memory metric source (CWAgent) as evidence.

2. **Decision matrix citation.** The skill cites the specific matrix
   thresholds (CPU < 30% + Memory < 50% → downsize) and verifies both
   dimensions are well below. A generic assistant picks a smaller instance
   without justifying the magnitude of the change.

3. **Graviton compatibility verification, not assumption.** The skill
   confirms the workload is Java 17 (full Graviton support) AND that the
   Docker image has an arm64 manifest entry (multi-arch) — both
   preconditions for Graviton. A generic assistant says "consider Graviton"
   without checking the prerequisites.

4. **Pricing-model layering.** The skill stacks three savings: rightsize
   (m5.2xlarge → m7g.large), Graviton price-performance, and a 3-year
   Compute Savings Plan. A generic assistant captures only the rightsize
   savings, leaving 40% of the total on the table.

5. **Cross-family migration is flagged as higher-effort.** The skill
   identifies that m5 → m7g is a cross-family + cross-architecture
   migration (not a same-family right-size), and recommends provisioning
   a new instance rather than in-place modification. A generic assistant
   recommends `modify-instance-attribute` which fails on a running
   instance and doesn't handle the AMI architecture change.

6. **Rollback plan.** The skill creates an AMI before the change and
   keeps the original instance for 24-48 hours post-cutover. A generic
   assistant goes straight to `modify-instance-attribute` with no rollback
   path — the operator is stuck if the new type can't handle the workload.

## Slash-command invocation

```
/aws:optimize-ec2-rightsizing
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our EC2 fleet for the Q3 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: ec2-rightsizing-optimizer]` and hands
off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new instance's utilization:

```bash
# Confirm the new instance type landed
aws ec2 describe-instances --instance-ids i-prod-app-01-m7g \
  --profile default --output json | \
  jq '.Reservations[].Instances[] | .InstanceType'

# Monitor CPU and Memory for 7 days post-change
aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-prod-app-01-m7g \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json

aws cloudwatch get-metric-statistics --namespace CWAgent \
  --metric-name mem_used_percent \
  --dimensions Name=InstanceId,Value=i-prod-app-01-m7g \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json

# Confirm Savings Plan is covering the new instance
aws savingsplans describe-savings-plans --state ACTIVE \
  --output json | jq '.SavingsPlans[] | {savingsPlanId, commitment, endTime}'
```

If CPU > 80% or Memory > 85% sustained for 7 days, roll back to the
original m5.2xlarge from the pre-rightsize AMI.

## Fleet-wide extension

For a fleet of N instances, run the skill in batch mode:

1. Identify all instances with CPU < 30% AND Memory < 50% over 30 days.
2. Sort by estimated monthly savings (largest first).
3. Slice into batches of 5 instances.
4. For each batch: emit the per-instance MIGRATION_STEPS, then a single
   CONFIRM for the batch.
5. Verify each batch before proceeding to the next.
6. After the rightsize sweep, evaluate the steady-state spend and commit
   to a 3-year Compute Savings Plan for the baseline.
