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

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

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

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

## Expert edge cases — non-obvious Compute Optimizer behaviors

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

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

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

## Remediation guidance

Moved verbatim to [references/error-handling.md](references/error-handling.md) - load on demand (see References below).

## Deep reference: Compute Optimizer internals

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — secondary worked example (LOW-confidence inferred memory) moved from SKILL.md
- [references/advanced-patterns.md](references/advanced-patterns.md) — expert edge cases, deep internals reference, 2024-2026 features moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live pre-flight checks + pre-rightsize safety checks moved from SKILL.md
- [references/error-handling.md](references/error-handling.md) — per-verdict remediation guidance moved from SKILL.md

## Domain

AWS CloudOps / Compute Cost Optimization & Right-Sizing.

## AWS documentation

- **AWS Compute Optimizer User Guide** — https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is.html
- **Compute Optimizer Security** — https://docs.aws.amazon.com/compute-optimizer/latest/ug/security.html
- **Compute Optimizer API Reference** — https://docs.aws.amazon.com/compute-optimizer/latest/APIReference/
- **Compute Optimizer CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/compute-optimizer/
