---
name: cloudwatch-application-signals-deployer
description: 'Enables CloudWatch Application Signals on ECS / EKS / EC2 / Lambda with auto-instrumentation (Java, Python), service discovery from CloudMap and Kubernetes services, SLO creation (latency, availability, custom), service map visualization, ServiceLevelObjective (period, target, alarm), and RED metrics extraction (Rate, Errors, Duration) from X-Ray traces. Emits a READY_TO_DEPLOY checklist with every prerequisite verified. Use when enabling Application Signals on a service, instrumenting a Java/Python app for auto-derived RED metrics, creating ServiceLevelObjective (period, target, alarm), wiring service discovery, or wiring a CloudWatch SLO alarm. Triggers: application signals, service map, service-level objective, SLO, X-Ray RED metrics, auto-instrument application signals, CloudMap service discovery, EKS service map, ECS application signals, OpenTelemetry AWS distro, Java Python application signals.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with application-signals, xray, cloudwatch, ecs, eks, ec2, lambda, iam, and ssm access. Works with Terraform aws_cloudwatch_service_level_objective, CloudFormation AWS::ApplicationSignals::ServiceLevelObjective, and the CloudWatch agent / AWS Distro for OpenTelemetry.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, cloudwatch, application-signals, observability, deploy, slo, service-map, instrumentation
  dependencies: aws-orchestrator
  keywords: aws, cloudwatch, application-signals, observability, cloudops, deploy, provisioning, slo, service-level-objective, service-map, xray, red-metrics, opentelemetry, instrumentation, ecs, eks, ec2, lambda
  when_to_use: Invoke when the user wants to enable CloudWatch Application Signals on a workload (ECS, EKS, EC2, or Lambda), instrument a Java or Python application for auto-derived RED metrics, create a CloudWatch ServiceLevelObjective (period, target, alarm), wire service discovery from CloudMap or Kubernetes services, or visualize the application service map. Do NOT invoke for plain CloudWatch dashboards/alarms (use cloudwatch-dashboard-deployer / cloudwatch-alarm-operator), for X-Ray-only tracing without Application Signals, or for CloudWatch Container Insights (separate feature).
---

# CloudWatch Application Signals Deployer

An AWS CloudOps agent skill that enables CloudWatch Application Signals on
container and Lambda workloads with the correct production defaults —
auto-instrumentation, service discovery, SLOs, service map, and RED
metrics. Emits a READY_TO_DEPLOY checklist verifying every prerequisite.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the provisioning order matters | "Reasoning framework" |
| What to verify before enabling | "Prerequisites" |
| The ordered provisioning steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| RED metrics, SLO, service discovery | "Deployment procedure" Steps 3-8 |
| Workload-specific defaults | "Workload matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/deployment-cli-commands.md` |
| SLO, service discovery, instrumentation guide | `references/slo-and-service-discovery-guide.md` |

## STRICT output contract

