---
name: compute-optimizer-findings-auditor
description: Audits AWS Compute Optimizer findings for EC2, EBS, Lambda, Auto Scaling Group, and ECS resources — classifies overprovisioned (underutilized) waste, underprovisioned (performance-risk) findings, and low-confidence recommendations (inferred memory, high performanceRisk, stale data) into a deterministic verdict with per-finding risk and CLI remediation. Emits UNDERUTILIZED | NOT_OPTIMIZED | OK per resource. Use when reviewing Compute Optimizer recommendations, triaging right-sizing findings, validating finding confidence before acting, or auditing cost-optimization posture.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline finding-document classification. Live-account audits use aws compute-optimizer get-ec2-instance-recommendations, get-ebs-volume-recommendations, get-lambda-function-recommendations, and get-enrollment-status (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  verdict_shape: UNDERUTILIZED | NOT_OPTIMIZED | OK
  when_to_use: Reviewing Compute Optimizer findings for EC2, EBS, Lambda, or ASG resources, triaging right-sizing recommendations, validating finding confidence before approving a right-size action, auditing cost- optimization posture, or checking whether a finding is actionable or low-confidence noise.
  activation_triggers: audit compute optimizer findings, check EC2 right-sizing recommendations, is this compute optimizer finding reliable, review overprovisioned resources, compute optimizer low confidence, Lambda memory recommendations, EBS volume recommendations, performanceRisk too high, compute optimizer stale findings, right-size EC2 instances
  invocation_schema: 'Input: either (a) a Compute Optimizer finding/recommendation document (EC2, EBS, Lambda, ASG) with finding, findingReasons, utilizationMetrics, recommendationOptions, and metadata, OR (b) a resource ARN for live-account audit. Output: deterministic RESOURCE/VERDICT/REASON/FINDINGS/REMEDIATION block per resource, where VERDICT ∈ {UNDERUTILIZED, NOT_OPTIMIZED, OK}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Compute Optimizer, right-sizing, overprovisioned, underprovisioned, underutilized, EC2 recommendations, EBS recommendations, Lambda recommendations, Auto Scaling Group, ECS Fargate, performanceRisk, savingsOpportunity, finding confidence, inferred memory, CloudWatch Agent, cost optimization, resource utilization, gp3 migration, Lambda memory, finding reasons
  tags: compute, cost-optimization, right-sizing, compute-optimizer, ec2, ebs, lambda, audit
---

# Compute Optimizer Findings Auditor

## Mindset

**One-line takeaway:** the verdict depends on BOTH the finding field AND
finding confidence. An `Overprovisioned` finding with inferred memory (no
CloudWatch Agent) is NOT actionable — it is NOT_OPTIMIZED, not
UNDERUTILIZED. Confidence gates the verdict.

AWS Compute Optimizer analyses 30+ days of CloudWatch utilization metrics and
emits findings: `Optimized`, `Overprovisioned`, or `Underprovisioned`. But the
finding text alone does not tell you whether the recommendation is safe to act
on. Three factors override the finding:
- **Memory metrics are inferred without the CloudWatch Agent (CWAgent).**
  Without it, Compute Optimizer cannot see actual memory usage — it infers
  memory from the instance type's published specs. An `Overprovisioned`
  finding based on CPU-only data may be wrong if the instance is memory-bound.
- **performanceRisk (1-5) on the recommended option** warns whether the
  suggested instance type can handle the workload. Risk 4-5 means the
  recommendation is speculative — do NOT act without load testing.
- **Insufficient data** (new resources, stopped instances, zero-invocation
  Lambda functions) produces unreliable or absent findings.

## Quick reference — verdict thresholds

| Condition | Verdict | Rule |
|---|---|---|
| `finding: Overprovisioned` + HIGH confidence + savings > $0 | **UNDERUTILIZED** | Step 4a |
| `finding: Overprovisioned` + LOW confidence (inferred memory / performanceRisk ≥ 4) | **NOT_OPTIMIZED** | Step 3 |
| `finding: Underprovisioned` | **NOT_OPTIMIZED** | Step 4b |
| `finding: Optimized` + metrics present | **OK** | Step 4c |
| No finding / insufficient data / enrollment inactive | **NOT_OPTIMIZED** | Step 1 |
| `finding: Optimized` + lastRefresh > 30 days stale | **NOT_OPTIMIZED** | Step 2 |

See the ordered steps below for edge cases. Deep Compute Optimizer internals
(analysis windows, metric sources, recommendation generation) are in the
[Deep reference](#deep-reference-compute-optimizer-internals) section.

## Pre-flight: enrollment and data gate (run before classification)

Before evaluating findings, verify that Compute Optimizer is producing real
data. Several conditions short-circuit the audit — misclassifying them
produces false confidence.

**Live-account pre-flight checks (skip if doing offline finding-doc audit):**
1. Verify enrollment: `aws compute-optimizer get-enrollment-status`. If
   `status: Inactive`, the account is NOT enrolled — no findings exist
   regardless of resource count. Output `NOT_OPTIMIZED` with reason
   "enrollment inactive."
2. Paginate findings: EC2/EBS/Lambda recommendation APIs return up to 1,000
   items per page. Use `--next-token` from the prior response to page through
   all resources; iterating only the first page silently skips the long tail.
3. Cross-check CloudTrail for `compute-optimizer:Get*Recommendations` calls —
   a recommendation export may have been run days ago and the findings are
   stale. Always check `lastRefreshTimestamp` on each finding.

| Condition | Effect on audit |
|---|---|
| Enrollment `Inactive` | No findings possible. Output NOT_OPTIMIZED: "enrollment inactive — opt in via AWS Console or CLI." |
| `lastRefreshTimestamp` > 30 days old | Stale finding — workload may have changed. Downgrade to NOT_OPTIMIZED. |
| `utilizationMetrics` empty or < 2 entries | Insufficient data for reliable classification. NOT_OPTIMIZED. |
| EC2 Memory metric absent (no CWAgent) | Memory inferred — finding confidence is LOW. Gate per Step 3. |
| Lambda invocations = 0 during analysis period | No utilization signal. NOT_OPTIMIZED: "insufficient invocation data." |
| `findingReasons` empty on a non-Optimized finding | Malformed finding — missing root cause. NOT_OPTIMIZED with note. |

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Validate input

If the finding document is missing required fields (`finding`, or `finding`
is not one of `Optimized`/`Overprovisioned`/`Underprovisioned`), output:

```text
RESOURCE: <arn>
VERDICT: ERROR
REASON: Finding document is missing the 'finding' field or contains an invalid value — cannot classify.
REMEDIATION: Re-fetch with the appropriate aws compute-optimizer get-*-recommendations command.
```

### Step 1: Enrollment and data sufficiency check

If any of these conditions are true, classify as **NOT_OPTIMIZED** and skip
remaining steps:

- Enrollment status is `Inactive` (no data at all).
- `utilizationMetrics` is empty or has fewer than 2 entries (EC2/EBS) —
  insufficient data to determine optimization state.
- Lambda function with 0 invocations during the analysis period — no
  utilization signal exists.
- `findingReasons` is empty on a non-`Optimized` finding — root cause
  cannot be determined.

These all mean the resource's optimization state cannot be confidently
determined. The finding (if present) is noise, not signal.

### Step 2: Stale finding check

If `lastRefreshTimestamp` is more than 30 days old, the finding reflects a
workload that may have since changed. Classify as **NOT_OPTIMIZED**
regardless of finding value, with reason: "stale finding — last refresh >
30 days ago; re-run recommendation before acting."

This is critical because Compute Optimizer does NOT retroactively update
findings when a workload changes — it only refreshes on the next analysis
cycle (approximately every 24 hours). A finding from 45 days ago may
describe a workload that was terminated and replaced.

### Step 3: Confidence evaluation (gates the verdict)

Evaluate whether the finding is HIGH or LOW confidence. **Confidence
determines whether an Overprovisioned finding becomes UNDERUTILIZED
(actionable cost waste) or NOT_OPTIMIZED (unreliable — do not act).**

**A finding is LOW confidence if ANY of these are true:**

1. **EC2 Memory metric is absent** from `utilizationMetrics`. Without the
   CloudWatch Agent (CWAgent), Compute Optimizer cannot see actual memory
   usage. It infers memory from the instance type's published specifications.
   An `Overprovisioned` finding may be wrong if the instance is
   memory-constrained — the CPU is idle but memory is at 95%. This is the
   single most common false-positive source in Compute Optimizer.

2. **performanceRisk ≥ 4** on the recommended instance type. The
   performanceRisk score (1-5) estimates the likelihood that the recommended
   instance type cannot handle the workload. Risk 1 is safe; Risk 4-5 means
   the recommendation is speculative and should not be acted on without load
   testing. The first (cheapest) recommendation option often carries the
   highest risk.

3. **EC2: fewer than 3 utilization metrics.** A reliable EC2 finding needs
   at least CPU, Memory, and one more dimension (Network or Disk). CPU-only
   findings are weak signal — the instance may be network-bound or I/O-bound.

4. **EBS: only one of {IOPS, Throughput} present.** Volume type/size
   recommendations need both read/write IOPS and throughput data. A
   recommendation based on only one dimension may miss a bottleneck in the
   other.

**If the finding is LOW confidence, classify as NOT_OPTIMIZED** — the
finding cannot be trusted enough to recommend a right-size action. The
remediation is to improve data quality (install CWAgent, wait for more data)
before re-evaluating.

**If the finding is HIGH confidence**, proceed to Step 4.

### Step 4: Finding field classification

Apply based on the `finding` value:

#### 4a: Overprovisioned + HIGH confidence → UNDERUTILIZED

The resource has excess capacity — it is underutilized and wasting spend.
Extract the `savingsOpportunity.estimatedMonthlySavings` to quantify the
waste. The recommendation options are actionable (performanceRisk is
acceptable).

**Risk levels for UNDERUTILIZED:**
- **HIGH risk** if estimatedMonthlySavings > $100/month OR CPU utilization < 10%
- **MEDIUM risk** if estimatedMonthlySavings $10-$100/month
- **LOW risk** if estimatedMonthlySavings < $10/month (pennies — note but
  do not prioritize)

#### 4b: Underprovisioned → NOT_OPTIMIZED

The resource is too small for its workload — performance degradation is
likely. This is NOT "underutilized" — the resource is overworked, not
wasting money. The remediation is to UP-size, not down-size.

**Risk levels for NOT_OPTIMIZED (Underprovisioned):**
- **HIGH risk** if CPU > 90% AND findingReasons include
  `CPUUnderprovisioned` — active performance degradation.
- **MEDIUM risk** if any single resource dimension is underprovisioned
  (Memory, Network, etc.).

#### 4c: Optimized → OK

The resource is correctly provisioned. No action needed. Verify that the
finding has sufficient utilization metrics to be trustworthy (Step 3
confidence check should have passed).

### Step 5: Aggregation — worst finding wins

When auditing multiple resources in a single pass, the account-level verdict
is the **worst** verdict across all resources, where NOT_OPTIMIZED is worse
than UNDERUTILIZED and UNDERUTILIZED is worse than OK:

```text
account_verdict = max(all_resource_verdicts)
```

Order: NOT_OPTIMIZED > UNDERUTILIZED > OK

This ordering reflects that a performance risk (Underprovisioned) is more
urgent than wasted spend (Overprovisioned) — an underprovisioned resource
may be causing customer-visible latency, while an overprovisioned resource
is only losing money.

## Output format (per resource)

```text
RESOURCE: <arn or resource-id>
VERDICT: UNDERUTILIZED | NOT_OPTIMIZED | OK
REASON: <1-2 sentences citing the finding, confidence level, and key metric>
RISK: HIGH | MEDIUM | LOW
FINDINGS:
  - [<severity>] <finding description with rule citation>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — EC2 Overprovisioned, high confidence

```text
RESOURCE: arn:aws:ec2:us-east-1:111111111111:instance/i-0abc123
VERDICT: UNDERUTILIZED
REASON: Finding is Overprovisioned with HIGH confidence — CPU 8%, Memory 15%
(both measured by CloudWatch Agent), performanceRisk 1 on recommendation.
Savings opportunity: $150/month.
RISK: HIGH
FINDINGS:
  - [HIGH] Overprovisioned: m5.2xlarge with CPU max 8% and Memory max 15% —
    both metrics measured by CWAgent. Recommended t3.large saves 75% (Step 4a).
  - [OK] performanceRisk 1 on recommended option — safe to right-size.
REMEDIATION:
  1. Stop the instance: aws ec2 stop-instances --instance-ids i-0abc123.
  2. Change instance type: aws ec2 modify-instance-attribute --instance-id
     i-0abc123 --instance-type "{\"Value\": \"t3.large\"}".
  3. Start the instance: aws ec2 start-instances --instance-ids i-0abc123.
  4. Monitor CPU and Memory for 7 days post-change to confirm the
     workload runs within the new instance's capacity.
```

### Worked example — EC2 Overprovisioned, LOW confidence (inferred memory)

```text
RESOURCE: arn:aws:ec2:us-east-1:111111111111:instance/i-0def456
VERDICT: NOT_OPTIMIZED
REASON: Finding is Overprovisioned but confidence is LOW — Memory metric is
absent (CloudWatch Agent not installed; memory inferred). performanceRisk 4
on recommended option. Cannot safely recommend right-sizing.
RISK: MEDIUM
FINDINGS:
  - [MEDIUM] Overprovisioned finding is low-confidence: CPU-only data (12%
    max). Memory utilization is inferred, not measured (Step 3, condition 1).
  - [MEDIUM] performanceRisk 4 on recommended option — right-sizing may
    cause performance regression (Step 3, condition 2).
REMEDIATION:
  1. Install the CloudWatch Agent on the instance to report actual Memory
     utilization: see AWS docs for CWAgent installation and Memory metric
     configuration.
  2. Wait 30 days for Compute Optimizer to analyse with real Memory data.
  3. Re-evaluate the finding once Memory metrics are present.
  4. Do NOT right-size based on this finding — it may be a false positive.
```

## Expert edge cases — non-obvious Compute Optimizer behaviors

These behaviors change classification if ignored:

- **Memory inference without CWAgent.** Compute Optimizer cannot see actual
  memory usage unless the CloudWatch Agent is installed. Without it, the
  Memory metric is absent from `utilizationMetrics` and memory utilization is
  inferred from the instance type's specs. An `Overprovisioned` finding based
  on CPU-only data may be a false positive — the instance could be
  memory-bound. This is the #1 source of unreliable findings.

- **performanceRisk scale is 1-5, not 0-1.** Each recommendation option
  includes a `performanceRisk` integer (1 = very safe, 5 = very risky). The
  cheapest option often carries the highest risk. Risk 1-2 is safe to act on;
  Risk 3 is acceptable with monitoring; Risk 4-5 requires load testing before
  acting. Treat Risk ≥ 4 as LOW confidence (Step 3).

- **30-hour continuous data requirement.** Compute Optimizer needs at least
  30 hours of continuous utilization data to produce a finding. A frequently
  stopped/started instance may not accumulate enough continuous data,
  producing no finding or a misleading one from partial data. Check the
  number of utilization metric data points as a proxy for data completeness.

- **Lambda memory increase can REDUCE total cost.** For Lambda functions,
  increasing memory also increases CPU allocation, which can reduce
  execution time. Since Lambda bills on `memory × duration`, a faster
  function may cost LESS even with more memory. An `Underprovisioned` Lambda
  finding that recommends more memory may show a negative savingsOpportunity
  (cost increase on paper) but actually reduce real cost through faster
  execution. Always cross-reference `projectedUtilizationMetrics` with the
  function's billed duration.

- **gp2 → gp3 EBS recommendations are price-driven, not utilization-driven.**
  Compute Optimizer frequently recommends migrating `gp2` volumes to `gp3`
  because gp3 has a lower baseline price ($0.08/GB vs $0.10/GB) — not because
  the volume is misconfigured. A gp2 volume at 80% IOPS utilization may still
  get an `Overprovisioned` finding simply because gp3 is cheaper. Treat gp2
  → gp3 recommendations as cost optimizations, not performance issues.

- **ASG recommendations are launch-template level.** Changing an Auto Scaling
  Group recommendation requires updating the launch template AND rolling
  existing instances — this is a higher-effort change than a standalone
  instance right-size. Old instances continue running on the old type until
  terminated and replaced. Flag ASG findings as higher-effort remediation.

- **Savings opportunity can be negligible.** Even with an `Overprovisioned`
  finding, the `estimatedMonthlySavings` may be $0 or near-zero (e.g.,
  t3.nano → t3.micro saves pennies). Do not treat all `Overprovisioned`
  findings as equally urgent. Use savings magnitude to prioritise.

- **External metrics integration raises confidence.** Compute Optimizer
  supports external metrics (Datadog, Dynatrace, Instana) via the AWS
  Marketplace. When external metrics are configured, findings include richer
  data (application-level metrics, not just infrastructure). A finding with
  external metrics data is HIGHER confidence than one with CloudWatch-only
  data.

- **Enhanced infrastructure metrics for EC2 bare-metal / metal instance
  types.** Some instance types (`.metal`, certain 7th-gen types) require
  enhanced infrastructure metrics enrollment to produce full findings.
  Without it, these instances may show no finding despite being
  overprovisioned.

- **Compute Optimizer does not analyse Spot Instance pricing.** A Spot
  Instance with an `Overprovisioned` finding still represents waste, but the
  savings opportunity assumes On-Demand pricing. The actual savings from
  right-sizing a Spot Instance are smaller because Spot is already
  discounted up to 90%.

- **Finding reasons drive remediation path.** `CPUOverprovisioned` vs
  `NetworkBandwidthOverprovisioned` lead to different remediation. CPU-
  based findings are safe to right-size by reducing vCPU. Network-based
  findings may need a different instance family (e.g., from `m5` to `t3`
  with burst networking) rather than simply a smaller size. Always extract
  `findingReasons` and cite the specific reason in remediation.

- **ECS/Fargate recommendations require separate enrollment.** ECS service
  recommendations on Fargate need the Compute Optimizer ECS enrollment
  (distinct from the base EC2/EBS/Lambda enrollment). An account enrolled
  for EC2 may not be enrolled for ECS — check before expecting ECS findings.

- **Recommendation options are ranked by savings, not by safety.** The first
  recommendation option (index 0) is the cheapest, not the safest. Always
  check `performanceRisk` on each option. The safest option may be at index
  1 or 2 with slightly lower savings.

## Anti-Patterns — NEVER

- NEVER classify an `Overprovisioned` finding as UNDERUTILIZED when the
  EC2 Memory metric is absent from `utilizationMetrics`. Without the
  CloudWatch Agent, memory usage is inferred — the finding is LOW confidence
  and should be NOT_OPTIMIZED. This is the most common false positive.

- NEVER act on a recommendation with `performanceRisk` ≥ 4 without load
  testing. The risk score means Compute Optimizer estimates a meaningful
  chance the recommended instance type cannot handle the workload.

- NEVER treat `Underprovisioned` as UNDERUTILIZED. An underprovisioned
  resource is overworked, not wasting money. It needs MORE capacity, not
  less. Underprovisioned always maps to NOT_OPTIMIZED.

- NEVER assume a Lambda function with 0 invocations is "optimized." Zero
  invocations means no utilization data — the finding is noise. Classify as
  NOT_OPTIMIZED: "insufficient invocation data."

- NEVER right-size based on a single utilization metric. CPU-only data on
  an EC2 instance cannot tell you whether the instance is memory-bound,
  network-bound, or I/O-bound. Require at least 3 metrics for HIGH
  confidence.

- NEVER recommend an ASG right-size as a quick fix. ASG recommendations
  require launch-template changes AND instance replacement — it is a
  higher-effort change that can take hours to roll out across a fleet.

- NEVER ignore `lastRefreshTimestamp`. A finding older than 30 days
  describes a workload that may no longer exist. Stale findings are
  NOT_OPTIMIZED until refreshed.

- NEVER assume all `Overprovisioned` findings are equally valuable. A
  finding with `estimatedMonthlySavings` of $2 is noise; a finding with
  $500 is a priority. Use savings magnitude to triage, not just finding
  count.

- NEVER recommend migrating a gp2 EBS volume to gp3 solely based on an
  `Overprovisioned` finding without checking IOPS/throughput utilization.
  gp3 has lower baseline performance (3,000 IOPS / 125 MiB/s) than gp2
  (which scales IOPS with size). A gp2 volume at 10,000 IOPS will LOSE
  performance on gp3 unless additional provisioned IOPS are purchased.

- NEVER change an EC2 instance type without stopping it first.
  `modify-instance-attribute --instance-type` requires the instance to be
  stopped. Attempting it on a running instance returns
  `IncorrectInstanceState`.

- NEVER accept a recommendation option at index 0 blindly. The first option
  is ranked by savings (cheapest), not by safety. Check `performanceRisk`
  on every option — the safest may be index 1 or 2.

- NEVER assume Compute Optimizer is enrolled for all resource types. EC2,
  EBS, Lambda, and ECS enrollments are independent. An account enrolled for
  EC2 may not be enrolled for Lambda — check `get-enrollment-status` for
  each resource type before expecting findings.

- NEVER overlook the effort of migrating instance families (e.g., m5 → t3).
  Same-family right-sizes (m5.2xlarge → m5.large) are low-effort; cross-
  family changes (m5 → t3) may require AMI changes, driver compatibility
  checks, and application testing.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any instance stop, type change,
  volume modification, or Lambda update, the auditor MUST emit:
  `CONFIRM: About to <action> on <resource-id> in account <account>. This
  will cause <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **Snapshot EC2 before right-sizing.** Capture the current state:
  `aws ec2 create-image --instance-id <id> --name "pre-rightsize-$(date +%s)"`
  before stopping and changing instance type. This provides a rollback path
  if the new type cannot handle the workload.

- **For ASG right-sizing:** update the launch template version, then trigger
  an instance refresh: `aws autoscaling start-instance-refresh`. Monitor
  the rollout — a failed refresh should be rolled back to the previous
  template version.

- **For EBS volume type changes:** `aws ec2 modify-volume --volume-id <id>
  --volume-type gp3` is non-disruptive (the volume stays online), but
  performance may degrade during the migration window. Flag this in the
  confirmation gate.

- **For Lambda memory changes:** `aws lambda update-function-configuration
  --function-name <name> --memory-size <mb>` takes effect immediately on
  the next invocation. Test with a small percentage of traffic first (use
  alias routing) before applying to all invocations.

- **Verify CWAgent is installed** before acting on any EC2 finding. If
  Memory metrics are absent, install CWAgent first, wait 30 days, then
  re-evaluate. Right-sizing without memory data is guessing.

- Prefer the recommendation option with `performanceRisk` ≤ 2, even if it
  has slightly lower savings. The cost of a performance regression
  (customer impact, rollback effort) exceeds the marginal savings of a
  riskier option.

## Remediation guidance

### For UNDERUTILIZED (Overprovisioned, HIGH confidence)

**EC2:**
1. Create a pre-rightsize AMI (see Pre-flight).
2. Stop the instance: `aws ec2 stop-instances --instance-ids <id>`.
3. Change type: `aws ec2 modify-instance-attribute --instance-id <id>
   --instance-type "{\"Value\": \"<new-type>\"}"`.
4. Start: `aws ec2 start-instances --instance-ids <id>`.
5. Monitor CloudWatch CPU + Memory for 7 days. If CPU > 80% or Memory >
   85%, roll back to the original type.

**EBS:**
1. `aws ec2 modify-volume --volume-id <id> --volume-type <new-type>
   --size <new-size> --iops <new-iops>`.
2. Verify the modification completes: `aws ec2 describe-volumes-modifications
   --volume-ids <id>`.

**Lambda:**
1. `aws lambda update-function-configuration --function-name <name>
   --memory-size <new-mb>`.
2. Check CloudWatch metrics `Duration` and `Errors` for 1-3 days.
3. If Duration increases or Errors spike, roll back to original memory.

**ASG:**
1. Create a new launch template version with the recommended instance type.
2. Update the ASG to use the new template version.
3. Trigger instance refresh: `aws autoscaling start-instance-refresh
   --auto-scaling-group-name <name>`.
4. Monitor the refresh until complete.

### For NOT_OPTIMIZED

**Underprovisioned (performance risk):**
1. Identify the bottleneck from `findingReasons`
   (CPUUnderprovisioned, MemoryUnderprovisioned, etc.).
2. UP-size the resource to a recommendation option with
   `performanceRisk` ≤ 2.
3. Same EC2/EBS/Lambda CLI steps as UNDERUTILIZED, but with a LARGER type.

**Low confidence (inferred memory / high performanceRisk):**
1. Install CloudWatch Agent for memory metrics (EC2).
2. Wait 30 days for Compute Optimizer to analyse with real data.
3. Re-evaluate. Do NOT act on the current finding.

**Stale finding:**
1. Re-run recommendations: `aws compute-optimizer
   get-ec2-instance-recommendations --instance-arns <arn>`.
2. Check `lastRefreshTimestamp` on the new finding.
3. Re-evaluate with fresh data.

### For OK

1. No remediation required for the current posture.
2. Recommend installing CWAgent if not present (defense-in-depth for future
   findings).
3. Recommend reviewing findings quarterly as workloads evolve.

## Deep reference: Compute Optimizer internals

### Analysis window and data sources

Compute Optimizer analyses the trailing **30 days** of CloudWatch metrics.
The minimum data threshold is **30 hours of continuous** utilization within
that window. Resources that do not accumulate 30 hours (frequently stopped
instances, rarely invoked Lambda functions) receive no finding.

For EC2, the data sources are:
- **CPU** — always available from CloudWatch (`AWS/EC2` namespace,
  `CPUUtilization`).
- **Memory** — only available when CloudWatch Agent is installed
  (`CWAgent` namespace, `mem_used_percent`). Without CWAgent, Memory is
  inferred from instance type specifications.
- **Network** — always available (`NetworkIn`, `NetworkOut`).
- **Disk** — available for instance-store volumes (`DiskReadOps`,
  `DiskWriteOps`). EBS-attached volumes are analysed separately via the EBS
  recommendations API.

### Recommendation option ranking

Recommendation options are ranked by `savingsOpportunity`
(highest savings first), NOT by safety. The `performanceRisk` field (1-5)
is the safety indicator — it is independent of ranking. Always evaluate
both fields: an option with high savings but performanceRisk 5 is not
actionable.

### Finding refresh cycle

Compute Optimizer refreshes findings approximately every **24 hours**. The
`lastRefreshTimestamp` on each finding indicates when it was last
recomputed. A finding with a stale timestamp (> 30 days) may indicate:
(1) the resource was stopped or terminated, (2) Compute Optimizer lost
access to CloudWatch data, or (3) enrollment was paused. Always verify
resource state before acting on a stale finding.

### EBS volume type migration matrix

| From | To | Performance impact | Cost impact |
|---|---|---|---|
| gp2 | gp3 | Baseline 3,000 IOPS / 125 MiB/s (vs gp2's size-scaled IOPS). Purchase provisioned IOPS to match. | Cheaper per GB; may need provisioned IOPS for parity. |
| io1 | gp3 | gp3 caps at 16,000 IOPS; io1 supports up to 64,000. High-IOPS workloads may lose performance. | Significantly cheaper. |
| st1 | gp3 | gp3 is SSD (random I/O); st1 is HDD (sequential). Random-I/O workloads improve, sequential may not. | More expensive per GB but better random I/O. |

### Lambda memory-cost relationship

Lambda allocates CPU proportional to memory (approximately 1 vCPU per
1,769 MB). Increasing memory increases CPU, which can reduce duration. The
optimal memory setting minimises `memory × duration` (total cost). Compute
Optimizer's Lambda recommendations model this trade-off, but always verify
with `aws lambda get-function` and CloudWatch Duration metrics
post-change.

## Recent AWS features (2024-2026)

- **EBS volume recommendations (2024):** Compute Optimizer now provides right-sizing recommendations for EBS volumes (gp2 to gp3, io1 to io2, size adjustments). Auditors should include EBS findings in the cost-optimization review alongside EC2 and Lambda.
- **Enhanced finding filters and trade-off analysis (2024-2025):** Compute Optimizer now supports filtering by workload metadata and trade-off analysis between cost and performance risk. Auditors should verify that the finding confidence and performance-risk thresholds are appropriate before acting on recommendations.
- **ECS service recommendations (2024):** Compute Optimizer now provides right-sizing recommendations for ECS services (CPU and memory task-size optimization). Auditors should include ECS task-definition findings in the optimization review.

## Domain

AWS CloudOps / Compute Cost Optimization & Right-Sizing.

## AWS documentation

- **AWS Compute Optimizer User Guide** — https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is.html
- **Compute Optimizer Security** — https://docs.aws.amazon.com/compute-optimizer/latest/ug/security.html
- **Compute Optimizer API Reference** — https://docs.aws.amazon.com/compute-optimizer/latest/APIReference/
- **Compute Optimizer CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/compute-optimizer/
