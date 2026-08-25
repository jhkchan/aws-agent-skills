---
name: devops-guru-troubleshooter
description: 'Diagnoses Amazon DevOps Guru insights across Proactive and Reactive categories. Covers insight types (Proactive=anomalous behavior, Reactive=operational issue), severity (High/Medium/Low), resource coverage (CloudFormation stacks, Auto Scaling groups, ALB, RDS, DynamoDB, Lambda, ECS, CodeBuild), analysis categories (performance, availability, cost, configuration), recommendation implementation, false positive suppression. Latest: DevOps Guru for RDS/CodeBuild/ Lambda, server-side encryption analysis, event-based insights. Emits ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE. Use when a DevOps Guru insight is OPEN or investigating performance/availability anomalies flagged by the service.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline diagnosis works on supplied describe-insight / list-recommendations JSON. Live-account diagnosis uses aws devops-guru describe-insight, list-anomalies-for-insight, list-recommendations, describe-resource-health, and aws logs filter-log-events for correlated CloudWatch Logs (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: devops-guru, management, troubleshoot, insight, proactive, reactive, anomaly, recommendation
  dependencies: aws-orchestrator
  keywords: DevOps Guru, insight, Proactive, Reactive, anomalous behavior, operational issue, severity, High, Medium, Low, CloudFormation, Auto Scaling group, ALB, RDS, DynamoDB, Lambda, ECS, CodeBuild, performance, availability, cost, configuration, recommendation, false positive, server-side encryption
  when_to_use: Invoke when the user is investigating an Amazon DevOps Guru insight (OPEN or recently resolved), needs to map an insight to a root cause, wants to implement or validate a DevOps Guru recommendation, needs to suppress false positives, or is onboarding DevOps Guru to a new resource set (CloudFormation stacks, Auto Scaling groups, RDS, Lambda, ECS). Do NOT invoke for CloudWatch alarm triage (use cloudwatch-alarm-operator), or for general performance analysis without a DevOps Guru insight context.
---

# DevOps Guru Troubleshooter

An AWS CloudOps agent skill that diagnoses Amazon DevOps Guru insights.
The skill walks the operator from an insight ID through severity
classification, resource/analysis categorization, anomaly correlation,
recommendation evaluation, and root-cause determination. It emits a
ROOT_CAUSE_FOUND verdict with evidence from describe-insight,
list-anomalies-for-insight, and list-recommendations.

## What this skill does

Diagnoses DevOps Guru insights: classifies Proactive (anomalous
behavior detected by ML) vs Reactive (operational issue already
occurring), maps the insight to a resource category (CloudFormation
stack, Auto Scaling group, ALB, RDS, DynamoDB, Lambda, ECS, CodeBuild),
identifies the analysis category (performance, availability, cost,
configuration), evaluates the recommendations, and decides whether to
implement, suppress, or escalate.

## Activation

Trigger phrases: "DevOps Guru insight", "proactive insight", "reactive
insight", "DevOps Guru anomaly", "DevOps Guru recommendation", "DevOps
Guru false positive", "DevOps Guru for RDS", "DevOps Guru for Lambda",
"DevOps Guru CodeBuild", "insight severity high", "DevOps Guru resource
collection", "server-side encryption analysis".

## Invocation contract (hard requirement)

When this skill is invoked with a DevOps Guru insight, the agent MUST
respond with the diagnostic block defined in §"STRICT output contract"
using the literal all-caps labels `INSIGHT:`, `VERDICT:`,
`ROOT_CAUSE:`, `EVIDENCE:`, and `REMEDIATION:`. Do NOT preface the
block with prose, headings, or disclaimers — emit the block as the
first lines of the response. This contract is what assertion-based
evals and downstream diagnostic pipelines rely on.

## Mindset

**One-line takeaway:** DevOps Guru insights are ML-detected signals,
not root causes. The insight tells you WHAT is anomalous (a resource's
behavior deviates from baseline); the operator's job is to walk from
the anomaly to the underlying cause (code change, capacity exhaustion,
misconfiguration, dependency failure). The insight itself rarely names
the root cause directly.

Three misconceptions dominate DevOps Guru troubleshooting:

- **"DevOps Guru tells me the root cause."** It does not. It tells you
  that an anomaly exists (Proactive) or that an operational issue is
  occurring (Reactive). The `Name` and `Description` fields describe
  the SYMPTOM. The `Recommendations` are best-effort heuristics, not
  authoritative diagnoses. Always correlate with CloudWatch metrics,
  CloudTrail events, and deployment history.

