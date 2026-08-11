---
name: elb-cost-optimizer
description: >-
  Optimizes Elastic Load Balancer cost across seven dimensions: ALB
  vs NLB vs CLB cost comparison and migration, LCU (Load Balancer
  Capacity Unit) analysis across the four billing dimensions (new
  connections, active connections, processed bytes, rule evaluations),
  target group consolidation via multi-path routing, cross-zone load
  balancing cost impact, idle load balancer detection, connection
  draining timeout tuning, CLB-to-ALB/NLB migration savings, data
  transfer cost reduction via PrivateLink, ALB access log volume
  reduction, and SSL certificate overhead. Reads CloudWatch LCU
  metrics, ELB configurations, and Cost Explorer data. Emits
  FURTHER_OPTIMIZATION_AVAILABLE or OPTIMIZED with estimated savings
  and consolidation steps. Use when reviewing ELB spend, analyzing
  LCU costs, consolidating ALBs, migrating CLBs, or a FinOps review
  of load balancer spend.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). Offline recommendation classification works from
  pasted CloudWatch LCU metrics, ELB configurations, and Cost
  Explorer data. Live-account optimization uses aws elbv2
  describe-load-balancers, describe-target-groups, describe-listeners,
  describe-rules, aws cloudwatch get-metric-statistics
  (ConsumedLCUs, NewConnectionCount, ActiveConnectionCount,
  ProcessedBytes, RuleEvaluations), aws ce get-cost-and-usage, and
  aws elb describe-load-balancers (for CLB inventory, AWS CLI v2,
  SSO or key-based credentials).
keywords:
  - Elastic Load Balancer
  - ALB
  - NLB
  - CLB
  - LCU
  - Load Balancer Capacity Unit
  - multi-path routing
  - target group consolidation
  - cross-zone
  - idle load balancer
  - CLB migration
  - PrivateLink
  - access logs
  - SSL certificate
  - connection draining
  - FinOps
  - cost optimization
tags: [elb, alb, nlb, clb, networking, cost-optimization, finops, lcu, load-balancer]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Networking
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: >-
    Optimizing ELB cost, analyzing LCU (Load Balancer Capacity Unit)
    utilization across the four billing dimensions, consolidating ALBs
    via multi-path routing and target group merging, evaluating CLB
    to ALB/NLB migration, detecting idle load balancers, tuning
    connection draining timeouts, reducing cross-zone data transfer
    costs, evaluating PrivateLink for inter-AZ traffic reduction,
    reducing ALB access log volume, or conducting a FinOps review of
    load balancer spend.
  when_not_to_use: >-
    ALB 5xx error troubleshooting (use alb-5xx-troubleshooter),
    CLB-to-ALB migration execution (use clb-to-alb-migration-operator),
    Route 53 cost optimization (use route53-cost-optimizer), or VPC
    data transfer optimization (use data-transfer-optimizer). This
    skill focuses on cost-driven optimization, not functional
    debugging or migration execution.
  activation_triggers:
    - "optimise ELB cost"
    - "ALB LCU analysis"
    - "load balancer cost"
    - "idle load balancer"
    - "CLB to ALB migration cost"
    - "target group consolidation"
    - "multi-path routing"
    - "reduce ALB count"
    - "cross-zone load balancing cost"
    - "LCU dimensions"
    - "ELB FinOps"
    - "reduce load balancer bill"
    - "NLB vs ALB cost"
    - "PrivateLink data transfer"
    - "ALB access log cost"
  invocation_schema: >-
    Input: either (a) a load balancer ARN with live-account context,
    (b) CloudWatch LCU metrics (ConsumedLCUs, NewConnectionCount,
    ActiveConnectionCount, ProcessedBytes, RuleEvaluations) with at
    least 14 days of observation, OR (c) an ELB configuration with
    listener and target group details. Output: a deterministic TARGET
    / VERDICT / REASON / RECOMMENDATION / ESTIMATED_SAVINGS /
    ACTION_STEPS block per load balancer or fleet, where VERDICT is
    one of {OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE}.
