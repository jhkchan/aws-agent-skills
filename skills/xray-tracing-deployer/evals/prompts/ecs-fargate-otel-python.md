# Eval: ecs-fargate-otel-python

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — ADOT Collector sidecar, OTel SDK, custom sampling on checkout

## Prompt

Enable distributed tracing on a Python Flask service named
"payments-api-prod" running on ECS Fargate (cluster payments-prod)
in us-east-1. Use the ADOT Collector (OpenTelemetry) as a sidecar
container instead of the X-Ray daemon. Python 3.11 with
opentelemetry-instrumentation-flask and
opentelemetry-instrumentation-botocore. Task role payments-task
with X-Ray write permissions. Custom sampling rule
payments-checkout (100% on POST /checkout, reservoir 10/s).
Default rule at 5% for all other endpoints. Annotations:
customer_id, environment=production. Metadata: response_status.
Enable CloudWatch ServiceLens. Account: 123456789012.
