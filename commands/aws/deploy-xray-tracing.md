---
description: Deploy AWS X-Ray distributed tracing with production-grade configuration (X-Ray daemon or ADOT Collector deployment on EC2/ECS/EKS/Lambda, SDK instrumentation for Java/Python/Node.js/Go/.NET, default and custom sampling rules with reservoir and rate, annotations and metadata for trace context, service map generation, X-Ray groups and insights, CloudWatch ServiceLens integration, IAM permissions for PutTraceSegments and GetSamplingRules). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "enable x ray tracing"
  - "deploy x ray daemon"
  - "x ray distributed tracing"
  - "x ray sampling rules"
  - "x ray sdk instrumentation"
  - "x ray service map"
  - "x ray ecs sidecar"
  - "x ray eks daemonset"
  - "x ray ec2 systemd"
  - "x ray lambda layer"
  - "opentelemetry adot collector"
  - "lambda powertools tracing"
  - "cloudwatch servicelens"
  - "x ray annotations"
  - "x ray groups insights"
routes_to: xray-tracing-deployer
---

# /aws:deploy-xray-tracing

Activate the `xray-tracing-deployer` skill and deploy AWS X-Ray
distributed tracing with production-grade configuration.

## What it does

The skill walks an 8-step deployment procedure and emits a
READY_TO_DEPLOY checklist:

1. IAM permissions (PutTraceSegments, PutTelemetryRecords,
   GetSamplingRules, GetSamplingTargets on the app runtime role)
2. X-Ray daemon / ADOT Collector deployment (EC2 systemd, ECS sidecar,
   EKS DaemonSet, Lambda built-in)
3. SDK instrumentation (Java, Python, Node.js, Go, .NET) with AWS SDK
   patching for downstream calls
4. Sampling rules (default reservoir + rate, custom rules with URL /
   method / service-name predicates)
5. Annotations (indexable) and metadata (debug context)
6. Groups and insights (saved filters, anomaly detection)
7. CloudWatch ServiceLens integration
8. Verification commands

## When to use

- You need to enable X-Ray tracing on a new application or service.
- You are adding the X-Ray daemon / ADOT Collector to ECS, EKS, EC2,
  or Lambda.
- You want to create or validate custom sampling rules.
- You need SDK instrumentation for Java, Python, Node.js, Go, or .NET.
- You want to migrate from X-Ray SDK to OpenTelemetry / ADOT.
- You want to check for deployment blockers (missing IAM permissions,
   missing daemon, SDK not patched, oversampled default rule).

## How to invoke

### Slash command

```
/aws:deploy-xray-tracing
```

Then provide: application name, platform (EC2 / ECS / EKS / Lambda /
App Runner), language and framework, SDK choice (X-Ray SDK or
OpenTelemetry / ADOT), daemon address, sampling rule requirements
(default rate, custom rules for critical endpoints), annotations and
metadata fields, and IAM role name.

### Natural language

Any of these routes to the same skill:

- "enable X-Ray tracing on my app"
- "deploy the X-Ray daemon to ECS"
- "create a custom X-Ray sampling rule"
- "instrument Python Flask with X-Ray"
- "set up Lambda Powertools tracing"
- "migrate to ADOT Collector"

### CLI routing

```bash
node cli/bin/cli.js route "deploy x ray tracing"
```

## What the checklist contains

The output is a single block with literal labels:

```
SERVICE: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Platform — <ec2|ecs|eks|lambda>, <detail>
  [✓]      Daemon — <image> <mode> (UDP 2000 | gRPC 4317)
  [✓]      SDK instrumentation — <language>, <package>, <middleware>
  [✓]      Sampling rule — default (<rate>), custom <name> (<rate> on <match>)
  [✓]      IAM role — <role> has all 5 X-Ray actions
  [✓]      Annotations — <indexable fields>
  [✓]      Metadata — <debug fields>
  [✓]      Service map — generated from traces
  [✓]      CloudWatch ServiceLens — integrated
  [OPTIONAL] X-Ray group — <name> (filter expression <expr>)
VERIFICATION_COMMANDS:
  aws xray get-sampling-rules
  aws xray get-service-graph ...
  aws ecs describe-task-definition ...
```

The output checklist feeds into verification pipelines and audit
skills (e.g., a CloudWatch ServiceLens auditor for post-deployment
checks).

## Example

```
You: /aws:deploy-xray-tracing

     Enable distributed tracing on payments-api-prod on ECS Fargate
     cluster payments-prod in us-east-1. Use ADOT Collector sidecar.
     Python 3.11 with opentelemetry Flask + botocore instrumentation.
     Task role payments-task. Custom sampling rule payments-checkout
     at 100% on POST /checkout with reservoir 10/s. Default at 5%.
     Annotations: customer_id, environment=production. Metadata:
     response_status. Enable ServiceLens. Account: 123456789012.

Skill:
  SERVICE: payments-api-prod
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Platform — ECS Fargate, cluster payments-prod
    [✓]      Daemon — ADOT Collector (aws-otel-collector) sidecar, gRPC 4317
    [✓]      SDK instrumentation — Python 3.11, opentelemetry-instrumentation-flask + botocore
    [✓]      AWS SDK patched — BotocoreInstrumentor for DynamoDB, S3, SQS
    [✓]      Sampling rule — Default (5%), custom payments-checkout (100% on POST /checkout)
    [✓]      IAM role — payments-task has all 5 X-Ray actions
    [✓]      Annotations — customer_id, environment=production
    [✓]      Metadata — response_status
    [✓]      Service map — generated from traces
    [✓]      CloudWatch ServiceLens — integrated
  VERIFICATION_COMMANDS:
    aws xray get-sampling-rules
    aws ecs describe-task-definition --task-definition payments-api-prod
    aws xray get-service-graph --start-time 2026-08-10T00:00:00Z --end-time 2026-08-10T23:59:59Z
```

## References

- Skill definition: `skills/xray-tracing-deployer/SKILL.md`
- Daemon and sampling guide: `skills/xray-tracing-deployer/references/daemon-and-sampling-guide.md`
- SDK instrumentation guide: `skills/xray-tracing-deployer/references/sdk-instrumentation-guide.md`
- Eval suite: `skills/xray-tracing-deployer/evals/evals.json`