---

# ELB Cost Optimizer

## Activation

Activate this skill when the user reports Elastic Load Balancer cost
concerns. Trigger phrases: "optimise ELB cost", "ALB LCU analysis",
"load balancer cost", "idle load balancer", "CLB to ALB migration
cost", "target group consolidation", "multi-path routing", "reduce
ALB count", "cross-zone load balancing cost", "LCU dimensions", "ELB
FinOps", "reduce load balancer bill".

## Mindset

**One-line takeaway:** ELB cost is driven by the highest of four LCU
dimensions, not the sum. ALB charges per LCU-hour where 1 LCU is the
max of: 25 new connections/sec, 3000 active connections, 1 GB/hour
processed bytes, or 1000 rule evaluations/sec. You pay for the peak
dimension. The optimal ALB minimizes the peak dimension's value while
consolidating ALB instances via multi-path routing. Start with idle
detection, then LCU optimization, then consolidation.

Three facts make ELB cost optimization different from generic
infrastructure tuning:

- **LCU is a max-function, not a sum.** If your ALB does 2000 new
  connections/sec (80 LCUs) but only 0.1 GB/hour processed (0.1 LCU),
  you pay for 80 LCUs. The other three dimensions are free but wasted.
  Optimization means reducing the peak dimension — not the average.
- **CLBs are billed per-hour plus per-GB, with no LCU concept.** A CLB
  at $0.025/hour ($18.25/month) seems cheaper than an ALB at
  $0.0225/hour ($16.43/month) — but CLBs lack path-based routing,
  have lower performance, and cannot be consolidated. Migrating CLBs
  to ALBs enables multi-path routing, which can consolidate 5 CLBs
  into 1 ALB, saving 80% of the per-hour cost.
- **Cross-zone load balancing on NLBs incurs data transfer charges.**
  NLBs charge $0.01/GB for cross-zone traffic. ALBs include
  cross-zone traffic in the LCU price. For high-traffic workloads,
  this difference alone can make ALB cheaper than NLB.

## Quick reference — load balancer pricing (us-east-1, 2026)

| Type | Hourly rate | LCU/GB rate | Monthly base (730h) | Best for |
|---|---|---|---|---|
| ALB | $0.0225/h | $0.008/LCU-h | $16.43 | HTTP/HTTPS, path routing |
| NLB | $0.0225/h | $0.006/GB processed | $16.43 | TCP/UDP, extreme perf |
| CLB | $0.025/h | $0.008/GB processed | $18.25 | Legacy only — migrate |
| Gateway LB | $0.0125/h | $0.0035/GB | $9.13 | Third-party security appliances |

## Quick navigation

| Section | Purpose |
|---|---|
| **Step 0** | Capture the ELB inventory and LCU metrics |
| **Step 1** | Classify the optimization category (A-G) |
| **Step 2** | IDLE_LB: detect and eliminate idle load balancers |
| **Step 3** | LCU_DIM: LCU dimension analysis and peak reduction |
| **Step 4** | CONSOLIDATION: multi-path routing to reduce ALB count |
| **Step 5** | CLB_MIGRATION: CLB-to-ALB/NLB cost savings |
| **Step 6** | DATA_TRANSFER: cross-zone and PrivateLink optimization |
| **Step 7** | Root-cause catalog (top patterns + canonical fixes) |
| **Step 8** | Verify the recommendation |
| **Step 9** | Decide VERDICT (OPTIMIZED / FURTHER_OPTIMIZATION_AVAILABLE) |

## STRICT output contract

