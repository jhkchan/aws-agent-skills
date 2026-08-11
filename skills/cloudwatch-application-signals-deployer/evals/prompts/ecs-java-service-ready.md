# Eval: ecs-java-service-ready

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — ECS Fargate Java, IAM policies attached, X-Ray sampling set

## Prompt

Enable CloudWatch Application Signals on the payments-api
service running on ECS Fargate in us-east-1. Runtime: Java 17
(Corretto). The task role payments-api-task already has
CloudWatchApplicationSignalsReportServiceAccess and
AWSXrayWriteOnlyAccess attached. X-Ray Default sampling rule
FixedRate=0.05. The service uses an ADOT collector sidecar
with the Java auto-instrumentation agent injected. Service
discovery via CloudMap namespace payments.local. Create a
99.9% availability SLO over 28 days rolling with burn-rate
alarms. Account: 123456789012.
