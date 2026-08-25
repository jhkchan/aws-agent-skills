---
name: xray-tracing-deployer
description: 'Deploys AWS X-Ray distributed tracing with production-grade configuration: X-Ray daemon deployment (EC2 systemd, ECS sidecar, EKS DaemonSet, Lambda built-in), SDK instrumentation (Java, Python, Node.js, Go, .NET) with annotations and metadata, sampling rules (default reservoir + rate vs custom rules with URL / method / service-name predicates), service map generation, trace query and retrieval, groups and insights, CloudWatch ServiceLens integration, IAM permissions (PutTraceSegments, GetSamplingRules), and latest features (Lambda Powertools tracing, OpenTelemetry / ADOT Collector support, W3C trace context). Emits a READY_TO_DEPLOY checklist with every configuration item verified. Use when enabling X-Ray on a new application, adding tracing to ECS / EKS / Lambda, validating a sampling configuration, or generating daemon deployment CLI and IaC templates. Triggers: X-Ray, distributed tracing, X-Ray daemon, sampling rules, service map, X-Ray SDK, OpenTelemetry, ADOT, Lambda Powertools, CloudWatch ServiceLens.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with xray, ec2, ecs, eks, lambda, iam, logs, and servicediscovery access. Works with Terraform aws_xray_* resources, CloudFormation AWS::XRay::* resources, and the AWS Distro for OpenTelemetry (ADOT) Collector.'
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
  tags: aws, xray, distributed-tracing, cloudops, deploy, observability, sampling-rules, opentelemetry
  dependencies: aws-orchestrator
  keywords: aws, xray, x-ray, distributed-tracing, cloudops, deploy, provisioning, observability, daemon, sampling-rules, service-map, opentelemetry, adot, servicelens
  when_to_use: Invoke when the user wants to enable X-Ray distributed tracing on a new application, add the X-Ray daemon to ECS / EKS / EC2 / Lambda, create or validate custom sampling rules, instrument an SDK (Java, Python, Node.js, Go, .NET), set up CloudWatch ServiceLens, or migrate from X-Ray SDK to OpenTelemetry / ADOT. Do NOT invoke for CloudWatch Logs metrics alone (use cloudwatch-alarm-auditor), for application performance monitoring without tracing (use cloudwatch-application-signals-deployer), or for pure log aggregation.
---

# X-Ray Tracing Deployer

An AWS CloudOps agent skill that deploys AWS X-Ray distributed tracing
with correct production defaults. Emits a READY_TO_DEPLOY checklist
verifying every configuration item.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the deployment order matters | "Reasoning framework" |
| What to verify before deploying | "Prerequisites" |
| The ordered deployment steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Platform-specific defaults | "Platform matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep daemon + sampling CLI | `references/daemon-and-sampling-guide.md` |
| SDK instrumentation, OTel, full NEVER | `references/sdk-instrumentation-guide.md` |

## STRICT output contract

When this skill is invoked with an X-Ray tracing deployment request, the
agent MUST respond with the READY_TO_DEPLOY checklist defined in "Output
format" using the literal all-caps labels `SERVICE:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines.

### Required output structure

1. `SERVICE: <application-name>` — the application being traced.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING`.
3. `CHECKLIST:` followed by indented lines with status markers
   (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented `aws xray ...` commands.

### FORBIDDEN output patterns

- **No prose preamble before `SERVICE:`** — first non-empty line MUST be
  `SERVICE:`.
- **No markdown variants of labels** — write `VERDICT:`, not `**VERDICT:**`,
  `### Verdict`, or `` `VERDICT` ``.
- **No swapping verdict tokens** — exactly `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`.
- **No omitting `VERIFICATION_COMMANDS:`** — include even when
  PREREQUISITES_MISSING.
- **No extra sections after `VERIFICATION_COMMANDS:`** — the checklist
  block is the entire response.
- **No status marker drift** — use only `[✓]`, `[✗]`, `[OPTIONAL]`,
  `[INPUT NEEDED]`.

### Perfect example (copy the shape exactly)

