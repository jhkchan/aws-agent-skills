# Advanced Patterns (load on demand) — DevOps Guru Troubleshooter

Expert heuristics (change correlation, resource-category diagnostic paths), 2024-2026 analysis additions, and Recent AWS features moved verbatim from SKILL.md.
The decision tree, STRICT output contract, primary worked example, and NEVER list remain in SKILL.md.

---

## Latest analysis additions (2024-2026) (moved from SKILL.md)

- **Server-side encryption analysis (2024-2025):** DevOps Guru flags
  resources without SSE-KMS (S3, DynamoDB, EBS, KMS-backed resources).
  These surface as PROACTIVE / CONFIGURATION insights with the
  recommendation to enable SSE-KMS with a customer CMK.
- **Cost analysis (2024-2025):** DevOps Guru detects cost anomalies on
  specific resources (not account-wide — that is Cost Anomaly
  Detection). Useful for catching a single misconfigured resource
  (e.g., a runaway Lambda, an oversized RDS instance).

---

## Expert heuristic: change-correlation is the leading root-cause signal (moved from SKILL.md)

Across production incidents surfaced by DevOps Guru, the root cause is
a **change** (deployment, config update, infrastructure modification)
in ~70% of cases. The remaining ~30% are capacity exhaustion, dependency
failures, or AWS-side events.

**Change-correlation procedure:**

```text
1. Identify the InsightTimeRange.StartTime (T0).
2. Query CloudTrail and deployment history for the window [T0-2h, T0].
3. Rank events by proximity to T0 (closest first).
4. For each candidate change:
   a. Does the changed resource match the insight's resource?
   b. Does the change plausibly cause the observed anomaly?
   c. Is there a rollback path?
5. If a strong candidate exists, the root cause is the change.
   Implement rollback or fix-forward.
6. If no candidate exists, investigate capacity, dependencies, or
   AWS-side events (Health Dashboard).
```

**Why 2 hours:** most deployment-induced anomalies surface within
minutes, but cache warmup, connection pool exhaustion, and gradual
capacity drain can delay symptom onset by 1-2 hours. Widening beyond
2 hours produces too many candidates to triage effectively.

---

## Expert heuristic: RESOURCE_CATEGORY determines the diagnostic path (moved from SKILL.md)

DevOps Guru insights on different resource categories require different
diagnostic probes. A baseline model applies the same "check CloudWatch"
probe to everything; a skilled operator uses the resource-specific path.

| Resource | First probe | Second probe | Common root cause |
|---|---|---|---|
| ALB / Target Group | `HTTPCode_Target_5XX_Count`, `TargetResponseTime` | Target health (`describe-target-health`) | Backend app error, health check misconfig, slow downstream |
| RDS | `CPUUtilization`, `DatabaseConnections`, `FreeableMemory` | Performance Insights top SQL | Slow query, connection pool leak, missing index |
| Lambda | `Duration`, `Errors`, `Throttles` | Lambda Insights / application logs | Cold start spike, concurrency limit, dependency timeout |
| ECS | `CPUUtilization`, `MemoryUtilization`, task stops | `describe-tasks --stopped-reason` | OOM kill, health check fail, host drift |
| DynamoDB | `ThrottledRequests`, `ConsumedCapacityUnits` | Per-partition metrics (via support) | Hot partition, insufficient WCU/RCU, GSI cascade |
| ASG | `GroupInServiceInstances`, scaling activities | `describe-scaling-activities` | Launch failure (AMI, capacity, IAM, subnet) |
| CodeBuild (2024-2025) | Build duration, failure rate | Build logs | Test flakiness, dependency download slow, environment drift |

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **DevOps Guru for RDS (2024-2025 GA):** dedicated analysis for RDS
  databases — detects Performance Insights anomalies (slow queries,
  wait events, connection saturation) and surfaces them as DevOps Guru
  insights. Provisioning tip: enable Performance Insights on production
  RDS instances for full coverage.
- **DevOps Guru for CodeBuild (2024-2025):** detects anomalous build
  durations and failure rates on CodeBuild projects. Useful for
  catching flaky tests and environment drift early.
- **DevOps Guru for Lambda (2024-2025 enhanced):** deeper Lambda
  analysis including cold-start anomaly detection, provisioned
  concurrency utilization, and downstream dependency latency. Pairs
  with CloudWatch Lambda Insights.
- **Server-side encryption analysis (2024-2025):** DevOps Guru now
  flags resources without SSE-KMS (S3, DynamoDB, EBS) as
  PROACTIVE/CONFIGURATION insights. Recommendation: enable SSE-KMS
  with a customer CMK. Useful for compliance-driven hardening.
- **Cost analysis category (2024-2025):** DevOps Guru detects
  per-resource cost anomalies (not account-wide — that remains Cost
  Anomaly Detection). Catches single-resource misconfigurations
  (runaway Lambda, oversized RDS, orphaned NAT Gateway).
- **Event-based insights (2024-2025):** DevOps Guru now correlates
  insights with CloudTrail events and deployment events natively
  (previously required manual correlation). The `list-events` API
  surfaces the correlated events directly.