```text
TARGET: <load balancer ARN or name> — <type, region>
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE | OPTIMIZED
REASON: <summary of LCU analysis, idle detection, consolidation opportunities>
RECOMMENDATION:
  1. <IDLE_LB recommendation: delete or consolidate idle LB>
  2. <LCU_DIM recommendation: reduce peak LCU dimension>
  3. <CONSOLIDATION recommendation: merge target groups via multi-path>
  4. <CLB_MIGRATION recommendation: migrate CLB to ALB/NLB>
  5. <DATA_TRANSFER recommendation: cross-zone or PrivateLink savings>
ESTIMATED_SAVINGS: $<monthly savings> ($<annual savings>)
ACTION_STEPS:
  1. <specific step with AWS CLI or console action>
  2. <verification step>
  3. <rollback step>
```

## NEVER

- **NEVER** delete a load balancer without verifying it has zero
  active traffic for at least 7 days. An "idle" ALB might serve a
  rarely-used internal API, a disaster-recovery endpoint, or a
  blue/green standby. Check Route 53 records, target group health
  checks, and CloudWatch request count before deletion. Always tag
  the LB for 7-day observation before deleting.

- **NEVER** consolidate ALBs without verifying the TLS certificate
  coverage. Multi-path routing requires a single TLS certificate that
  covers all hostnames (via SAN or wildcard). If each ALB has a
  separate certificate for a different domain, consolidation requires
  a multi-domain certificate first. Forgetting this causes TLS
  handshake failures after consolidation.

- **NEVER** assume NLB is cheaper than ALB without calculating
  cross-zone data transfer. NLB charges $0.01/GB for cross-zone
  traffic. For a workload processing 5 TB/month cross-zone, that is
  $51/month in data transfer alone — potentially making ALB cheaper
  despite the higher per-GB rate. Always calculate the total cost
  including data transfer.

- **NEVER** migrate a CLB to an NLB when the workload uses HTTP
  features. NLB operates at Layer 4 (TCP/UDP) and does not support
  path-based routing, host-based routing, SSL termination with SNI,
  or X-Forwarded-For headers. A CLB serving HTTP traffic should
  migrate to ALB, not NLB. Migrating to NLB breaks HTTP features.

- **NEVER** disable cross-zone load balancing on an ALB to save cost.
  ALBs include cross-zone traffic in the LCU price — there is no
  additional charge. Disabling cross-zone on an ALB has no cost
  benefit and degrades availability. (On NLBs, disabling cross-zone
  avoids the $0.01/GB charge but may cause uneven distribution.)

- **NEVER** ignore access log costs for high-traffic ALBs. ALB access
  logs are stored in S3 at $0.023/GB/month. A high-traffic ALB can
  generate 100+ GB/month of access logs ($2.30/month + PUT request
  costs). While not the primary cost driver, it compounds with
  multiple ALBs. Consider sampling, lifecycle rules, or disabling
  for non-production ALBs.

## Process — ELB cost optimization decision tree (apply in order)

### Step 0: Capture the ELB inventory and LCU metrics

Gather these inputs. Each step below branches on which are available.

| Signal | Source | Why required |
|---|---|---|
| **Load balancer inventory** | `aws elbv2 describe-load-balancers` | ALB/NLB configs, type, scheme, VPC |
| **CLB inventory** | `aws elb describe-load-balancers` | Legacy CLBs, migration candidates |
| **Listeners and rules** | `aws elbv2 describe-listeners`, `describe-rules` | Path-based routing, rule count |
| **Target groups** | `aws elbv2 describe-target-groups` | Consolidation opportunities |
| **LCU metrics** | CloudWatch `ConsumedLCUs`, `NewConnectionCount`, `ActiveConnectionCount`, `ProcessedBytes`, `RuleEvaluations` | LCU dimension analysis |
| **Cost data** | `aws ce get-cost-and-usage` filtered by ELB | Baseline spend |

If the user has not provided LB data or metrics, output:

```text
TARGET: <load balancer or account>
VERDICT: NEED_MORE_INFO
REASON: Cannot optimize ELB cost without LCU metrics and LB inventory.
MISSING:
  - Load balancer ARN or name
  - CloudWatch ConsumedLCUs (14+ days)
  - CloudWatch per-dimension metrics: NewConnectionCount,
    ActiveConnectionCount, ProcessedBytes, RuleEvaluations
  - Listener and target group configuration
  - Monthly ELB spend (from Cost Explorer)
```

