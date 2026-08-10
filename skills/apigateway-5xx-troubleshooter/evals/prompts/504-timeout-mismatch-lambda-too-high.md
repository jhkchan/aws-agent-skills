# Eval prompt: 504-timeout-mismatch-lambda-too-high

Diagnose the 5xx failure for the following API Gateway stage. Walk the
error-code-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: clients of API def456 (stage prod) receive 504 GatewayTimeout
on GET /reports after exactly 29 seconds. The reports-handler function
was recently changed to run a heavier database query. Before the change,
the endpoint returned within 5 seconds.

API id: def456 (REST API, v1)
Stage: prod
Integration: AWS_PROXY (Lambda proxy) on GET /reports
Lambda function: reports-handler
aws lambda get-function-configuration reports-handler:
  Timeout: 60
  MemorySize: 512
  Runtime: nodejs20.x
Lambda Duration metric (last hour): Maximum 45000ms during the failure
  window. Average 8000ms (older successful invocations).
Lambda Errors metric: zero (no Runtime.LogError).
Lambda Throttles metric: zero.
API Gateway Latency metric: Maximum 29000ms (the 29s ceiling).
API Gateway IntegrationLatency metric: Maximum 29000ms.
Access log integrationErrorMessage on failing requests: "Execution
  failed due to a timeout error."
Access log integrationStatus: 504.
Stage throttling: rateLimit 1000, burstLimit 2000 — not exceeded.

Emit the standard diagnostic block (TARGET, VERDICT, REASON, LAYER,
EVIDENCE, REMEDIATION).
