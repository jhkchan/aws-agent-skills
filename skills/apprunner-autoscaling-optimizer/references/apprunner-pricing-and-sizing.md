# App Runner Pricing and Sizing Reference

Load this reference when analyzing App Runner cost or planning instance
type and concurrency changes. The data below covers published us-east-1
rates as of 2026, the cost model, and sizing heuristics.

## Pricing model

App Runner bills in two dimensions:

### 1. Compute (provisioned or on-demand)

| Billing mode | Trigger | Rate | When it applies |
|---|---|---|---|
| **Provisioned** | MinSize >= 1 | Per-hour (even when idle) | Always-on baseline instances |
| **On-demand** | Instance processing a request | Per-second (sub-second billing) | Any instance handling traffic, including provisioned instances above MinSize |

**Key insight:** Provisioned instances are billed per-hour for the baseline.
On-demand instances are billed per-second only while processing requests.
With MinSize 0 and no traffic, compute cost is zero (scale-to-zero).

### 2. Instance type pricing (us-east-1, 2026)

| Instance type | Provisioned rate | On-demand rate | vCPU | Memory |
|---|---|---|---|---|
| 1 vCPU / 2 GB | $0.063/hr | $0.0000175/s | 1 | 2 GB |
| 2 vCPU / 4 GB | $0.126/hr | $0.0000350/s | 2 | 4 GB |
| 4 vCPU / 8 GB | $0.252/hr | $0.0000700/s | 4 | 8 GB |

### Monthly cost examples (730 hours/month)

| Scenario | Instance type | MinSize | Calculation | Monthly compute |
|---|---|---|---|---|
| Always-on, no traffic | 1 vCPU / 2 GB | 1 | $0.063 * 730 | ~$46/month |
| Always-on, no traffic | 2 vCPU / 4 GB | 1 | $0.126 * 730 | ~$92/month |
| Scale-to-zero, 8M req | 1 vCPU / 2 GB | 0 | per-second * avg duration * request count | ~$200-400/month |
| 24/7 at 3 avg instances | 1 vCPU / 2 GB | 1 | 1 * $0.063 * 730 + 2 * on-demand | ~$300-500/month |

### 3. Additional costs

| Cost type | Rate | Notes |
|---|---|---|
| **NAT gateway (if VPC connector)** | $0.045/GB processed + $0.045/GB transferred + $0.045/hr | Applies to all internet-bound traffic from VPC |
| **VPC endpoint (private link)** | $0.010/hr + $0.01/GB | For S3 Gateway endpoints: free (no hourly or per-GB charge) |
| **CloudWatch Logs ingestion** | $0.50/GB ingested | App Runner sends logs by default |
| **CloudWatch Logs storage** | $0.03/GB/month | After first 5 GB free tier |
| **ECR container storage** | $0.10/GB/month | For the container image |
| **Custom domain (managed cert)** | Free (ACM) | No per-certificate charge |
| **Data transfer (out to internet)** | $0.09/GB (first 10TB) | Applies to response data sent to clients |

## Concurrency cost model

Concurrency does not have a direct charge. It controls how many concurrent
HTTP requests one instance handles. The autoscaler provisions instances
based on:

```
Required instances = ceil(total_concurrent_requests / concurrency_setting)
```

**Example:**
- 1,000 concurrent requests
- Concurrency 100 → 10 instances
- Concurrency 200 → 5 instances (50% cost reduction)
- Concurrency 50 → 20 instances (100% cost increase)

**The tradeoff:** Higher concurrency = fewer instances = lower cost, but
each instance handles more work. For CPU-bound workloads, this directly
increases latency. For I/O-bound workloads (async I/O, database queries),
the impact is minimal.

## Sizing heuristics

### Instance type selection

| Workload profile | Recommended type | Rationale |
|---|---|---|
| Simple web API, low traffic | 1 vCPU / 2 GB | Cheapest option; scale horizontally |
| Standard web API, moderate traffic | 1 vCPU / 2 GB | Use concurrency 80-100 |
| CPU-intensive (image processing, ML inference) | 2 vCPU / 4 GB or 4 vCPU / 8 GB | CPU is the bottleneck |
| Memory-intensive (large datasets, caching) | 2 vCPU / 4 GB or 4 vCPU / 8 GB | Memory pressure at high concurrency |
| Batch processing, background workers | 1 vCPU / 2 GB | Burst traffic; scale-to-zero between batches |