```text
SERVICE: payments-api-prod
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Platform — ECS Fargate, cluster payments-prod
  [✓]      Daemon — aws-xray-daemon:4.1 sidecar (UDP 2000), task definition payments-xray-sidecar:3
  [✓]      SDK instrumentation — Python 3.11, aws-xray-sdk 2.13, middleware on Flask app
  [✓]      Sampling rule — default (reservoir 1/s, rate 5%), custom rule payments-checkout (reservoir 10/s, rate 100% on POST /checkout)
  [✓]      IAM execution role — payments-task-exec has xray:PutTraceSegments + xray:PutTelemetryRecords
  [✓]      IAM task role — payments-task has xray:PutTraceSegments + xray:PutTelemetryRecords + xray:GetSamplingRules + xray:GetSamplingTargets
  [✓]      Annotations — region, environment, customer_id (indexable)
  [✓]      Metadata — request_body_size, response_status (not indexable, for correlation)
  [✓]      Service map — generated from traces, 4 segments (ALB, payments-api, DynamoDB, SQS)
  [✓]      CloudWatch ServiceLens — integrated, service map visible in CloudWatch console
  [OPTIONAL] X-Ray group — payments-checkout-group (filter expression annotation.region = "us-east-1")
VERIFICATION_COMMANDS:
  aws xray get-sampling-rules
  aws xray get-sampling-targets
  aws ecs describe-task-definition --task-definition payments-xray-sidecar:3
  aws ecs describe-services --cluster payments-prod --services payments-api-prod
  aws xray get-service-graph --start-time 2026-08-10T00:00:00Z --end-time 2026-08-10T23:59:59Z
```

## Reasoning framework (why the deployment order matters)

1. **IAM FIRST** — without `xray:PutTraceSegments` and
   `xray:PutTelemetryRecords` on the application's runtime role, the SDK
   generates traces but the daemon cannot upload them. Traces are silently
   dropped. This is the #1 X-Ray deployment failure.
2. **Daemon (or OTel Collector) SECOND** — the X-Ray SDK sends segment
   documents to `127.0.0.1:2000` (UDP). If no daemon is listening, the
   SDK silently drops the segment. No error, no log, no trace.
3. **SDK instrumentation THIRD** — the SDK captures incoming requests
   (HTTP framework middleware) and downstream calls (SDK patches). Without
   SDK patches for downstream AWS calls, only the entry segment is
   captured — no downstream dependencies appear in the service map.
4. **Sampling rules FOURTH** — sampling rules control WHICH requests are
   traced. Without a custom rule, the default rule (reservoir 1/s, rate
   5%) is applied. For high-traffic endpoints, this is too low; for
   critical endpoints (checkout, payment), set a custom rule with
   100% sampling.
5. **Groups + insights FIFTH** — groups are saved trace filters for
   recurring queries. Insights auto-detect anomalies (latency spikes,
   error rate increases). Apply AFTER traces are flowing.
6. **ServiceLens SIXTH** — ServiceLens integrates X-Ray traces with
   CloudWatch metrics and logs. It is enabled at the account level, no
   per-service config needed.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **IAM role with X-Ray permissions** | App runtime role needs `xray:PutTraceSegments`, `xray:PutTelemetryRecords`, `xray:GetSamplingRules`, `xray:GetSamplingTargets`. Without these, traces are silently dropped. | `aws iam list-attached-role-policies --role-name <role>` + `aws iam list-role-policies --role-name <role>` |