- **"Proactive insights are less urgent than Reactive."** Proactive
  insights are ML-detected anomalies that have NOT yet caused an
  operational issue — they are EARLY WARNINGS. A Proactive insight
  with High severity often precedes a Reactive incident by hours or
  days. Treat Proactive=High with the same urgency as Reactive=Medium.

- **"Recommendations are safe to apply automatically."** DevOps Guru
  recommendations include generic guidance ("consider adding a CloudWatch
  alarm", "review the IAM policy") and specific actions ("increase the
  Auto Scaling group maximum"). Always evaluate the recommendation
  against the actual root cause before applying — a recommendation
  generated from a symptom (high CPU) may address the symptom
  (scale out) without addressing the cause (a code regression causing
  CPU spin).

## Quick navigation

- **Step 0** — Capture the insight (insight ID, region, account).
- **Step 1** — Classify insight type (Proactive vs Reactive).
- **Step 2** — Read severity (High / Medium / Low) and urgency.
- **Step 3** — Map resource category (CFN stack, ASG, ALB, RDS, etc.).
- **Step 4** — Identify analysis category (performance, availability,
  cost, configuration).
- **Step 5** — Correlate anomalies (`list-anomalies-for-insight`).
- **Step 6** — Evaluate recommendations (`list-recommendations`).
- **Step 7** — Cross-reference CloudWatch metrics + CloudTrail + deploy
  history.
- **Step 8** — Decide: implement / suppress / escalate.
- **Step 9** — Decide VERDICT (ROOT_CAUSE_FOUND / NEED_MORE_INFO /
  ESCALATE).

## STRICT output contract

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
INSIGHT: <insight ID> in <region> — <InsightType + InsightSeverity + Name>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <InsightCategory> — <one-sentence specific root cause>
EVIDENCE:
  - describe-insight: <quoted InsightType, Severity, Status, Name>
  - list-anomalies-for-insight: <quoted anomaly descriptions and sources>
  - list-recommendations: <quoted recommendation text, with ARN>
  - CloudWatch correlation: <metric + datapoint>
  - CloudTrail correlation: <event source + event name + time>
RESOURCE_CATEGORY: #<N>
ANALYSIS_CATEGORY: <PERFORMANCE | AVAILABILITY | COST | CONFIGURATION>
REMEDIATION:
  1. <exact action — code change, config update, capacity adjustment>
  2. <verification command or CloudWatch metric>
  3. <post-apply monitoring step>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll investigate…" — the
  INSIGHT line is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `ROOT_CAUSE_FOUND`,
  `NEED_MORE_INFO`, or `ESCALATE`.
- NEVER declare `ROOT_CAUSE_FOUND` without quoting evidence from at
  least TWO sources (describe-insight + one of: anomalies,
  recommendations, CloudWatch, CloudTrail). A single-source diagnosis
  is a hypothesis, not a root cause.
- NEVER auto-apply a recommendation without evaluating it against the
  root cause. DevOps Guru recommendations address symptoms; the root
  cause may require a different fix (code change vs capacity scale).
- NEVER suppress an insight as a "false positive" without documenting
  the suppression rationale. Suppression without a paper trail
  guarantees the same insight will recur and be re-investigated from
  scratch.

## Insight type decision tree

| InsightType | What it means | Diagnostic step |
|---|---|---|
| `PROACTIVE` | ML detected anomalous behavior — has NOT yet caused an outage | Step 1A |
| `REACTIVE` | An operational issue IS occurring or recently occurred | Step 1B |

### Step 1A — Proactive insight diagnostic

Proactive insights surface anomalies detected by the ML model against
the trailing 14-day baseline. Common patterns:

| Proactive pattern (read from `Name` + anomalies) | Likely root cause | Probe |
|---|---|---|
| "High latency on ALB" with elevated `TargetResponseTime` | Backend slow-down (DB, downstream API, thread pool exhaustion) | CloudWatch `TargetResponseTime`, RDS `DatabaseConnections` / `CPUUtilization`, application logs |
| "Increased error rate" with elevated `HTTPCode_Target_5XX_Count` | Code regression (latest deployment), downstream dependency failure, capacity exhaustion | Deployment history (CodeDeploy / CodePipeline), CloudTrail `error` events, dependency health |
| "Anomalous API throttle" with elevated `ThrottleCount` | API gateway usage plan exceeded, downstream service throttling, burst traffic | CloudWatch API Gateway `4XXErrors`, application logs |
| "Low RDS connection count" with dropping `DatabaseConnections` | Application connection pool misconfiguration, failover event, security group change | RDS events, CloudTrail `ModifyDBInstance` / `ModifySecurityGroup` |
| "Resource saturation" with high `CPUUtilization` / `Memory` | Capacity exhaustion, hot shard, runaway process | CloudWatch EC2/ECS/Lambda metrics, application profiler |
| "SSE-KMS configuration anomaly" (2024-2025 feature) | KMS key disabled, key policy changed, cross-region replication with missing key | CloudTrail `DisableKey` / `PutKeyPolicy`, KMS `KeyState` |

**Diagnostic walk:**
1. Read `describe-insight` for the full `Name`, `Description`, and
   `InsightTimeRange`.
2. Call `list-anomalies-for-insight` — each anomaly includes the
   `Source` (CloudWatch metric, CloudTrail event) and the
   `Data` (time series showing the deviation from baseline).
3. Correlate the anomaly time range with deployment history. Most
   Proactive=High insights that turn into Reactive incidents are
   caused by a code or config change in the trailing 24-48 hours.

### Step 1B — Reactive insight diagnostic

Reactive insights surface operational issues that ARE occurring (an
ALB returning 5xx, an ASG unable to launch instances, an RDS failover).
These are higher-urgency than Proactive.

| Reactive pattern | Likely root cause | Probe |
|---|---|---|
| "ALB 5xx error rate" | Backend target returning 5xx (application error, timeout, health check failure) | CloudWatch `HTTPCode_Target_5XX_Count`, target group health, application error logs |
| "ASG launch failures" | Capacity (instance type unavailable in AZ), AMI not found, IAM instance profile missing, subnet out of IP | ASG activity history, CloudTrail `RunInstances`, EC2 `DescribeInstances` for failed launches |
| "RDS failover initiated" | Multi-AZ failover (primary failure, AZ outage, storage failure) | RDS event subscription, CloudTrail `FailoverDBCluster` / `RebootDBInstance` |
| "Lambda throttling" | Concurrency limit reached (account-level or reserved) | CloudWatch `Throttles`, Lambda concurrent executions, reserved concurrency config |
| "ECS task stop" | Container exit (OOM, health check fail, deregistration), host failure | ECS `TaskStopCode`, `StoppedReason`, container logs |
| "DynamoDB throttling" | Hot partition, insufficient capacity (PROVISIONED), GSI cascade | CloudWatch `ThrottledRequests`, DynamoDB `ConsumedCapacityUnits` per partition |

**Diagnostic walk:**
1. Read `describe-insight` — the `Name` names the operational issue.
2. Call `list-anomalies-for-insight` for the correlated metrics/events.
3. Cross-reference CloudTrail for the same time range — Reactive
   insights often correlate with a specific API event (deployment,
   config change, infrastructure event).

## Step 2 — Read severity and urgency

| Severity | Proactive meaning | Reactive meaning | Response SLA |
|---|---|---|---|
| `HIGH` | Anomaly strongly suggests an impending incident; the ML confidence is high and the deviation is large | Operational issue is actively degrading user experience or system availability | Immediate — investigate now |
| `MEDIUM` | Anomaly is notable but the deviation is moderate; may self-resolve or escalate | Operational issue is marginal; some users affected but system is functional | Same business day |
| `LOW` | Anomaly is minor; informational only | Operational issue is resolved or was transient | Next business day |

**Precedence rule:** when multiple insights are OPEN simultaneously on
related resources (e.g., an ASG insight + an ALB insight + an RDS
insight), the ALB/RDS insight is usually the root cause and the ASG
insight is the downstream symptom. Investigate the infrastructure-layer
insight first.

## Step 3 — Map resource category

DevOps Guru groups insights by resource. The resource category drives
the diagnostic path.

| Resource category | Typical InsightType | Diagnostic probe |
|---|---|---|
| CloudFormation stack | PROACTIVE / REACTIVE | `aws cloudformation describe-stack-events`, drift detection |
| Auto Scaling group | PROACTIVE / REACTIVE | `aws autoscaling describe-scaling-activities`, ASG activity history |
| ALB / Target Group | PROACTIVE / REACTIVE | CloudWatch ALB metrics, target health |
| RDS (DevOps Guru for RDS, 2024) | PROACTIVE / REACTIVE | RDS Performance Insights, RDS events |
| DynamoDB table | PROACTIVE | CloudWatch `ThrottledRequests`, `ConsumedCapacityUnits` |
| Lambda function | PROACTIVE / REACTIVE | CloudWatch Lambda metrics, Lambda Insights |
| ECS cluster / service | PROACTIVE / REACTIVE | ECS task metrics, container insights |
| CodeBuild project (2024-2025) | PROACTIVE | CodeBuild build history, build duration anomalies |

## Step 4 — Identify analysis category

DevOps Guru classifies each insight into one of four analysis
categories:

| AnalysisCategory | Meaning | Example |
|---|---|---|
| `PERFORMANCE` | Latency, throughput, resource saturation | "Increased ALB latency", "RDS CPU saturation" |
| `AVAILABILITY` | Errors, failures, outages | "ALB 5xx errors", "ASG launch failures", "Lambda throttling" |
| `COST` | Unusual spend pattern (2024-2025 enhancement) | "DynamoDB cost anomaly", "Unexpected EC2 spend" |
| `CONFIGURATION` | Misconfiguration detected (e.g., SSE-KMS missing, IAM drift) | "S3 bucket without SSE-KMS", "Security group open to 0.0.0.0/0" |

**Latest analysis additions (2024-2026):**
- **Server-side encryption analysis (2024-2025):** DevOps Guru flags
  resources without SSE-KMS (S3, DynamoDB, EBS, KMS-backed resources).
  These surface as PROACTIVE / CONFIGURATION insights with the
  recommendation to enable SSE-KMS with a customer CMK.
- **Cost analysis (2024-2025):** DevOps Guru detects cost anomalies on
  specific resources (not account-wide — that is Cost Anomaly
  Detection). Useful for catching a single misconfigured resource
  (e.g., a runaway Lambda, an oversized RDS instance).

## Step 5 — Correlate anomalies (`list-anomalies-for-insight`)

```bash
aws devops-guru list-anomalies-for-insight \
  --region <region> \
  --insight-id <insight-id> \
  --start-time-range '{From=2026-08-01T00:00:00Z,To=2026-08-10T23:59:59Z}' \
  --query 'ProactiveAnomalies[*].{name:Name,source:Source,severity:Severity}' \
  --output table
```

Each anomaly includes:
- `Name` — short description of the anomalous metric or event.
- `Source` — the metric namespace + metric name, or the CloudTrail
  event source.
- `Data` — time series showing the deviation from baseline.
- `Severity` — anomaly-level severity (may differ from insight severity).

**Cross-reference with CloudWatch:**

```bash
# Get the actual metric values for the anomaly time range
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=app/my-alb/1234567890 \
  --start-time 2026-08-09T00:00:00Z \
  --end-time 2026-08-10T00:00:00Z \
  --period 300 --statistics Average \
  --query 'Datapoints[*].[Timestamp,Average]' --output table
```

## Step 6 — Evaluate recommendations (`list-recommendations`)

```bash
aws devops-guru list-recommendations \
  --region <region> \
  --insight-id <insight-id> \
  --query 'Recommendations[*].{name:Name,description:Description,category:Category,link:Link}' \
  --output table
```

Recommendations are categorized:
- `AGGREGATE_OF_EVENT_LOGS` — based on CloudWatch Logs patterns.
- `AGGREGATE_OF_METRICS` — based on CloudWatch metric patterns.
- `DEPLOYMENT_FAILURE` — based on deployment events.
- `LOG_PATTERN` — based on specific log patterns.

**Evaluation framework:**

| Recommendation type | When to apply directly | When to investigate further |
|---|---|---|
| Specific action (e.g., "increase ASG max to 20") | When the anomaly is capacity-driven and the root cause is traffic growth | When a code change is the root cause — scaling masks but does not fix |
| Generic guidance (e.g., "consider adding a CloudWatch alarm") | When the insight is informational | Always — generic recommendations rarely fix the root cause |
| `DEPLOYMENT_FAILURE` | When the deployment correlates with the insight start time | When multiple deployments occurred — identify the specific one |
| `LOG_PATTERN` | When the pattern points to a known error | When the pattern is novel — capture and route to the application team |

## Step 7 — Cross-reference CloudTrail + deployment history

The most common root cause of a DevOps Guru insight is a **change**
(code deployment, config update, infrastructure modification) in the
trailing 24-48 hours.

```bash
# CloudTrail events in the insight time range
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=UpdateStack \
  --start-time 2026-08-09T00:00:00Z \
  --end-time 2026-08-10T00:00:00Z \
  --query 'Events[*].[EventTime,Username,EventName,ResourceName]' \
  --output table

# CodePipeline / CodeDeploy deployment history
aws deploy list-deployments \
  --application-name <app> \
  --create-time-range start=2026-08-09T00:00:00Z,end=2026-08-10T00:00:00Z

aws codepipeline list-pipeline-executions \
  --pipeline-name <pipeline> \
  --query 'pipelineExecutionSummaries[*].[startTime,status,sourceRevisions]' \
  --output table
```

**Change-correlation heuristic:** if a deployment or config change
occurred within 1-2 hours of the `InsightTimeRange.StartTime`, that
change is the leading hypothesis for the root cause.

## Step 8 — Decide: implement / suppress / escalate

| Decision | Criteria | Action |
|---|---|---|
| **Implement recommendation** | Root cause is confirmed and the recommendation addresses the root cause (not just the symptom) | Apply the recommendation; verify via CloudWatch; close insight |
| **Implement different fix** | Root cause is confirmed but the recommendation addresses the symptom | Apply the root-cause-specific fix (code change, config update); document why the recommendation was not followed |
| **Suppress as false positive** | Anomaly is confirmed benign (known maintenance window, expected traffic pattern, test environment noise) | Document the rationale; do NOT use the console "dismiss" alone — use the runbook to add the resource or metric pattern to the suppression list |
| **Escalate** | Root cause is outside the operator's scope (AWS-side issue, cross-team dependency, security incident) | Escalate to the appropriate team with the evidence block; mark the insight for tracking |

**False positive suppression patterns:**

| Pattern | When it is a false positive | Suppression approach |
|---|---|---|
| Traffic spike during known marketing event | Pre-announced event; traffic spike is expected | Tag the resource with `DevOpsGuru:SuppressedReason` and add a CloudWatch alarm annotation |
| Test environment noise | Non-production; insights are informational | Set the DevOps Guru `ResourceCollection` to exclude the test account/tags |
| Scheduled maintenance (deployments, backups) | Maintenance window is known and approved | Use CloudWatch Events to annotate the time range; DevOps Guru does not auto-suppress maintenance windows |
| Resource right-sizing after scale-down | Post-scale-down metrics look "anomalous" against the pre-scale-down baseline | Wait 14 days for the baseline to retrain; if urgency is low, let it self-resolve |

## Step 9 — Decide VERDICT

- **ROOT_CAUSE_FOUND.** The diagnostic walk identified a specific root
  cause (code change, capacity exhaustion, config change, dependency
  failure) supported by evidence from at least two sources. Output
  REMEDIATION with the exact action.
- **NEED_MORE_INFO.** The walk reached a step where evidence is
  insufficient (e.g., CloudWatch metrics unavailable, CloudTrail not
  configured for the relevant API, application logs not shipped to
  CloudWatch). Output the list of missing inputs.
- **ESCALATE.** The root cause is outside the operator's scope: an
  AWS-side incident, a cross-team dependency, a security finding.
  Output the escalation target and the specific request.

## Output format

```text
INSIGHT: <insight ID> in <region> — <InsightType + InsightSeverity + Name>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <InsightCategory> — <specific root cause in one sentence>
EVIDENCE:
  - describe-insight: <InsightType, Severity, Status, Name>
  - list-anomalies-for-insight: <anomaly name + source + deviation>
  - list-recommendations: <recommendation category + text>
  - CloudWatch correlation: <metric + datapoint>
  - CloudTrail correlation: <event + time + user>
RESOURCE_CATEGORY: #<N>
ANALYSIS_CATEGORY: <PERFORMANCE | AVAILABILITY | COST | CONFIGURATION>
REMEDIATION:
  1. <exact action>
  2. <verification command or metric>
  3. <post-apply monitoring>
```

### Worked example — Proactive performance insight (ALB latency)

```text
INSIGHT: x-1234abcd in us-east-1 — PROACTIVE / HIGH / "Increased latency on ALB app/my-alb"
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: PERFORMANCE — Code deployment at 2026-08-09T14:32Z introduced an N+1 query in the /checkout handler, increasing RDS query latency 8x and propagating to ALB TargetResponseTime
EVIDENCE:
  - describe-insight: PROACTIVE, HIGH, OPEN, "Increased latency on ALB app/my-alb", StartTime 2026-08-09T14:35Z
  - list-anomalies-for-insight: Anomaly "TargetResponseTime" source AWS/ApplicationELB, p99 elevated from 200ms baseline to 1800ms starting 14:35Z
  - list-recommendations: AGGREGATE_OF_METRICS — "Investigate the backend service for increased processing time" (generic, addresses symptom not root cause)
  - CloudWatch correlation: AWS/RDS DatabaseConnections elevated from 50 to 380 (connection pool exhaustion); CPUUtilization 92%
  - CloudTrail correlation: CodeDeploy deployment event at 2026-08-09T14:32Z, application=my-app, revision=abc123
RESOURCE_CATEGORY: ALB + RDS (downstream)
ANALYSIS_CATEGORY: PERFORMANCE
REMEDIATION:
  1. Roll back the CodeDeploy deployment to the previous revision
  2. Verify ALB TargetResponseTime returns to baseline (<300ms) within 10 minutes
  3. Fix the N+1 query in the /checkout handler before redeploying; add a CloudWatch alarm on p99 TargetResponseTime > 500ms
```

## NEVER do these things (top)

1. **NEVER treat the DevOps Guru insight `Name` or `Description` as the
   root cause.** They describe the SYMPTOM (anomalous behavior, elevated
   error rate). The root cause is the underlying change, failure, or
   misconfiguration that CAUSED the anomaly. Always correlate with
   CloudTrail and deployment history to identify the proximate change.

2. **NEVER auto-apply a DevOps Guru recommendation without evaluating
   it against the root cause.** Recommendations are heuristic — they
   address the symptom (scale out, add an alarm) not necessarily the
   root cause (a code regression). Scaling out masks the regression
   but the regression persists and will recur under higher load.

3. **NEVER suppress an insight as a "false positive" without
   documenting the suppression rationale in a runbook or ticket.**
   Console "dismiss" is ephemeral; the same insight will recur when
   the ML model retrains. Use resource tags or `ResourceCollection`
   filters for durable suppression, and record the reason.

4. **NEVER declare `ROOT_CAUSE_FOUND` based on a single evidence
   source.** The describe-insight field alone is a symptom description.
   Always correlate with at least one additional source:
   list-anomalies-for-insight (metric deviation),
   list-recommendations (heuristic), CloudWatch (actual metric values),
   or CloudTrail (change events). Single-source diagnosis is a
   hypothesis.

5. **NEVER treat Proactive insights as low-priority by default.**
   Proactive=HIGH insights are ML-detected anomalies with high
   confidence that an incident is impending. They often precede
   Reactive incidents by hours or days. A Proactive=HIGH on a
   production resource deserves the same urgency as a Reactive=MEDIUM.

(Additional: never rely solely on `InsightSeverity` for response
prioritization without reading the `Name` — a LOW severity insight on
a payment-processing resource may matter more than a HIGH on a dev
sandbox. Never skip the deployment history check — the majority of
Proactive insights correlate with a recent code or config change.
Never assume DevOps Guru covers ALL resources — coverage requires
explicit `ResourceCollection` config or CloudFormation stack tagging.)

## Expert heuristic: change-correlation is the leading root-cause signal

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

## Expert heuristic: RESOURCE_CATEGORY determines the diagnostic path

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

## Recent AWS features (2024-2026)

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

## Domain

AWS CloudOps / Management — AIOps Insight Triage & Remediation.

## AWS documentation

- **Amazon DevOps Guru User Guide** — https://docs.aws.amazon.com/devops-guru/latest/userguide/welcome.html
- **DevOps Guru insights** — https://docs.aws.amazon.com/devops-guru/latest/userguide/working-with-insights.html
- **DevOps Guru recommendations** — https://docs.aws.amazon.com/devops-guru/latest/userguide/working-with-recommendations.html
- **DevOps Guru for RDS** — https://docs.aws.amazon.com/devops-guru/latest/userguide/working-with-rds.html
- **DevOps Guru CLI reference** — https://docs.aws.amazon.com/cli/latest/reference/devops-guru/
- **DevOps Guru pricing** — https://aws.amazon.com/devops-guru/pricing/
- **DevOps Guru resource coverage** — https://docs.aws.amazon.com/devops-guru/latest/userguide/working-with-cw.html