```bash
# List all ALBs and NLBs:
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[*].{name:LoadBalancerName,arn:LoadBalancerArn,type:Type,scheme:Scheme,vpc:VpcId,dns:DNSName,created:CreatedTime}'

# List all CLBs (legacy):
aws elb describe-load-balancers \
  --query 'LoadBalancerDescriptions[*].{name:LoadBalancerName,dns:DNSName,scheme:Scheme,created:CreatedTime}'

# Pull 14-day LCU consumption (ALB):
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name ConsumedLCUs \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Average Maximum \
  --query 'Datapoints[*].{time:Timestamp,avg:Average,max:Maximum}'
```

### Step 1: Identify the optimization category

| Category | Signal | Diagnostic step |
|---|---|---|
| **A. IDLE_LB** | RequestCount < 100/day or zero healthy targets for 7+ days | Step 2 |
| **B. LCU_DIM** | ConsumedLCUs > 10 (indicating a high peak dimension) | Step 3 |
| **C. CONSOLIDATION** | Multiple ALBs in the same VPC serving related paths | Step 4 |
| **D. CLB_MIGRATION** | Any active CLB in the account | Step 5 |
| **E. DATA_TRANSFER** | NLB with cross-zone enabled + high GB processed | Step 6 |
| **F. ALREADY_OPTIMAL** | Right-sized, consolidated, no CLBs, LCU-efficient | Verdict: OPTIMIZED |
| **G. ACCESS_LOGS** | ALB access logs to S3 with no lifecycle policy | Step 6 |

**Apply A before B before C.** Eliminating idle LBs is the easiest
win (delete = 100% savings). Then reduce LCU consumption. Then
consolidate remaining LBs. CLB migration is a larger project —
schedule it separately.

### Step 2: IDLE_LB — detect and eliminate idle load balancers

An idle load balancer costs $16.43/month (ALB/NLB) or $18.25/month
(CLB) just for existing — plus LCU/GB charges for any minimal traffic.
Idle LBs are the #1 ELB cost waste.

**Idle detection criteria:**

| Metric | Threshold | Action |
|---|---|---|
| RequestCount (ALB) | < 100/day for 7 days | Candidate for deletion |
| ProcessedBytes (NLB) | < 1 MB/day for 7 days | Candidate for deletion |
| HealthyHostCount | 0 for 7 days | Delete — no targets registered |
| NewConnectionCount | < 50/day for 7 days | Investigate; likely deletable |

**Diagnostic commands:**

```bash
# Check ALB request count (14-day daily):
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Sum \
  --query 'Datapoints[*].{time:Timestamp,sum:Sum}'

# Check healthy host count:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HealthyHostCount \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> Name=TargetGroup,Value=<tg-full-name> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Average Minimum

# Check Route 53 records pointing to the LB (avoid orphaning DNS):
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> \
  --query 'ResourceRecordSets[?contains(ResourceRecords[].Value, `<lb-dns-name>`) || contains(AliasTarget.DNSName, `<lb-dns-name>`)]'
```

**Savings: deleting one idle ALB = $16.43/month + LCU charges.
Deleting 5 idle ALBs = $82+/month.**

### Step 3: LCU_DIM — LCU dimension analysis and peak reduction

ALB charges per LCU-hour. The LCU rate is $0.008/hour. The number of
LCUs is determined by the MAX of four dimensions:

**LCU dimension definitions:**

| Dimension | 1 LCU = | Metric name |
|---|---|---|
| New connections | 25 new connections/sec | NewConnectionCount |
| Active connections | 3000 active connections | ActiveConnectionCount |
| Processed bytes | 1 GB/hour (2.78 Mbps) | ProcessedBytes |
| Rule evaluations | 1000 rule evaluations/sec | RuleEvaluations |