When this skill is invoked with an Application Signals enablement request
(service name, platform, language, or a partial existing configuration),
the agent MUST respond with the READY_TO_DEPLOY checklist defined in
"Output format" using the literal all-caps labels `SERVICE:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines
of the response.

### Required output structure

1. `SERVICE: <service-name>` — the workload being instrumented.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING`.
3. `CHECKLIST:` followed by indented lines with status markers
   (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented `aws ...` commands.

### FORBIDDEN output patterns

- **No prose preamble before `SERVICE:`** — the first non-empty line MUST
  be `SERVICE:`.
- **No markdown variants of labels** — write `VERDICT:`, not `**VERDICT:**`,
  `### Verdict`, `Verdict =`, or `` `VERDICT` ``.
- **No swapping verdict tokens** — exactly `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`. Not "ready", "missing", "BLOCKED", "OK".
- **No omitting `VERIFICATION_COMMANDS:`** — include even when
  PREREQUISITES_MISSING; the operator needs commands to verify gaps.
- **No extra sections after `VERIFICATION_COMMANDS:`** — the checklist
  block is the entire response. Put deeper explanation in `references/`.
- **No status marker drift** — use only `[✓]`, `[✗]`, `[OPTIONAL]`,
  `[INPUT NEEDED]`. Do not invent `[?]`, `[!]`, `[WARN]`, or emoji.

### Perfect example (copy the shape exactly)

```text
SERVICE: payments-api
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Platform — ECS Fargate
  [✓]      Runtime — Java 17 (Corretto)
  [✓]      Auto-instrumentation — AWS Distro for OpenTelemetry (ADOT) Java agent injected
  [✓]      Application Signals role — arn:aws:iam::123456789012:role/payments-api-task (CloudWatchApplicationSignalsReportServiceAccess, AWSXrayWriteOnlyAccess)
  [✓]      Service name override — AWS_SERVICE_NAME=payments-api, AWS_APPLICATION_ENVIRONMENT=prod
  [✓]      X-Ray tracing — enabled, sampling rule configured (5% default)
  [✓]      Service discovery — Kubernetes service + CloudMap namespace backed
  [✓]      RED metrics — CloudWatch receives Rate / Errors / Duration (1-min aggregates)
  [✓]      Service map — node visible within 5-10 min of first trace
  [✓]      SLO — 99.9% availability over 28 days rolling, burn-rate alarms on minutes/hours
  [OPTIONAL] Custom SLO — p95 latency < 250ms over 5-min windows
  [OPTIONAL] Client-side telemetry — RUM web app integration
VERIFICATION_COMMANDS:
  aws application-signals list-services --region us-east-1
  aws application-signals list-service-level-objectives --region us-east-1
  aws xray get-sampling-rules --region us-east-1
  aws ecs describe-tasks --cluster payments --tasks <task-id> --query 'tasks[0].taskDefinitionArn'
  aws cloudwatch describe-alarms --alarm-name-prefix CWApplicationSignals
```

## Reasoning framework (why the provisioning order matters)

Enabling Application Signals has **dependency and ordering constraints**
that make the procedure non-trivial. Skipping or misordering causes silent
gaps — the service map stays empty, SLOs never trigger, or RED metrics
fail to land:

1. **IAM role FIRST** — Application Signals is opt-in via the
   `CloudWatchApplicationSignalsReportServiceAccess` and
   `AWSXrayWriteOnlyAccess` managed policies. The workload's task
   execution / instance / function role MUST attach these BEFORE the
   agent runs. Missing policies produce silent `AccessDenied` in the
   CloudWatch agent log; the service map never populates.
2. **Auto-instrumentation language-specific** — Java and Python are the
   GA paths. The ADOT Java/Python auto-instrumentation agent MUST be
   injected (ECS: sidecar or init container; EKS: mutating webhook or
   init container; EC2: CloudWatch agent config; Lambda: layer).
3. **Service name + environment labels** — `AWS_SERVICE_NAME` and
   `AWS_APPLICATION_ENVIRONMENT` env vars disambiguate services in the
   service map. Without them, multiple services collapse into a single
   node ("SpringBootApp", "app") and SLOs cannot bind to a workload.
4. **Service discovery AFTER traces flow** — Application Signals
   auto-discovers services from the traces themselves (named via
   `AWS_SERVICE_NAME`) plus optional CloudMap / Kubernetes service
   enrichment. Discovery runs after the first traces arrive — typically
   5-10 minutes lag.
5. **RED metrics are derived** — Rate, Errors, and Duration come from
   X-Ray traces, not from CloudWatch custom metrics. If X-Ray sampling
   is misconfigured (no rule, 0% sampling, missing write IAM), RED
   metrics are blank even when Application Signals is "enabled".
6. **SLOs reference a service + metric** — the
   `AWS::ApplicationSignals::ServiceLevelObjective` CloudFormation
   resource binds to a discovered service key and an
   `AWS/ApplicationSignals` metric (Latency, Availability, or custom).
   Creating the SLO before the service exists produces a CloudFormation
   rollback.
7. **Alarm period must match SLO interval** — burn-rate alarms must
   reference the SLO's evaluation period (e.g., 1-min alarm for a
   5-min SLO window). Mismatched periods produce either flapping or
   permanently non-firing alarms.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **AWS account opt-in for Application Signals** | Service must be enabled in the account/Region. | `aws application-signals list-services` (no error = enabled) |
