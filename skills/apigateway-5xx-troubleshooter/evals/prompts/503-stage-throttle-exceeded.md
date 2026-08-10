# Eval prompt: 503-stage-throttle-exceeded

Diagnose the 5xx failure for the following API Gateway stage. Walk the
error-code-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: clients of API ghi789 (stage prod) receive 503
ServiceUnavailable starting at 14:00 UTC during a marketing campaign
launch. No 502 or 504 errors reported. The backend Lambda function is
healthy and reports no errors when invoked directly.

API id: ghi789 (REST API, v1)
Stage: prod
Integration: AWS_PROXY (Lambda proxy) on POST /checkout
aws apigateway get-stage ghi789/prod methodSettings:
  */throttling/rateLimit: 100
  */throttling/burstLimit: 200
CloudWatch Count metric (ApiName=ghi789, Stage=prod): Sum 300000 in the
  14:00-14:05 window (1000 rps average).
CloudWatch 5XXError metric: Sum 250000 in the same window.
Lambda Invocations metric: does NOT spike during the failure window —
  only 50000 invocations vs 300000 requests received.
Lambda Throttles metric: zero.
Lambda ConcurrentExecutions metric: 50 (well below account limit 1000).
No usage plan is associated with the stage (no API key required).
Access log integrationStatus on failing requests: "-" (integration was
  never invoked).
Access log integrationLatency: 0.

Emit the standard diagnostic block (TARGET, VERDICT, REASON, LAYER,
EVIDENCE, REMEDIATION).