| **X-Ray daemon / OTel Collector** | Must be running and listening on UDP 2000 (X-Ray daemon) or gRPC 4317 (OTel Collector). Without it, the SDK drops segments. | `aws ecs describe-task-definition` (ECS) / `kubectl get daemonset` (EKS) / `systemctl status xray` (EC2) |
| **SDK installed + middleware enabled** | The SDK must be a dependency AND the middleware/patcher must be active. Installing the package without enabling the middleware captures nothing. | Check `requirements.txt` / `package.json` / `pom.xml` for `aws-xray-sdk` or `opentelemetry-*` |
| **AWS region with X-Ray endpoint** | X-Ray is regional. The daemon resolves the regional endpoint. Ensure the region supports X-Ray. | `aws xray get-sampling-rules --region <region>` |
| **VPC endpoints (if private)** | If the app runs in a private VPC without NAT Gateway, an X-Ray VPC interface endpoint is needed. | `aws ec2 describe-vpc-endpoints --filter Name=service-name,Values=com.amazonaws.<region>.xray` |
| **ECS task definition (if ECS)** | The daemon must be a sidecar container in the SAME task definition as the app. | `aws ecs describe-task-definition --task-definition <family>` |
| **EKS DaemonSet (if EKS)** | The daemon runs as a DaemonSet (one pod per node). The app pod's traffic to the daemon is via the node IP. | `kubectl get daemonset -n kube-system aws-xray-daemon` |
| **Lambda layer / Powertools (if Lambda)** | Lambda does NOT need the daemon — the runtime injects it. Use the X-Ray Lambda layer or Powertools for tracing. | `aws lambda get-function-configuration --function-name <name> --query 'Layers'` |
| **KMS key (if encryption)** | X-Ray encrypts at rest with AWS-owned KMS by default. CMK needs grant on the X-Ray service role. | `aws xray get-encryption-config` |

## Deployment procedure (apply in order)

### Step 1: IAM permissions (application runtime role)

The application's runtime role (ECS task role, EC2 instance profile,
Lambda execution role, EKS pod IRSA role) needs X-Ray permissions.

```bash
aws iam attach-role-policy \
  --role-name <app-role> \
  --policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess
```

`AWSXRayDaemonWriteAccess` grants:
- `xray:PutTraceSegments`
- `xray:PutTelemetryRecords`
- `xray:GetSamplingRules`
- `xray:GetSamplingTargets`
- `xray:GetEncryptionConfig`

It does NOT grant read access to traces (`BatchGetTraces`,
`GetServiceGraph`). Those are for operators / CI roles, not the app.

For custom inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords",
      "xray:GetSamplingRules",
      "xray:GetSamplingTargets",
      "xray:GetEncryptionConfig"
    ],
    "Resource": "*"
  }]
}
```

**NEVER forget `xray:GetSamplingRules` and `xray:GetSamplingTargets`.**
Without these, the SDK cannot fetch sampling rules and falls back to
local default sampling (1/s, fixed). The central sampling rules you
configure in the console are NEVER applied.

### Step 2: X-Ray daemon deployment (by platform)

#### EC2 (systemd)

EC2 systemd install (daemon download, unit file, enable): [Daemon and sampling guide](references/daemon-and-sampling-guide.md).
Load on demand for EC2 deployments.

#### ECS Fargate (sidecar container)

ECS Fargate sidecar container definition (JSON) and localhost UDP 2000 rationale: [Daemon and sampling guide](references/daemon-and-sampling-guide.md).
Load on demand for ECS Fargate deployments.

#### ECS EC2 (daemon as a service, NOT sidecar)

On ECS EC2, you can run the daemon as a separate ECS service (one daemon
task per instance) or a sidecar. The daemon-as-a-service pattern saves
memory but requires the app to send traces to the HOST IP on port 2000
(NOT localhost). Set the `AWS_XRAY_DAEMON_ADDRESS` env var to
`<host-ip>:2000`.

#### EKS / Kubernetes (DaemonSet)

EKS DaemonSet manifest and node-IP downward-API injection: [Daemon and sampling guide](references/daemon-and-sampling-guide.md).
Load on demand for EKS deployments.

#### Lambda (built-in — no daemon needed)

Lambda enable-tracing and Powertools layer CLI: [Daemon and sampling guide](references/daemon-and-sampling-guide.md).
Load on demand for Lambda deployments.

### Step 3: SDK instrumentation (by language)

Full code examples in `references/sdk-instrumentation-guide.md`.

| Language | Package | Middleware |
|---|---|---|
| **Python** | `aws-xray-sdk` | `XRayMiddleware(app)` for Flask/Django, `@xray_recorder.capture()` for functions |
| **Node.js** | `aws-xray-sdk-core` | `aws-xray-sdk.express.openSegment(<name>)` for Express, `AWSXRay.captureAWS()` for AWS SDK |
| **Java** | `aws-xray-recorder-sdk-core` | `@XRayEnabled` on JAX-RS resources, `AWSXRay.beginSegment()` for custom |
| **Go** | `github.com/aws/aws-xray-sdk-go` | `xray.Handler(nil, http.HandlerFunc(handler))` for HTTP |
| **.NET** | `AWSXRayRecorder` | `app.UseXRay("<name>")` for ASP.NET Core |

**Critical SDK patterns:**

1. **Patch AWS SDK** — without `AWSXRay.captureAWS(AWS)` (Node.js) or
   `aws_xray_sdk.core.patch_all()` (Python), downstream AWS calls do NOT
   generate subsegments. The service map shows only the entry point.
2. **Patch HTTP clients** — patch `requests` (Python), `http`/`https`
   (Node.js) to trace outbound HTTP calls to non-AWS APIs.
3. **Annotations vs metadata** — annotations are indexable (use for
   `customer_id`, `region`, `environment`). Metadata is NOT indexable
   (use for request/response bodies, debug info).

### Step 4: Sampling rules

```bash
# Default rule (always present, applied to all services without a custom match)
aws xray create-sampling-rule --cli-input-json '{
  "SamplingRule": {
    "RuleName": "Default",
    "RuleARN": "",
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
}'