| **Workload IAM role** | Task/instance/function role must have `CloudWatchApplicationSignalsReportServiceAccess` + `AWSXrayWriteOnlyAccess`. | `aws iam list-attached-role-policies --role-name <role>` |
| **X-Ray tracing enabled in the account** | X-Ray is the trace source feeding RED metrics. | `aws xray get-encryption-config` (200 = enabled) |
| **X-Ray sampling rule** | At least the default sampling rule must exist; 0% sampling blanks RED metrics. | `aws xray get-sampling-rules` (Default rule ≥ 5%) |
| **Runtime supported** | GA: Java (JDK 8+), Python (3.8+). Other runtimes: manual OTel SDK. | Check container base image / Lambda runtime |
| **Service name uniqueness** | `AWS_SERVICE_NAME` must be unique within the environment; collisions collapse service-map nodes. | `aws application-signals list-services` |
| **CloudMap namespace** (if used) | Optional enrichment source for service discovery. | `aws servicediscovery list-namespaces` |
| **CloudWatch Logs role** | Application Signals emits audit logs to a service-linked role. | `aws iam get-role --role-name AWSServiceRoleForCloudWatchApplicationSignals` |
| **IAM permissions for caller** | Caller needs `application-signals:*`, `xray:*`, `cloudwatch:PutMetricData`, `iam:AttachRolePolicy`. | `aws sts get-caller-identity` |

## Deployment procedure (apply in order)

### Step 1: Opt in the account for Application Signals

Application Signals is Region-scoped and account-opt-in. In most Regions
the first call to `ListServices` opts the account in automatically. To
opt in explicitly:

```bash
aws application-signals list-services --region us-east-1
```

A successful empty-list response (no error) confirms opt-in. If you
receive `AccessDeniedException` for `application-signals:ListServices`,
your caller IAM lacks the service prefix — add the inline policy.

The AWS service-linked role `AWSServiceRoleForCloudWatchApplicationSignals`
is created automatically on first opt-in. Do NOT delete it.

### Step 2: Attach IAM policies to the workload role

Attach two managed policies to the workload's execution role (ECS task,
EKS pod, EC2 instance profile, Lambda execution role):

```bash
aws iam attach-role-policy \
  --role-name payments-api-task \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchApplicationSignalsReportServiceAccess

aws iam attach-role-policy \
  --role-name payments-api-task \
  --policy-arn arn:aws:iam::aws:policy/AWSXrayWriteOnlyAccess
```

`CloudWatchApplicationSignalsReportServiceAccess` grants the agent
permission to publish the derived RED metrics and service map topology
to the `AWS/ApplicationSignals` and `AWS/ApplicationSignalsClient` metric
namespaces. `AWSXrayWriteOnlyAccess` grants X-Ray segment writes.

**Without both policies the agent runs but produces zero output — a
silent failure.**

### Step 3: Inject the OpenTelemetry auto-instrumentation agent

Language-specific injection. The AWS Distro for OpenTelemetry (ADOT) is
the supported path.

Language-specific injection worked examples (Java ECS Fargate sidecar task definition, Java EKS mutating webhook, Python auto-instrumentation) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when writing the task definition or injection annotations; Lambda layers and EC2 paths live in `references/deployment-cli-commands.md` Steps 3c-3d.

For Lambda, attach the `aws-otel-lambda-python` (or `aws-otel-lambda-java`)
layer. Full sequences in `references/deployment-cli-commands.md`.

### Step 4: Set service name + environment labels

Application Signals keys every node in the service map by
`AWS_SERVICE_NAME` + `AWS_APPLICATION_ENVIRONMENT`. These MUST be set
as environment variables on the application container, not the sidecar:

```bash
AWS_SERVICE_NAME=payments-api
AWS_APPLICATION_ENVIRONMENT=prod
```

Additionally, the OTel resource attributes `service.name` and
`service.namespace` are propagated into X-Ray trace annotations and
drive the service map topology.

**NEVER omit `AWS_SERVICE_NAME`.** Without it, the service appears as
the container image name or the OTel default (`unknown_service`), making
SLOs impossible to bind.