**LCU calculation example:**

| Dimension | Observed value | LCUs consumed |
|---|---|---|
| New connections | 500/sec | 500/25 = 20.0 LCU |
| Active connections | 15,000 | 15000/3000 = 5.0 LCU |
| Processed bytes | 2 GB/hour | 2/1 = 2.0 LCU |
| Rule evaluations | 3000/sec | 3000/1000 = 3.0 LCU |
| **Peak (billed)** | | **20.0 LCU** |

You pay for 20 LCU/hour = $0.16/hour = $116.80/month.

**The peak dimension is "new connections" at 20 LCU.** Reducing the
other three dimensions to zero saves nothing. The only way to reduce
the bill is to reduce new connections/sec.

**Peak dimension reduction strategies:**

| Peak dimension | Reduction strategy | Expected savings |
|---|---|---|
| New connections | Connection reuse (HTTP keep-alive), merge endpoints | 30-60% |
| Active connections | Reduce idle timeout (default 60s), connection draining | 10-30% |
| Processed bytes | Response compression (gzip/brotli), reduce payload | 20-50% |
| Rule evaluations | Reduce listener rules, simplify conditions | 10-40% |

**Diagnostic commands for per-dimension analysis:**

```bash
# New connections per second (14-day hourly):
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name NewConnectionCount \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum

# Active connections:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name ActiveConnectionCount \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum

# Processed bytes:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name ProcessedBytes \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum

# Rule evaluations:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name RuleEvaluations \
  --dimensions Name=LoadBalancer,Value=<lb-full-name> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum
```

### Step 4: CONSOLIDATION — multi-path routing to reduce ALB count

Multiple ALBs in the same VPC serving related services can often be
consolidated into a single ALB using path-based and host-based
routing. Each consolidated ALB saves $16.43/month + its LCU charges.

**Consolidation decision table:**

| Scenario | Consolidate? | Method |
|---|---|---|
| 3 ALBs, each serving one microservice, same domain | YES | Host-based routing (one ALB, 3 listener rules on host header) |
| 5 ALBs, each serving one path of the same domain | YES | Path-based routing (one ALB, 5 listener rules on path pattern) |
| 2 ALBs in different VPCs (prod and staging) | NO | Different VPCs — keep separate |
| 1 ALB internal + 1 ALB internet-facing for the same service | MAYBE | Can use one ALB with both schemes? No — ALB scheme is immutable. Keep separate. |
| 4 ALBs with different TLS certificates for different domains | YES (with SAN cert) | Obtain a multi-domain certificate; consolidate with SNI |

**Example: 3 ALBs -> 1 ALB consolidation**

Before: 3 ALBs at $16.43/month each = $49.29/month + LCU charges.
After: 1 ALB at $16.43/month + LCU charges (merged).
**Savings: $32.86/month minimum (just from per-hour charges).**

```bash
# Create path-based rules on the consolidated ALB:
aws elbv2 create-rule \
  --listener-arn <listener-arn> \
  --priority 10 \
  --conditions Field=path-pattern,Values='/api/*' \
  --actions Type=forward,TargetGroupArn=<api-tg-arn>

aws elbv2 create-rule \
  --listener-arn <listener-arn> \
  --priority 20 \
  --conditions Field=path-pattern,Values='/admin/*' \
  --actions Type=forward,TargetGroupArn=<admin-tg-arn>

aws elbv2 create-rule \
  --listener-arn <listener-arn> \
  --priority 30 \
  --conditions Field=path-pattern,Values='/static/*' \
  --actions Type=forward,TargetGroupArn=<static-tg-arn>
```

### Step 5: CLB_MIGRATION — CLB to ALB/NLB cost and feature savings

Classic Load Balancers (CLBs) are a legacy product with no new feature
development. They cost $0.025/hour ($18.25/month) plus $0.008/GB
processed. Migrating to ALB or NLB saves on per-hour cost AND enables
modern features (path routing, SNI, LCU-based pricing).