# Custom rule — 100% sampling for checkout endpoint
aws xray create-sampling-rule --cli-input-json '{
  "SamplingRule": {
    "RuleName": "payments-checkout-100",
    "ResourceARN": "*",
    "Priority": 100,
    "FixedRate": 1.0,
    "ReservoirSize": 10,
    "ServiceName": "payments-api",
    "ServiceType": "*",
    "Host": "*",
    "HTTPMethod": "POST",
    "URLPath": "/checkout/*",
    "Version": 1,
    "Attributes": {}
  }
}'
```

**Sampling rule semantics:**
- **Priority** — lower number = higher priority. Rules are evaluated in
  priority order. The FIRST match wins.
- **ReservoirSize** — guaranteed traces per second BEFORE the rate
  applies. The reservoir ensures at least N traces/s even at low traffic.
- **FixedRate** — fraction of requests ABOVE the reservoir to sample.
  `1.0` = 100%, `0.05` = 5%.
- **Matching** — a rule matches if ALL of `ServiceName`, `ServiceType`,
  `Host`, `HTTPMethod`, `URLPath`, and `Attributes` match. `*` is
  wildcard.

**NEVER set FixedRate=1.0 on the Default rule for a high-traffic service.**
This generates massive trace volume, X-Ray costs scale with trace count,
and the service map becomes noisy. Use a custom rule scoped to specific
endpoints.

### Step 5: Annotations and metadata

```python
from aws_xray_sdk.core import xray_recorder

# Annotation — indexable, use for filtering in X-Ray console
xray_recorder.put_annotation("customer_id", "cust-12345")
xray_recorder.put_annotation("region", "us-east-1")

# Metadata — NOT indexable, for debug context
xray_recorder.put_metadata("request_body_size", 1024)
xray_recorder.put_metadata("feature_flags", {"new_checkout": True})
```

Annotations are indexed and searchable in the X-Ray console. Metadata
is visible on individual traces but NOT searchable. Use annotations for
fields you will filter on; use metadata for everything else.

### Step 6: Groups and insights

```bash
# Group — saved filter expression
aws xray create-group \
  --group-name "payments-checkout-group" \
  --filter-expression 'annotation.region = "us-east-1" AND service("payments-api") { fault = true }'

# Insights — auto-detect anomalies (enabled by default, no config needed)
aws xray get-insight --insight-id <id>
```

Groups are saved filter expressions for recurring queries. Insights
auto-detect latency spikes, error rate increases, and anomalous behavior.
Insights are enabled by default — no config needed.

### Step 7: CloudWatch ServiceLens

ServiceLens integrates X-Ray traces with CloudWatch metrics and logs. It
is enabled at the account level — no per-service config needed. To
verify:

```bash
aws cloudwatch describe-alarms-for-metric \
  --namespace AWS/XRay \
  --metric-name FaultRate
