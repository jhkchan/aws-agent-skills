# Insight Catalog and Decision Tree — DevOps Guru Troubleshooter

Deep reference covering the full insight pattern catalog, resource-
specific diagnostic paths, and the decision tree for implement vs
suppress vs escalate. Loaded on-demand when the skill needs the full
catalog rather than the summary in the SKILL.md.

## Proactive insight catalog

### Performance insights

| Pattern (from Name + anomalies) | Likely root cause | First probe | Second probe |
|---|---|---|---|
| "Increased latency on ALB" | Code regression, downstream slow-down, capacity exhaustion | CloudWatch `TargetResponseTime` | RDS `DatabaseConnections`, application logs, deployment history |
| "High CPU on RDS" | Slow query, connection pool leak, missing index | RDS Performance Insights top SQL | CloudWatch `CPUUtilization`, `DatabaseConnections` |
| "Resource saturation" (EC2/ECS) | Hot shard, runaway process, capacity exhaustion | CloudWatch `CPUUtilization`, `MemoryUtilization` | Application profiler, container insights |
| "Increased Lambda duration" | Dependency timeout, cold start spike, code regression | CloudWatch Lambda `Duration`, `Errors` | Lambda Insights, application logs |
| "Slow CodeBuild builds" (2024-2025) | Test flakiness, dependency download slow, env drift | CodeBuild build duration, failure rate | Build logs, build environment config |

### Availability insights

| Pattern | Likely root cause | First probe | Second probe |
|---|---|---|---|
| "Increased error rate on ALB" | Code regression, downstream failure, capacity exhaustion | CloudWatch `HTTPCode_Target_5XX_Count` | Deployment history, application logs |
| "Lambda throttling" | Concurrency limit reached, burst traffic | CloudWatch `Throttles`, concurrent executions | Reserved concurrency config, traffic pattern |
| "DynamoDB throttling" | Hot partition, insufficient WCU, GSI cascade | CloudWatch `ThrottledRequests` | `ConsumedCapacityUnits` per partition |
| "ASG launch failures" | Capacity (instance type/AZ), AMI missing, IAM/subnet issue | ASG activity history | CloudTrail `RunInstances`, EC2 `DescribeInstances` |
| "ECS task stops" | OOM, health check fail, host failure | ECS `TaskStopCode`, `StoppedReason` | Container logs, host EC2 health |

### Configuration insights

| Pattern (from Name + category) | Likely root cause | Action |
|---|---|---|
| "S3 bucket lacks SSE-KMS" (2024-2025) | Bucket created without SSE; compliance gap | Enable SSE-KMS with customer CMK via `put-bucket-encryption` |
| "DynamoDB table without PITR" | PITR not enabled; recovery risk | Enable PITR via `update-continuous-backups` |
| "Security group open to 0.0.0.0/0" | Misconfiguration or legacy rule | Restrict to known CIDR; verify via CloudTrail `AuthorizeSecurityGroupIngress` |
| "IAM role with overly broad permissions" | Wildcard actions/resources in policy | Scope the policy; use IAM Access Analyzer for finding verification |
| "RDS instance without Multi-AZ" | Single-AZ deployment; availability risk | Enable Multi-AZ via `modify-db-instance` |

### Cost insights (2024-2025)

| Pattern | Likely root cause | Action |
|---|---|---|
| "Anomalous EC2 spend" | Orphaned instances, oversized instance type, idle resources | EC2 right-sizing, `describe-instances` for orphaned, Compute Optimizer recommendations |
| "Unexpected Lambda cost" | Runaway invocations, high-duration regression, misconfigured retry | CloudWatch `Invocations`, `Duration`; application logs for trigger |
| "DynamoDB cost spike" | GSI over-provisioning, on-demand burst from scan/query | `ConsumedCapacityUnits` per GSI; query patterns |

## Reactive insight catalog

| Pattern | What it means | First probe | Second probe |
|---|---|---|---|
| "ALB 5xx error rate" | Backend target returning 5xx | `HTTPCode_Target_5XX_Count`, target health | Application error logs, deployment history |
| "RDS failover initiated" | Multi-AZ failover (primary failure, AZ outage) | AWS Health Dashboard, RDS events | CloudTrail `FailoverDBCluster` |
| "ASG unable to launch" | Capacity, AMI, IAM, or subnet issue | ASG `describe-scaling-activities` | CloudTrail `RunInstances` |
| "ECS service degraded" | Task stops, host drain, deployment regression | ECS `describe-services`, `describe-tasks` | Container insights, deployment history |
| "API Gateway 5xx" | Integration timeout, backend unavailable, Lambda error | API Gateway logs, `5XXErrors` | Integration (Lambda/backend) health |

## Resource-category to first-probe mapping

DevOps Guru insights on different resource categories require different
diagnostic probes. Using the resource-specific probe dramatically
reduces time-to-root-cause.