### Step 5: Configure X-Ray sampling

RED metrics are derived from X-Ray traces. A 0% sampling rule or a
missing Default rule blanks all three (Rate, Errors, Duration):

```bash
# Default sampling rule: capture 5% of requests, 1 per second
# (raise for low-traffic services)
aws xray create-sampling-rule --cli-input-json file://sampling-rule.json
```

```json
{
  "SamplingRule": {
    "RuleName": "Default",
    "ResourceARN": "*",
    "Priority": 10000,
    "FixedRate": 0.05,
    "ReservoirSize": 1,
    "ServiceName": "*",
    "ServiceType": "*",
    "Host": "*",
    "HTTPMethod": "*",
    "URLPath": "*",
    "Version": 1,
    "Attributes": {}
  }
}
```

For a service under load tests or initial verification, temporarily
raise `FixedRate` to `1.0` (100% sampling) for the first 30 minutes,
then drop to 5%.

### Step 6: Wire service discovery (CloudMap / Kubernetes)

Application Signals auto-discovers services from the traces themselves.
Two optional enrichment sources:

**CloudMap** — add the service to a CloudMap namespace and annotate the
service in the trace with the CloudMap service ID. Application Signals
joins on `service.name`:

```bash
aws servicediscovery create-service \
  --name payments-api \
  --namespace-id ns-abc123 \
  --dns-config '{"NamespaceId":"ns-abc123","DnsRecords":[{"Type":"A","TTL":10}]}'
```

**Kubernetes service** — the OTel Kubernetes attributes processor
automatically tags traces with `k8s.pod.name`, `k8s.namespace.name`,
and `k8s.service.name`. Application Signals surfaces these in the service
detail page.

Discovery is **eventually consistent** — expect 5-10 minutes after the
first trace arrives before the service appears in
`aws application-signals list-services`.

### Step 7: Verify RED metrics flow to CloudWatch

After 5-10 minutes of trace flow, verify the three derived metrics land
in the `AWS/ApplicationSignals` namespace:

```bash
aws cloudwatch list-metrics --namespace AWS/ApplicationSignals \
  --metric-name Latency --dimensions Name=ServiceName,Value=payments-api

aws cloudwatch list-metrics --namespace AWS/ApplicationSignals \
  --metric-name ErrorRate --dimensions Name=ServiceName,Value=payments-api

aws cloudwatch list-metrics --namespace AWS/ApplicationSignals \
  --metric-name CallCount --dimensions Name=ServiceName,Value=payments-api
```

Application Signals publishes (per `ServiceName`, `Environment`):

- **Rate** — `CallCount` (requests/min) and `RequestCount` (cumulative).
- **Errors** — `ErrorRate` (fraction of fault/error responses) and
  `FaultCount`.
- **Duration** — `Latency` (p50, p90, p95, p99 — statistic selector on
  the metric query).

If the metrics do not appear within 15 minutes, the cause is almost
always missing IAM policies on the workload role (Step 2).

### Step 8: Create a ServiceLevelObjective (SLO)

The `AWS::ApplicationSignals::ServiceLevelObjective` CloudFormation
resource (or `aws application-signals create-service-level-objective`
CLI) defines the SLO. Three required components:

- **Metric** — `Latency` (with target percentile) or `Availability`
  (success ratio), or a custom metric query.
- **Period / Interval** — evaluation window (e.g., rolling 28 days, or
  5-minute burn-rate window).
- **Target** — attainment goal (e.g., 99.9% available).
- **Alarm** — burn-rate CloudWatch alarm tied to the SLO interval.

Availability and Latency SLO worked examples (CloudFormation YAML) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when authoring the ServiceLevelObjective resource; CLI and Terraform equivalents live in `references/slo-and-service-discovery-guide.md`.

Full CLI / Terraform equivalents in
`references/slo-and-service-discovery-guide.md`.

### Step 9: Configure the SLO burn-rate alarm