**CLB migration decision:**

| CLB workload | Migrate to | Rationale |
|---|---|---|
| HTTP/HTTPS traffic | ALB | Path routing, LCU pricing, SNI, better metrics |
| TCP/UDP traffic | NLB | Higher performance, static IPs, lower latency |
| Mixed HTTP + TCP | ALB for HTTP, NLB for TCP | Split services across two LB types |

**CLB vs ALB cost comparison (1 TB/month processed):**

| Type | Hourly | GB rate | Monthly total | Features |
|---|---|---|---|---|
| CLB | $0.025/h | $0.008/GB | $18.25 + $8.00 = $26.25 | Legacy, no path routing |
| ALB | $0.0225/h | LCU-based | $16.43 + LCU charges | Path routing, SNI, metrics |
| NLB | $0.0225/h | $0.006/GB | $16.43 + $6.00 = $22.43 | TCP/UDP, static IPs |

```bash
# Describe CLB listeners and backends for migration planning:
aws elb describe-load-balancers \
  --load-balancer-names <clb-name> \
  --query 'LoadBalancerDescriptions[*].{name:LoadBalancerName,listeners:ListenerDescriptions,instances:Instances,scheme:Scheme,subnets:Subnets,sg:SecurityGroups}'

# Create the target group for the migrated ALB:
aws elbv2 create-target-group \
  --name migrated-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id <vpc-id> \
  --health-check-path /health \
  --health-check-interval-seconds 30

# Create the replacement ALB:
aws elbv2 create-load-balancer \
  --name migrated-alb \
  --subnets <subnet-1> <subnet-2> \
  --security-groups <sg-id> \
  --scheme internet-facing \
  --type application
```

### Step 6: DATA_TRANSFER — cross-zone and PrivateLink optimization

**Cross-zone load balancing:**

| LB type | Cross-zone default | Cost impact |
|---|---|---|
| ALB | Always on (cannot disable) | Included in LCU price — no extra charge |
| NLB | Off by default (can enable) | $0.01/GB for cross-AZ traffic when enabled |

For NLBs with cross-zone enabled, the cross-AZ data transfer can
exceed the NLB hourly cost. A 5 TB/month NLB with cross-zone enabled
incurs $51/month in data transfer alone.

**PrivateLink cost reduction:**

When ALBs serve traffic from clients in different VPCs, the traffic
crosses VPC peering or Transit Gateway, incurring data transfer
charges. PrivateLink (interface VPC endpoints) can reduce this cost
by keeping traffic within the AWS network.

**Decision: NLB cross-zone on vs off:**

| Scenario | Recommendation | Rationale |
|---|---|---|
| Targets evenly distributed across AZs | OFF | Each AZ handles its own traffic; no cross-AZ charge |
| Targets concentrated in one AZ | ON | Without cross-zone, one AZ is overloaded |
| Clients concentrated in one AZ | OFF | Route to local AZ targets; avoid cross-AZ |
| Unpredictable traffic distribution | ON | Better availability; accept cross-AZ charge |

**Access log optimization:**

ALB access logs are stored in S3 at $0.023/GB/month. For high-traffic
ALBs:

| ALB traffic | Log volume/month | S3 cost/month |
|---|---|---|
| 1M req/day | ~30 GB | $0.69 |
| 10M req/day | ~300 GB | $6.90 |
| 100M req/day | ~3000 GB | $69.00 |

**Recommendation:** Apply S3 lifecycle rules to transition access logs
to Standard-IA after 30 days, Glacier after 90 days, and expire after
1 year. This reduces the effective S3 cost by 70-90%.

### Step 7: Map to root-cause catalog