### Concurrency sweet spots

| Workload type | Recommended concurrency | Rationale |
|---|---|---|
| CPU-bound (per-request CPU > 200ms) | 10-30 | Each request monopolizes a vCPU slice |
| Mixed (CPU + I/O) | 50-80 | Balance between cost and latency |
| I/O-bound (API proxy, DB queries) | 80-200 | Async I/O allows high concurrency |
| Static content / health checks | 200-500 | Minimal per-request cost |

### MinSize selection

| Traffic pattern | Recommended MinSize | Rationale |
|---|---|---|
| Static 24/7 (consistent traffic) | Steady-state instance count | Avoid cold starts; no idle scaling |
| Dynamic (business-hours peaks) | 0 or 1 | 0 = scale-to-zero overnight; 1 = always-on |
| Intermittent (event-driven, bursty) | 0 | Scale-to-zero between events |
| Production, low-latency requirement | 1 | Avoid cold starts (< 5s first request) |

### MaxSize selection

| Traffic variability | Recommended MaxSize | Rationale |
|---|---|---|
| Predictable traffic | Peak instance count + 50% | Handle minor spikes |
| Variable traffic | Peak instance count * 2 | Handle moderate spikes |
| Highly variable / viral | Peak instance count * 3 | Handle major spikes |
| Cost-sensitive | Peak instance count + 1 | Cap cost; accept some 5xx during spikes |

## Cost-per-request benchmark

| Platform | Cost per 1M requests | Notes |
|---|---|---|
| App Runner (1 vCPU/2 GB, concurrency 80) | ~$0.15-0.25 | Includes compute only |
| Lambda + API Gateway | ~$0.20-0.35 | API Gateway surcharge |
| ECS/Fargate (1 vCPU/2 GB) | ~$0.10-0.20 | Lower overhead, more ops |
| EC2 (t3.medium, always-on) | ~$0.05-0.10 | Best for sustained traffic |

App Runner is cost-competitive for moderate traffic with managed
infrastructure. For sustained high traffic (> $2,000/month), ECS/Fargate
or EC2 may be cheaper (lower per-compute overhead, no managed-service
premium).

## Cost calculation worksheet

```
MONTHLY COMPUTE COST:
  provisioned_cost = MinSize * hourly_rate * 730
  ondemand_cost = avg_instances_above_min * avg_request_duration_sec * request_count * per_second_rate
  compute_total = provisioned_cost + ondemand_cost

EGRESS COST (if VPC connector):
  nat_cost = monthly_egress_GB * 0.045 + NAT_hourly * 730
  (subtract VPC endpoint traffic if configured)

OBSERVABILITY COST:
  log_cost = monthly_log_GB * 0.50

DATA TRANSFER OUT:
  dto_cost = monthly_response_GB * 0.09

TOTAL = compute_total + nat_cost + log_cost + dto_cost
```

## CLI quick-reference

| Goal | Command |
|---|---|
| Describe service | `aws apprunner describe-service --service-arn <arn>` |
| Describe auto-scaling config | `aws apprunner describe-auto-scaling-configuration --auto-scaling-configuration-arn <arn>` |
| List services | `aws apprunner list-services` |
| List auto-scaling configs | `aws apprunner list-auto-scaling-configurations` |
| Create auto-scaling config | `aws apprunner create-auto-scaling-configuration --auto-scaling-configuration-name <name> --min-size <n> --max-size <n> --concurrency <n>` |
| Update service config | `aws apprunner update-service --service-arn <arn> --auto-scaling-configuration-arn <new-arn>` |
| Pause service | `aws apprunner pause-service --service-arn <arn>` |
| Resume service | `aws apprunner resume-service --service-arn <arn>` |
| Delete auto-scaling config | `aws apprunner delete-auto-scaling-configuration --auto-scaling-configuration-arn <arn>` |
| CloudWatch metrics | `aws cloudwatch get-metric-statistics --namespace AWS/AppRunner --metric-name <metric> --dimensions Name=ServiceId,Value=<id> ...` |
| Cost Explorer | `aws ce get-cost-and-usage --filter '{"Dimensions":{"Key":"Service","Values":["App Runner"]}}' ...` |
