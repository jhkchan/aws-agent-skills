# Eval: missing-iam-permissions

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — GetSamplingRules + GetSamplingTargets required

## Prompt

Enable X-Ray tracing on a Node.js Express service named
"search-api-prod" on ECS Fargate in us-east-1. Use the X-Ray SDK
(aws-xray-sdk-core) with the xray-daemon:4.1 sidecar. The task
role search-task currently has xray:PutTraceSegments and
xray:PutTelemetryRecords but does NOT have
xray:GetSamplingRules or xray:GetSamplingTargets. The operator
has not added these permissions. Default sampling rule at 5%.
Account: 123456789012.