| # | Pattern | Category | Fix | Est. savings |
|---|---|---|---|---|
| 1 | ALB with < 100 requests/day for 7+ days | IDLE_LB | Delete the ALB | $16.43+/month per ALB |
| 2 | ALB with 0 healthy targets for 7+ days | IDLE_LB | Delete; no traffic possible | $16.43+/month |
| 3 | Peak LCU dimension = new connections (keep-alive disabled) | LCU_DIM | Enable HTTP keep-alive on targets | 30-60% LCU reduction |
| 4 | Peak LCU dimension = active connections (idle timeout 60s) | LCU_DIM | Reduce idle timeout to 30s | 10-30% LCU reduction |
| 5 | Peak LCU dimension = processed bytes (no compression) | LCU_DIM | Enable gzip/brotli compression | 20-50% LCU reduction |
| 6 | Peak LCU dimension = rule evaluations (too many rules) | LCU_DIM | Simplify rule conditions, reduce rules | 10-40% LCU reduction |
| 7 | 3+ ALBs in same VPC serving related paths | CONSOLIDATION | Multi-path routing into single ALB | $32.86+/month per merged ALB |
| 8 | Active CLB serving HTTP traffic | CLB_MIGRATION | Migrate to ALB | $1.82+/month + feature gains |
| 9 | NLB with cross-zone enabled + 5 TB/month | DATA_TRANSFER | Disable cross-zone if targets evenly distributed | $51/month |
| 10 | ALB access logs with no S3 lifecycle | ACCESS_LOGS | Add lifecycle: IA@30d, Glacier@90d, expire@365d | 70-90% of log S3 cost |

### Step 8: Verify the recommendation

- **For IDLE_LB:** tag the LB for 7 days before deletion. After 7 days
  of zero traffic, delete. Verify Route 53 records are updated.
- **For LCU_DIM:** after enabling keep-alive or compression, monitor
  ConsumedLCUs for 7 days. Verify the peak dimension dropped.
- **For CONSOLIDATION:** after merging ALBs, verify all paths route
  correctly. Test each listener rule. Monitor 5xx error rate for 24
  hours. Keep the old ALBs tagged but not deleted for 7 days as
  rollback.
- **For CLB_MIGRATION:** migrate traffic gradually (DNS weighted
  routing). Monitor error rates and latency for 7 days before
  decommissioning the CLB.
- **For DATA_TRANSFER:** after disabling NLB cross-zone, verify target
  health and traffic distribution remain balanced across AZs.

### Step 9: Decide — OPTIMIZED vs FURTHER_OPTIMIZATION_AVAILABLE

- **FURTHER_OPTIMIZATION_AVAILABLE.** At least one dimension has a
  cost optimization opportunity. Output RECOMMENDATION and
  ESTIMATED_SAVINGS.
- **OPTIMIZED.** No idle LBs, LCU peak dimension is well-managed,
  ALBs are consolidated where possible, no CLBs, data transfer is
  optimized, and access logs have lifecycle rules. No further action.

## Expert heuristic — "LCU is max not sum, consolidate to cut the floor, idle is free money"

Three rules, in order, produce 90% of ELB savings:

1. **LCU dimension maximization.** ALB bills on the MAX of four
   dimensions, not the sum. Identify the peak dimension and focus all
   optimization there. If new connections is the peak at 20 LCU, then
   reducing active connections from 5 LCU to 0 saves nothing. Enable
   keep-alive (reduces new connections by 80%+), compress responses
   (reduces processed bytes), and simplify rules (reduces rule
   evaluations). The peak dimension determines the bill.

2. **Multi-path routing to consolidate ALBs.** Each ALB costs
   $16.43/month minimum. Ten ALBs cost $164/month. Consolidating to
   three ALBs (one per environment: prod, staging, dev) using host-based
   and path-based routing saves $114/month. Use a single multi-domain
   TLS certificate (SAN) to cover all hostnames.

3. **CLB elimination urgency.** Every CLB is $18.25/month plus per-GB
   charges, with no path routing, no LCU-based pricing, and no new
   features. Migrating CLBs to ALBs is both a cost saving ($1.82/month
   per CLB on hourly rate alone) and a feature upgrade. Prioritize CLBs
   with the highest traffic — the per-GB savings are larger.

