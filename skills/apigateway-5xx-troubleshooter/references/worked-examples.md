# Worked examples - API Gateway 5xx Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Worked example — 504 from timeout mismatch

```text
TARGET: def456/prod (integration: AWS_PROXY Lambda)
VERDICT: ROOT_CAUSE_FOUND
REASON: Lambda function timeout is configured at 60s but the REST API
  integration timeout is 29s — API Gateway returns 504 at 29s while the
  function continues running (Step 3c).
LAYER: TIMEOUT_MISMATCH
EVIDENCE:
  - Symptom: clients receive 504 GatewayTimeout on GET /reports after
    exactly 29 seconds.
  - Probe: aws lambda get-function-configuration returns Timeout: 60.
    The REST API integration timeout is 29s (hard ceiling).
  - Probe: Lambda Duration metric shows Maximum 45000ms — the function
    finishes at 45s, well after API Gateway returned 504 at 29s.
  - Passing: No Lambda Runtime.LogError; Lambda Throttles metric is zero;
    stage throttling not exceeded.
REMEDIATION:
  1. Reduce the Lambda Timeout to 29s so the function fails fast and
     logs the timeout error:
     aws lambda update-function-configuration --function-name reports-handler
       --timeout 29 --profile <p>
  2. Optimize the function to complete within 29s (database query tuning,
     caching, async processing for long-running reports).
  3. Alternatively, migrate to an async pattern: API Gateway returns 202
     immediately; the client polls or receives a webhook when the report
     is ready.
  4. Verify: GET /reports completes within 29s, or returns 202 for async.
```

### Worked example — 503 from stage-level throttling

```text
TARGET: ghi789/prod (integration: AWS_PROXY Lambda)
VERDICT: ROOT_CAUSE_FOUND
REASON: Stage prod has a rate limit of 100 rps and burst of 200; traffic
  peaked at 500 rps during the marketing campaign launch. API Gateway
  returned 503 for requests exceeding the throttle (Step 4a).
LAYER: THROTTLE_STAGE
EVIDENCE:
  - Symptom: clients receive 503 ServiceUnavailable during the 14:00 UTC
    traffic peak. No 502 or 504 reported.
  - Probe: aws apigateway get-stage returns methodSettings with
    throttlingRateLimit: 100, throttlingBurstLimit: 200.
  - Probe: CloudWatch Count metric for the stage shows Sum 300000 in the
    14:00-14:05 window (1000 rps average) — well above the 100 rps limit.
  - Passing: Lambda Throttles metric is zero (the function was not the
    bottleneck); Lambda ConcurrentExecutions is below the account limit;
    no usage plan is associated with the stage.
REMEDIATION:
  1. Raise the stage throttle to match expected peak traffic:
     aws apigateway update-stage --rest-api-id ghi789 --stage-name prod
       --patch-operations
       op=replace,path=/methods/*/throttling/rateLimit,value=1000,
       op=replace,path=/methods/*/throttling/burstLimit,value=2000
  2. Create a usage plan for per-API-key throttling to prevent a single
     client from exhausting the stage budget.
  3. Verify: CloudWatch 5xxError drops to zero after the throttle change.
```