```

The ServiceLens service map is visible in the CloudWatch console under
"ServiceLens" > "Service Map".

### Step 8: Verification

```bash
aws xray get-sampling-rules
aws xray get-sampling-targets
aws xray get-service-graph --start-time <ISO> --end-time <ISO>
aws xray get-trace-summaries --start-time <ISO> --end-time <ISO>
aws xray get-groups
aws xray get-insight-summaries --start-time <ISO> --end-time <ISO>
```

## Latest X-Ray features (2024-2026)

2024-2026 feature delta (Powertools v2, ADOT Collector, attribute-based sampling, Insights anomaly detection, cross-account ServiceLens, CMK, daemon 4.x maintenance mode, W3C): [Advanced patterns](references/advanced-patterns.md).
Load on demand when choosing components.

## Platform matrix

| Platform | Daemon | SDK address | IAM role | Notes |
|---|---|---|---|---|
| **EC2** | systemd service | `127.0.0.1:2000` | Instance profile | Daemon runs as a background process |
| **ECS Fargate** | Sidecar container | `127.0.0.1:2000` | Task role | Same task definition (awsvpc shared network) |
| **ECS EC2** | Sidecar or daemon-service | `127.0.0.1:2000` or `<host-ip>:2000` | Task role | Daemon-service saves memory; sidecar is simpler |
| **EKS** | DaemonSet | `<node-ip>:2000` (downward API) | Pod IRSA role | DaemonSet = one daemon per node |
| **Lambda** | Built-in (no daemon) | N/A | Execution role | Enable `TracingConfig Mode=Active` |
| **App Runner** | N/A (managed) | N/A | Instance role | Enable observability config with `Vendor=AWSXRay` |
| **Elastic Beanstalk** | Instance or sidecar | `127.0.0.1:2000` | Instance profile | EB config has an X-Ray option |

## NEVER (top 5 — full list of 14 in references)

- NEVER deploy the X-Ray SDK without `xray:GetSamplingRules` and
  `xray:GetSamplingTargets` on the application's runtime role. The SDK
  fetches central sampling rules from the X-Ray API. Without these
  permissions, the SDK falls back to local default (1/s, fixed) and the
  rules you configure in the console are NEVER applied. #1 silent-failure.
- NEVER run the X-Ray daemon / OTel Collector without
  `xray:PutTraceSegments` and `xray:PutTelemetryRecords`. The SDK
  generates segments and sends them to the daemon, but the daemon
  uploads them. Without upload permissions, traces are silently dropped.
- NEVER set `FixedRate=1.0` on the Default sampling rule for high-traffic
  services. This generates massive trace volume. X-Ray charges per trace
  ingested. Use a custom rule scoped to specific endpoints.
- NEVER forget to patch the AWS SDK (`AWSXRay.captureAWS()` /
  `aws_xray_sdk.core.patch_all()`). Without the patch, downstream AWS
  calls (DynamoDB, S3, SQS) do NOT generate subsegments. The service map
  shows only the entry point — no dependencies.
- NEVER deploy the daemon as a separate ECS service on Fargate and point
  the app to it via DNS. Fargate tasks cannot reach each other on
  localhost. The daemon MUST be a sidecar in the same task definition.

## Expert heuristic — choosing X-Ray SDK vs ADOT, sampling, and annotations

SDK-vs-ADOT choice, reservoir/rate tuning, annotation discipline, trace-context propagation, and cost control: [Advanced patterns](references/advanced-patterns.md).
Load on demand when making design decisions.

## Pre-flight safety checks (run before any deployment CLI)

- **Confirm IAM role has all 5 X-Ray actions** (PutTraceSegments,
  PutTelemetryRecords, GetSamplingRules, GetSamplingTargets,
  GetEncryptionConfig). Use `AWSXRayDaemonWriteAccess` managed policy.
- **Confirm daemon / OTel Collector is running** and listening on UDP
  2000 (X-Ray) or gRPC 4317 (OTel).
- **Confirm SDK package is installed** and the middleware/patcher is
  active in the code.
- **Confirm AWS SDK is patched** for downstream call tracing.
- **Confirm trace context propagation** across all service boundaries.
- **Confirm sampling rules** (check the Default rule and any custom
  rules).
- **Confirm X-Ray encryption config** (AWS-owned key vs CMK).
- **For existing services, capture current sampling config for rollback.**

Full CLI sequences for all checks in `references/daemon-and-sampling-guide.md`.

## Output format — MANDATORY literal labels

When invoked with a tracing deployment request, your ENTIRE response MUST
be the checklist block below. The labels are **case-sensitive all-caps
keywords**. Do NOT write a preamble. Start with `SERVICE:` and stop after
the `VERIFICATION_COMMANDS:` block.

```text
SERVICE: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Platform — <ec2|ecs|eks|lambda|app-runner>, <cluster/function/detail>
  [✓]      Daemon — <daemon-image:version> <deployment-mode> (UDP 2000)
  [✓]      SDK instrumentation — <language> <version>, <package> <version>, <middleware>
  [✓]      Sampling rule — default (reservoir <n>/s, rate <p>%), custom rule <name> (reservoir <n>/s, rate <p>% on <match>)
  [✓]      IAM role — <role-name> has xray:PutTraceSegments + PutTelemetryRecords + GetSamplingRules + GetSamplingTargets
  [✓]      Annotations — <indexable fields>
  [✓]      Metadata — <debug fields>
  [✓]      Service map — generated from traces, <segment-count> segments
  [✓]      CloudWatch ServiceLens — integrated
  [OPTIONAL] X-Ray group — <group-name> (filter expression <expr>)