The SLO `Goal.Interval.BurnRates` array emits derived
`BurnRate` metrics that drive multi-window burn-rate alarms. Attach a
CloudWatch alarm:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name payments-api-slo-burn-fast \
  --namespace AWS/ApplicationSignals \
  --metric-name BurnRate \
  --dimensions Name=SLOId,Value=<slo-id> Name=RollupInterval,Value=MINUTE \
  --period 60 --evaluation-periods 1 \
  --threshold 14.4 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:oncall
```

**Burn-rate thresholds (industry-standard multi-window):**

| Window | Threshold | Meaning |
|---|---|---|
| 5m | 14.4× | Fast burn: 2% of budget in 5m → page |
| 1h | 6× | Medium burn: 10% of budget in 1h → page |
| 6h | 3× | Slow burn: 10% of budget in 6h → ticket |
| 1d | 1× | Day-long burn: budget drain → ticket |

The SLO resource auto-creates the burn-rate metrics when
`BurnRates` is populated; you only create the alarm.

### Step 10: Tag, verify, and watch service map

```bash
aws application-signals list-service-level-objectives --region us-east-1
aws application-signals list-services --region us-east-1
aws cloudwatch describe-alarms --alarm-name-prefix payments-api-slo
aws xray get-trace-summaries --start-time $(date -u +%s --date='10 min ago') \
  --end-time $(date -u +%s) --filter-expression 'service.id = "payments-api"'
```

Open the CloudWatch console → Application Signals → Service map to
confirm the `payments-api` node shows up with edges to downstream
dependencies (databases, downstream services, external HTTP).

## Edge-case handling

Edge-case catalog (service missing from map, blank RED metrics, collapsed nodes, ServiceNotFound rollback, Lambda layer arch, EKS webhook, custom-metric SLO) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when post-deployment verification fails.

## Workload matrix

| Workload | Platform | Runtime | Instrumentation | Service discovery | Notes |
|---|---|---|---|---|---|
| Container API | ECS Fargate | Java 17 | ADOT Java agent + collector sidecar | Service env var + CloudMap | Default recommendation |
| Container API | EKS | Java 17 | ADOT Operator + java inject webhook | K8s attributes processor | Recommended for K8s-native shops |
| Container worker | ECS EC2 | Python 3.11 | opentelemetry-instrument auto | Service env var | Use 100% sampling for low-traffic queues |
| Serverless API | Lambda | Java 21 | `aws-otel-lambda-java` layer | Service env var | Cold-start traces show in service map |
| Serverless API | Lambda | Python 3.12 | `aws-otel-lambda-python` layer | Service env var | Layer ARN must match runtime arch |
| Long-running service | EC2 | Java 17 | CloudWatch agent + ADOT Java agent | Service env var | Install CW agent with SSM |
| Multi-region | Any | Any | Per-Region instrumentation, per-Region SLO | Per-Region service map | Service map does NOT merge across Regions |

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when choosing between new and legacy mechanisms (Lambda/ECS GA, CloudFormation SLO, cross-account service map, RUM correlation).

## NEVER (top 5 — full list in references)

- NEVER skip the `CloudWatchApplicationSignalsReportServiceAccess` IAM
  policy on the workload role. The agent starts without error but
  produces zero metrics and no service-map nodes — silent failure.
- NEVER omit `AWS_SERVICE_NAME` and `AWS_APPLICATION_ENVIRONMENT` env
  vars. Without them services collapse into one node, SLOs cannot bind,
  and burn-rate alarms never fire.
- NEVER set X-Ray sampling to 0% on a service with an SLO. RED metrics
  derive from traces; 0% sampling blanks Rate, Errors, and Duration.
- NEVER create an SLO before its target service has appeared in
  `aws application-signals list-services`. CloudFormation rolls back;
  the SLO never binds to a service key.
- NEVER mismatch the SLO interval and the burn-rate alarm period. A
  5-minute burn-rate alarm against a 1-day-only SLO interval produces
  either flapping or permanently non-firing alarms.

## Expert heuristic — enabling signals and choosing SLOs

Expert heuristic — enabling signals and choosing SLOs (IAM-first ordering, language defaults, SLO count, burn-rate math, sampling vs accuracy, service-name discipline, cross-Region) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when planning instrumentation and SLO strategy.

## Pre-flight safety checks (run before any enablement CLI)

Pre-flight safety checks (opt-in, workload IAM policies, X-Ray sampling default, runtime support, service-name uniqueness, CloudMap namespace) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before running any enablement CLI.

## Output format — MANDATORY literal labels

When invoked with an Application Signals enablement request, your
ENTIRE response MUST be the checklist block below. The labels are
**case-sensitive all-caps keywords** — write them EXACTLY as shown. Do
NOT write a preamble. Start with `SERVICE:` and stop after the
`VERIFICATION_COMMANDS:` block.

```text
SERVICE: <service-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Platform — <ECS Fargate | ECS EC2 | EKS | EC2 | Lambda>
  [✓]      Runtime — <Java <ver> | Python <ver> | Node | Go | .NET>
  [✓]      Auto-instrumentation — <ADOT Java agent | ADOT Python inject | manual OTel SDK | Lambda layer>
  [✓]      Application Signals role — <role-arn> (CloudWatchApplicationSignalsReportServiceAccess, AWSXrayWriteOnlyAccess)
  [✓]      Service name override — AWS_SERVICE_NAME=<name>, AWS_APPLICATION_ENVIRONMENT=<env>
  [✓]      X-Ray tracing — enabled, sampling rule <FixedRate>
  [✓]      Service discovery — <Kubernetes service | CloudMap namespace | trace-derived>
  [✓]      RED metrics — CloudWatch receives Rate / Errors / Duration
  [✓]      Service map — node visible within 5-10 min of first trace
  [✓]      SLO — <availability | latency | custom> <target> over <interval>
  [✓]      Burn-rate alarm — fast (5m, 14.4x), medium (1h, 6x), slow (6h, 3x)
  [OPTIONAL] Custom SLO — <custom metric query>
  [OPTIONAL] Client-side telemetry — RUM web app integration
