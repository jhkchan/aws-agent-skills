# Eval prompt: 502-lambda-proxy-malformed-response

Diagnose the 5xx failure for the following API Gateway stage. Walk the
error-code-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: clients of API abc123 (stage prod) receive 502 BadGateway on
POST /orders. API Gateway access log shows `integrationErrorMessage:
"Execution failed due to configuration: Malformed Lambda proxy
response."` Lambda function orders-handler was deployed 30 minutes ago
with a new response shape. The function returns `{order_id: 123}` instead
of the proxy response contract.

API id: abc123 (REST API, v1)
Stage: prod
Integration: AWS_PROXY (Lambda proxy) on POST /orders
Lambda function: orders-handler
Lambda CloudWatch logs: no Runtime.LogError; function reports "Completed
in 245ms" at the matching timestamps.
Lambda Invocations metric: spikes matching the 5xxError spikes.
Lambda Errors metric: zero.
Access log integrationStatus: 502 for failing requests.
Access log integrationLatency: 240-260ms (function is fast — it runs,
just returns the wrong shape).

Emit the standard diagnostic block (TARGET, VERDICT, REASON, LAYER,
EVIDENCE, REMEDIATION).
