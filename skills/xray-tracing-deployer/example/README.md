# End-to-End Example: X-Ray Tracing Deployment

A walkthrough showing how to use the `xray-tracing-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are enabling X-Ray distributed tracing on a Python Flask service
running on ECS Fargate. The service calls DynamoDB, S3, and SQS via
boto3. You want to use the ADOT Collector (OpenTelemetry) as a sidecar
instead of the X-Ray daemon, apply a custom sampling rule for the
checkout endpoint, and annotate traces with customer and environment
metadata. The service requires:

- Python 3.11 with opentelemetry-instrumentation-flask and
  opentelemetry-instrumentation-botocore
- ADOT Collector sidecar (gRPC 4317)
- Custom sampling rule: 100% on POST /checkout (reservoir 10/s)
- Default sampling rule: 5% for all other endpoints
- Annotations: customer_id, environment=production
- Metadata: response_status
- CloudWatch ServiceLens integration

Service name: `payments-api-prod`
Cluster: `payments-prod`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-xray-tracing
```

Then paste the tracing requirements.

### Option B: Natural language

```
You: "Enable distributed tracing on payments-api-prod on ECS Fargate
      cluster payments-prod in us-east-1. Use ADOT Collector sidecar.
      Python 3.11 with opentelemetry Flask + botocore instrumentation.
      Task role payments-task. Custom sampling rule payments-checkout
      at 100% on POST /checkout with reservoir 10/s. Default at 5%.
      Annotations: customer_id, environment=production. Metadata:
      response_status. Enable ServiceLens. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy x ray tracing"
```

Output:

```
[Phase: Deploy | Skills routed: xray-tracing-deployer]

Primary route: xray-tracing-deployer (score: 18)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
SERVICE: payments-api-prod
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Platform — ECS Fargate, cluster payments-prod
  [✓]      Daemon — ADOT Collector (aws-otel-collector) sidecar, gRPC 4317
  [✓]      SDK instrumentation — Python 3.11, opentelemetry-instrumentation-flask + opentelemetry-instrumentation-botocore
  [✓]      AWS SDK patched — BotocoreInstrumentor for DynamoDB, S3, SQS
  [✓]      Sampling rule — Default (reservoir 1/s, rate 5%), custom payments-checkout (reservoir 10/s, rate 100% on POST /checkout)
  [✓]      IAM role — payments-task has xray:PutTraceSegments + PutTelemetryRecords + GetSamplingRules + GetSamplingTargets
  [✓]      Annotations — customer_id, environment=production
  [✓]      Metadata — response_status
  [✓]      Service map — generated from traces (payments-api, DynamoDB, S3, SQS)
  [✓]      CloudWatch ServiceLens — integrated
VERIFICATION_COMMANDS:
  aws xray get-sampling-rules
  aws ecs describe-task-definition --task-definition payments-api-prod
  aws xray get-service-graph --start-time 2026-08-10T00:00:00Z --end-time 2026-08-10T23:59:59Z
```

---

## Step 3 — Deployment commands

The skill generates the CLI sequence (from
`references/daemon-and-sampling-guide.md`):

```bash
# Step 1: IAM permissions — attach AWSXRayDaemonWriteAccess to the task role
aws iam attach-role-policy \
  --role-name payments-task \
  --policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess

# Step 2: Register task definition with ADOT Collector sidecar
aws ecs register-task-definition \
  --family payments-api-prod \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 1024 --memory 2048 \
  --task-role-arn arn:aws:iam::123456789012:role/payments-task \
  --execution-role-arn arn:aws:iam::123456789012:role/payments-exec \
  --container-definitions '[
    {
      "name": "app",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/payments-api:2.1.0",
      "essential": true,
      "cpu": 768, "memory": 1536,
      "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
      "environment": [
        {"name": "OTEL_EXPORTER_OTLP_ENDPOINT", "value": "http://localhost:4317"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/payments-api-prod",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    },
    {
      "name": "aws-otel-collector",
      "image": "public.ecr.aws/aws-observability/aws-otel-collector:v0.40.0",
      "essential": true,
      "cpu": 256, "memory": 512,
      "portMappings": [{"containerPort": 4317, "protocol": "tcp"}],
      "environment": [
        {"name": "AWS_REGION", "value": "us-east-1"}
      ],
      "command": ["--config=/etc/otel-config/ecs-xray.yaml"],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/aws-otel-collector",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "otel"
        }
      }
    }
  ]'

# Step 3: Create custom sampling rule for checkout endpoint
aws xray create-sampling-rule --cli-input-json '{
  "SamplingRule": {
    "RuleName": "payments-checkout",
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

# Step 4: Update the service to use the new task definition
aws ecs update-service \
  --cluster payments-prod \
  --service payments-api-prod \
  --task-definition payments-api-prod:latest
```

---

## Step 4 — Post-deployment verification

```bash
# Sampling rules — verify default + custom checkout rule
aws xray get-sampling-rules

# Task definition — verify ADOT Collector sidecar
aws ecs describe-task-definition --task-definition payments-api-prod

# Service status — verify deployment is complete
aws ecs describe-services --cluster payments-prod --services payments-api-prod

# Service graph — verify traces are flowing (wait 5 min after deploy)
START=$(date -u -v-1H +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -d '1 hour ago' +"%Y-%m-%dT%H:%M:%SZ")
END=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
aws xray get-service-graph --start-time $START --end-time $END

# Trace summaries — verify checkout traces are sampled at 100%
aws xray get-trace-summaries --start-time $START --end-time $END \
  --filter-expression 'annotation.customer_id EXISTS'

# IAM role — verify X-Ray permissions
aws iam list-attached-role-policies --role-name payments-task \
  --query 'AttachedPolicies[?contains(PolicyName, `XRay`)]'
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| IAM GetSamplingRules + GetSamplingTargets | Not added | Added via AWSXRayDaemonWriteAccess | Without these, the SDK cannot fetch central sampling rules. Rules configured in the console are NEVER applied. |
| ADOT Collector sidecar | Not deployed | Deployed with correct config | The OTel SDK sends to gRPC 4317. Without the Collector, traces are silently dropped. |
| BotocoreInstrumentor | Not called | Called in app startup | Without it, downstream DynamoDB/S3/SQS calls don't generate subsegments. Service map shows only the entry point. |
| Custom checkout sampling | Not created | 100% on POST /checkout | The Default 5% rule undersamples critical checkout flows. Custom rule ensures 100% visibility on payment paths. |
| Annotation vs metadata | Conflated | customer_id as annotation, response_status as metadata | Annotations are indexable/searchable. Metadata is not. High-cardinality metadata avoids index bloat. |
| OTLP endpoint env var | Not set | OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 | The OTel SDK defaults to localhost:4317 but explicit is safer. |
| Cost control (Default 5%) | Often set to 100% | Default stays at 5% | 100% on Default for a high-traffic service generates massive trace volume and X-Ray charges. |

---

## Related artifacts

- **Skill definition:** `skills/xray-tracing-deployer/SKILL.md`
- **Daemon and sampling guide:** `skills/xray-tracing-deployer/references/daemon-and-sampling-guide.md`
- **SDK instrumentation guide:** `skills/xray-tracing-deployer/references/sdk-instrumentation-guide.md`
- **Slash command:** `commands/aws/deploy-xray-tracing.md`
- **Eval suite:** `skills/xray-tracing-deployer/evals/evals.json`
- **Legacy test cases:** `skills/xray-tracing-deployer/eval/test-cases.yaml`