VERIFICATION_COMMANDS:
  aws application-signals list-services --region <region>
  aws application-signals list-service-level-objectives --region <region>
  aws xray get-sampling-rules --region <region>
  aws iam list-attached-role-policies --role-name <role>
  aws cloudwatch describe-alarms --alarm-name-prefix CWApplicationSignals
  aws cloudwatch list-metrics --namespace AWS/ApplicationSignals --dimensions Name=ServiceName,Value=<name>
```

**Status marker semantics:**
- `[✓]` — applied and verified.
- `[✗]` — NOT applied or misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required for the workload type.
- `[INPUT NEEDED]` — prerequisite value missing; operator must provide.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is
missing (workload role ARN, X-Ray sampling rule, supported runtime,
opt-in), the verdict is `PREREQUISITES_MISSING` with each gap listed.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — Step 3 language-specific injection examples and Step 8 Availability/Latency SLO CloudFormation examples moved from SKILL.md
- [references/advanced-patterns.md](references/advanced-patterns.md) — edge-case catalog, the enabling/SLO expert heuristic, and Recent AWS features (2024-2026) moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight safety checks moved from SKILL.md

## Domain

AWS CloudOps / Application-Centric Observability Provisioning.

## AWS documentation

- **Application Signals User Guide** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals.html
- **Enabling Application Signals** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Enable.html
- **Application Signals IAM** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-IAM.html
- **Creating SLOs** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-SLO.html
- **ServiceLevelObjective CloudFormation** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-applicationsignals-servicelevelobjective.html
- **AWS X-Ray Sampling Rules** — https://docs.aws.amazon.com/xray/latest/devguide/xray-console-sampling.html
- **AWS Distro for OpenTelemetry** — https://aws-observability.github.io/aws-otel-introduction/
- **CloudWatch RUM** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html
- **Application Signals CLI** — https://docs.aws.amazon.com/cli/latest/reference/application-signals/

## References

- `references/deployment-cli-commands.md` — full copy-pasteable CLI
  command sequence for all 10 enablement steps, including Terraform
  equivalents and per-platform (ECS / EKS / EC2 / Lambda) snippets.

- `references/slo-and-service-discovery-guide.md` — deep reference on
  SLO internals (period-based vs request-based SLI), service discovery
  internals, burn-rate math, full NEVER list, and edge-case handling.

