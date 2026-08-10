# Example usage: apigateway-5xx-troubleshooter

A walkthrough showing the skill diagnosing a 502 that masquerades as a
Lambda code bug, demonstrating the error-code-driven probe order, the
Lambda proxy response contract check, and the evidence-backed
ROOT_CAUSE_FOUND verdict.

## Input (user prompt)

> Our checkout API started returning 502 BadGateway after the last
> deployment. The Lambda function logs look clean — no errors, fast
> execution. We've been debugging this as a Lambda code issue for 20
> minutes. Help us find the actual root cause.

```text
API id: abc123 (REST API, v1)
Stage: prod
Integration: AWS_PROXY (Lambda proxy) on POST /checkout
Lambda function: checkout-handler
Lambda CloudWatch logs: no Runtime.LogError; "Completed in 180ms" at
  the failing request timestamps.
Lambda Duration metric: Average 180ms, Maximum 220ms — the function is
  fast and healthy.
Lambda Errors metric: zero.
API Gateway access log integrationErrorMessage on failing requests:
  "Execution failed due to configuration: Malformed Lambda proxy
   response"
Access log integrationLatency: 180-200ms (matches Lambda Duration).
aws lambda invoke with a test event returns:
  Payload: {"checkout_id": "chk_123", "status": "pending"}
  (Note: no statusCode, no body, no headers — bare object.)
```

## Skill output

```text
TARGET: abc123/prod (integration: AWS_PROXY Lambda)
VERDICT: ROOT_CAUSE_FOUND
REASON: The Lambda function checkout-handler returns a bare JSON object
  without the required statusCode field. API Gateway's Lambda proxy
  integration requires {statusCode, body, headers}. The access log
  confirms: integrationErrorMessage "Malformed Lambda proxy response"
  (Step 2b).
LAYER: BACKEND_RESPONSE_FORMAT
EVIDENCE:
  - Symptom: clients receive 502 BadGateway on POST /checkout after the
    last deployment. Lambda logs show no errors.
  - Probe: aws lambda invoke --function-name checkout-handler returns
    {"checkout_id":"chk_123","status":"pending"} — missing statusCode,
    body, and headers. The Lambda proxy contract requires all three
    (statusCode and body mandatory).
  - Probe: API Gateway access log integrationErrorMessage is
    "Execution failed due to configuration: Malformed Lambda proxy
    response" — the exact signature of BACKEND_RESPONSE_FORMAT.
  - Passing: Lambda Duration metric 180-220ms (function runs fast);
    Lambda Errors metric zero (no crash); Lambda Invocations spikes
    match API Gateway Count (function IS being invoked); Lambda
    Throttles zero; stage throttling not exceeded; CloudTrail confirms
    Invoke events.
REMEDIATION:
  1. Update the Lambda function to return the proxy response format:
     return {
       statusCode: 200,
       body: JSON.stringify({checkout_id: "chk_123", status: "pending"}),
       headers: {"Content-Type": "application/json"}
     };
  2. Deploy the Lambda function:
     aws lambda update-function-code --function-name checkout-handler ...
  3. Deploy the API (the response shape change requires the function
     redeploy only — no API Gateway config change, but verify the
     stage deploymentId is current):
     aws apigateway create-deployment --rest-api-id abc123
       --stage-name prod --profile <p>
  4. Verify: POST /checkout returns 200 with the expected body.
CONFIRM: Before deploying, emit and await:
  "CONFIRM: About to update-function-code on checkout-handler and
   create-deployment on abc123/prod. Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **The response contract, not the code.** A generic assistant sees
   "Lambda logs are clean, no errors" and concludes "the function is
   fine, must be API Gateway." The skill recognises that Lambda can
   execute successfully (no Runtime.LogError) but still produce an
   invalid proxy response — the 502 is a contract violation, not a code
   crash. The probe is `lambda invoke` to inspect the return shape, not
   a log scan.

2. **The access log signature.** The skill pattern-matches on
   `integrationErrorMessage: "Malformed Lambda proxy response"` as the
   exact signature of BACKEND_RESPONSE_FORMAT on a REST API Lambda proxy
   integration. A generic assistant treats 502 as a generic "backend
   error" without distinguishing the contract violation from a runtime
   crash.

3. **Evidence-backed verdict.** The skill produces a positive failing
   probe (the `lambda invoke` return value missing statusCode) AND
   passing probes (Lambda Duration, Errors, Throttles, Invocations).
   A generic assistant asserts the cause without evidence; an operator
   implementing the wrong fix (rewriting the function's business logic)
   loses another 20 minutes.

4. **Deployment verification.** The skill includes
   `create-deployment` in the remediation, even though the change is
   in the Lambda code. The deployment step verifies the stage
   `deploymentId` is current — operators who skip this step on
   "Lambda-only changes" can leave a stale integration response
   mapping live.

## Slash-command invocation

```
/aws:troubleshoot-apigateway-5xx
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why the checkout API returns 502 on POST /checkout"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: apigateway-5xx-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the response format:

```bash
# Confirm the function now returns the proxy contract
aws lambda invoke \
  --function-name checkout-handler \
  --payload file://test-event.json \
  --profile default \
  /tmp/response.json --query 'LogResult' --output text | base64 -d

# Inspect the response body
cat /tmp/response.json | jq '. | {statusCode, body, headers}'
# Expect: {"statusCode": 200, "body": "...", "headers": {...}}
```

Then monitor the API Gateway 5XXError CloudWatch metric for 15-30
minutes to confirm the 502 count drops to zero.