**The idle LB is the lowest-hanging fruit.** A single idle ALB at
$16.43/month costs $197/year for nothing. In accounts with 10+
ALBs, typically 2-3 are idle (leftover from testing, deprecated
services, or blue/green standby). Deleting them is 100% savings with
zero risk.

## Configuration dependency graph

```
ELB Inventory (describe-load-balancers + describe-load-balancers for CLB)
  |
  +-- RequestCount / ProcessedBytes (CloudWatch, 14-day)
  |     |
  |     +-- [IDLE_LB] -> Tag 7 days -> Delete if confirmed idle
  |
  +-- ConsumedLCUs (CloudWatch, 14-day)
  |     |
  |     +-- Per-dimension metrics (NewConn, ActiveConn, Bytes, RuleEval)
  |     |     |
  |     |     +-- [LCU_DIM] -> Reduce peak dimension (keep-alive, compression, rule simplification)
  |     |
  |     +-- Total LCU cost = peak_LCU x $0.008/h x 730h
  |
  +-- Listeners + Rules (describe-listeners + describe-rules)
  |     |
  |     +-- [CONSOLIDATION] -> Merge ALBs via multi-path routing
  |           |
  |           +-- TLS Certificate (acm list-certificates) -> SAN cert for multi-domain
  |
  +-- CLB Inventory (elb describe-load-balancers)
  |     |
  |     +-- [CLB_MIGRATION] -> Migrate to ALB (HTTP) or NLB (TCP/UDP)
  |
  +-- NLB cross-zone setting + ProcessedBytes
  |     |
  |     +-- [DATA_TRANSFER] -> Disable cross-zone if targets evenly distributed
  |
  +-- ALB Access Logs -> S3
        |
        +-- [ACCESS_LOGS] -> Lifecycle: IA@30d, Glacier@90d, expire@365d
```

## Recent AWS features (2024-2026)

- **ALB Zonal DNS Exclusion (2024-2025):** ALB now supports zonal DNS
  exclusion, allowing you to route traffic only to specific AZs. This
  reduces cross-AZ data transfer for workloads with geographically
  concentrated clients.
- **NLB cross-zone traffic visibility (2024-2025):** CloudWatch now
  provides per-AZ metrics for NLB cross-zone traffic, making it easier
  to quantify the cost impact of cross-zone load balancing.
- **ALB access log partitioning (2025-2026):** ALB access logs now
  support S3 partitioning by date and load balancer name, improving
  query performance and reducing Athena scan costs for log analysis.
- **L7 load balancer capacity unit improvements (2024-2026):** AWS
  has increased the LCU efficiency for ALBs handling HTTP/2 and HTTP/3
  (QUIC) traffic, reducing the effective LCU consumption for modern
  protocol workloads.
- **PrivateLink integration with ALB (2024-2026):** AWS PrivateLink
  now supports ALB as a resource, allowing private connectivity to ALB
  endpoints across VPCs without internet gateway or NAT gateway
  charges.

## References

See `references/elb-pricing-and-lcu-matrix.md` for the full pricing
reference (ALB/NLB/CLB rates, LCU dimension calculations, data transfer
rates, regional notes) and `references/elb-optimization-commands.md`
for the canonical command script for each optimization dimension.

## Domain

AWS CloudOps / Networking FinOps & Load Balancer Cost Optimization.

## AWS documentation

- **Elastic Load Balancing pricing** — https://aws.amazon.com/elasticloadbalancing/pricing/
- **ALB LCU details** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-cloudwatch-metrics.html
- **CLB to ALB migration** — https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/migrate-classic-load-balancer.html
- **Listener rules** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-rules.html
- **NLB cross-zone** — https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-target-groups.html#cross-zone-load-balancing
- **ALB access logs** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html
- **AWS PrivateLink** — https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html
- **ACM certificates** — https://docs.aws.amazon.com/acm/latest/userguide/acm-overview.html