VERIFICATION_COMMANDS:
  aws xray get-sampling-rules
  aws xray get-sampling-targets
  aws xray get-service-graph --start-time <ISO> --end-time <ISO>
  aws ecs describe-task-definition --task-definition <family>
```

**Status marker semantics:**
- `[✓]` — applied and verified.
- `[✗]` — NOT applied or misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required.
- `[INPUT NEEDED]` — prerequisite value missing; operator must provide.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is missing
(IAM permissions, daemon / Collector not running, SDK not instrumented,
sampling rules not configured), the verdict is `PREREQUISITES_MISSING`.

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — 2024-2026 feature delta, SDK-vs-ADOT heuristics, edge-case catalog
- [Daemon and sampling guide](references/daemon-and-sampling-guide.md) — per-platform daemon deployment blocks (EC2, ECS Fargate, EKS, Lambda) plus the full daemon/sampling CLI sequence
- [SDK instrumentation guide](references/sdk-instrumentation-guide.md) — language-by-language instrumentation and AWS SDK patching

## Domain

AWS CloudOps / X-Ray Distributed Tracing Observability Provisioning.

## Edge-case handling

Edge-case catalog (cross-account, SQS/EventBridge propagation, ECS EC2 host-IP, EKS limits, Lambda cold start, OTel migration, high-cardinality annotations, CMK grants): [Advanced patterns](references/advanced-patterns.md).
Load on demand when deployment hits a corner case.

## AWS documentation

- **AWS X-Ray Developer Guide** — https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html
- **X-Ray Daemon** — https://docs.aws.amazon.com/xray/latest/devguide/xray-daemon.html
- **X-Ray SDK** — https://docs.aws.amazon.com/xray/latest/devguide/xray-sdk.html
- **X-Ray Sampling Rules** — https://docs.aws.amazon.com/xray/latest/devguide/xray-console-sampling.html
- **X-Ray Service Map** — https://docs.aws.amazon.com/xray/latest/devguide/xray-services.html
- **X-Ray Groups and Insights** — https://docs.aws.amazon.com/xray/latest/devguide/xray-insights.html
- **CloudWatch ServiceLens** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ServiceLens.html
- **AWS Distro for OpenTelemetry (ADOT)** — https://aws-otel.github.io/
- **Lambda Powertools Tracing** — https://docs.powertools.aws.dev/lambda/python/latest/core/tracer/
- **X-Ray CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/xray/

## References

- `references/daemon-and-sampling-guide.md` — full copy-pasteable CLI
  command sequence for daemon deployment (EC2, ECS, EKS, Lambda),
  sampling rule creation (default + custom), IAM role setup, group
  creation, and Terraform / CloudFormation equivalents.

- `references/sdk-instrumentation-guide.md` — deep reference on SDK
  instrumentation (Python, Node.js, Java, Go, .NET), AWS SDK patching,
  annotation vs metadata, trace context propagation, OpenTelemetry / ADOT
  migration, full NEVER list, edge-case handling, and pre-flight safety
  CLI.
