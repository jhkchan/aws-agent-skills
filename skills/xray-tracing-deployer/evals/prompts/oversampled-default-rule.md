# Eval: oversampled-default-rule

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — Default rule at 100% generates massive trace volume and cost

## Prompt

Enable X-Ray tracing on a high-traffic Node.js API named
"media-api-prod" on EKS in us-east-1. The service handles 5000
requests/second. The operator wants the Default sampling rule
set to FixedRate=1.0 (100%) so that "every request is traced."
Use the aws-xray-sdk-core with the X-Ray daemon DaemonSet. Node.js
20 with Express. Pod IRSA role media-api-xray-role. Annotations:
user_id, content_type. The EKS cluster is media-prod. Account:
123456789012.