| Resource | First probe | Second probe | Common root cause |
|---|---|---|---|
| ALB / Target Group | `HTTPCode_Target_5XX_Count`, `TargetResponseTime` | `describe-target-health` | Backend app error, health check misconfig, slow downstream |
| RDS | `CPUUtilization`, `DatabaseConnections`, `FreeableMemory` | Performance Insights top SQL | Slow query, connection pool leak, missing index |
| Lambda | `Duration`, `Errors`, `Throttles` | Lambda Insights, application logs | Cold start, concurrency limit, dependency timeout |
| ECS | `CPUUtilization`, `MemoryUtilization`, task stops | `describe-tasks --stopped-reason` | OOM kill, health check fail, host drift |
| DynamoDB | `ThrottledRequests`, `ConsumedCapacityUnits` | Per-partition metrics (via support) | Hot partition, insufficient WCU, GSI cascade |
| ASG | `GroupInServiceInstances`, scaling activities | `describe-scaling-activities` | Launch failure (AMI, capacity, IAM, subnet) |
| CloudFormation | Stack events, drift | `describe-stack-events` | Stack drift, manual change, parameter misuse |
| CodeBuild (2024-2025) | Build duration, failure rate | Build logs | Test flakiness, dependency download, env drift |
| S3 (CONFIGURATION) | `get-bucket-encryption`, `get-bucket-versioning` | CloudTrail `PutBucketEncryption` | SSE-KMS missing, versioning disabled |
| API Gateway | `4XXErrors`, `5XXErrors`, `Count` | Execution logs | Integration failure, throttling, auth misconfig |

## Severity-driven response matrix

| Severity | Proactive meaning | Reactive meaning | Suggested response SLA |
|---|---|---|---|
| `HIGH` | ML confidence high; incident impending | User-facing degradation; system unavailable | Immediate (within minutes) |
| `MEDIUM` | Notable deviation; may escalate | Marginal degradation; partial impact | Same business day |
| `LOW` | Minor deviation; informational | Transient; resolved or self-healed | Next business day |

**Exception:** a `LOW` severity insight on a payment-processing or
authentication resource may matter more than a `HIGH` on a dev sandbox.
Always read the `Name` and `ResourceCollection` before applying the
severity-based SLA.

## False positive suppression patterns

| Pattern | When it is a false positive | Suppression approach |
|---|---|---|
| Traffic spike during known marketing event | Pre-announced event; traffic expected | Tag resource with `DevOpsGuru:SuppressedReason`; document in runbook |
| Test environment noise | Non-production; insights informational | Set `ResourceCollection` to exclude the test account or tags |
| Scheduled maintenance (deployments, backups) | Maintenance window known and approved | Use CloudWatch Events to annotate the window; DevOps Guru does not auto-suppress |
| Resource right-sizing after scale-down | Post-scale-down metrics look anomalous vs pre-scale-down baseline | Wait 14 days for baseline to retrain; low urgency — let self-resolve |
| New service launch | No baseline yet for the new service | Wait 14 days for baseline; suppress LOW insights during ramp |
| Test traffic to production | Synthetic monitoring, canary tests | Tag test resources; exclude from DevOps Guru coverage |

**Critical:** console "dismiss" is ephemeral — the ML model will re-flag
the same pattern when it retrains (typically within 14 days). Use
resource tags (`DevOpsGuru:SuppressedReason`) or `ResourceCollection`
filters for durable suppression.

## Decision tree: implement / suppress / escalate

```text
Is the insight a confirmed true positive (anomaly matches real issue)?
├── NO → Is the anomaly benign (known event, test, maintenance)?
│   ├── YES → Suppress with documented rationale; do NOT use console
│   │         "dismiss" alone (use tag or ResourceCollection filter)
│   └── NO → Insufficient evidence to classify
│            → NEED_MORE_INFO verdict
└── YES → Is the root cause within the operator's scope?
    ├── YES → Does the DevOps Guru recommendation address the root cause?
    │   ├── YES → Implement the recommendation; verify via CloudWatch
    │   └── NO → Implement the root-cause-specific fix; document why the
    │            recommendation was not followed
    └── NO → Is it an AWS-side issue?
        ├── YES → ROOT_CAUSE_FOUND with AWS Health Dashboard evidence;
        │         no application action needed
        └── NO → ESCALATE to the owning team with the evidence block
```

## Recommendations evaluation framework

| Recommendation category | When to apply directly | When to investigate further |
|---|---|---|
| `AGGREGATE_OF_METRICS` (generic) | Insight is informational | Always — generic recommendations rarely fix the root cause |
| `AGGREGATE_OF_EVENT_LOGS` | Log pattern matches known error | When pattern is novel — route to application team |
| `DEPLOYMENT_FAILURE` | Deployment correlates with insight start time | When multiple deployments occurred — identify the specific one |
| `LOG_PATTERN` | Pattern points to a known error | When pattern is novel — capture and route |
| Specific action ("increase ASG max to 20") | Capacity-driven root cause | When code change is the root cause — scaling masks |
| CONFIGURATION ("enable SSE-KMS") | Configuration gap confirmed | Verify the KMS key exists and is enabled before applying |

## Cross-reference: AWS-side events

When the change-correlation window [T0-2h, T0] returns no candidate
changes, investigate AWS-side events:

```bash
# AWS Health Dashboard (requires Business+ Support)
aws health describe-events \
  --region us-east-1 \
  --query 'events[?startTime>=`"2026-08-10T03:00:00Z"` && startTime<=`"2026-08-10T04:00:00Z"`].[eventArn,service,statusCode,eventTypeCategory,startTime]' \
  --output table

# AWS service health (public, no Support tier required)
# https://health.aws.amazon.com/health/status
```

AWS-side events that commonly surface as DevOps Guru Reactive insights:
- AZ power/cooling events (RDS failover, EC2 host reboot)
- Service degradation (API throttling, increased latency)
- Network device failover (VPC peering, Transit Gateway)
