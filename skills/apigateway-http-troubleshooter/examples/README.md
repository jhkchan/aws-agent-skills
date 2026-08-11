# Example usage: apigateway-http-troubleshooter

A walkthrough showing the skill diagnosing a 502 Bad Gateway caused by
a payload format version 2.0 base64 body mismatch, demonstrating the
symptom-to-layer triage, the PayloadFormatVersion identification, the
evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and the base64 decode
fix.

## Input (user prompt)

> Our HTTP API started returning 502 Bad Gateway on POST /orders when
> the request body exceeds 1 KB. GET requests work fine. The Lambda
> function logs show a JSON parse error. We've been debugging the
> Lambda handler for an hour — please help us find the actual root
> cause.

```text
ApiId: api-payments-orders
ProtocolType: HTTP
Stage: $default
AutoDeploy: true
RouteKey: POST /orders
IntegrationType: AWS_PROXY
IntegrationSubtype: Lambda
PayloadFormatVersion: "2.0"
LambdaFunctionArn: arn:aws:lambda:us-east-1:111111111111:function:fn-orders-api

Lambda log excerpt:
  INFO  Received request on POST /orders
  SyntaxError: Unexpected token in JSON at position 0
  event.isBase64Encoded: true
  event.body: "eyJvcmRlcklkIjoiUGF5MTIzNCIs...
  END RequestId: ... Duration: 12 ms

GET /orders requests show:
  event.isBase64Encoded: false
  event.body: '{"filter": "active"}'
```

## Skill output

```text
TARGET: api api-payments-orders / POST /orders / stage $default
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Integration PayloadFormatVersion is 2.0; the Lambda handler
  reads event.body as raw JSON without checking isBase64Encoded. POST
  bodies exceeding 1 KB or containing non-ASCII content are
  base64-encoded by API Gateway v2.0 and arrive with
  isBase64Encoded: true. The handler's JSON.parse(event.body) throws
  SyntaxError, causing API Gateway to receive an error response and
  return 502 Bad Gateway (Step 5a).
LAYER: PAYLOAD_FORMAT_VERSION
EVIDENCE:
  - Symptom: POST /orders returns 502 when body > 1 KB; GET succeeds.
    The failure is body-size-dependent, not method-dependent.
  - Probe: aws apigatewayv2 get-integration --api-id api-payments-orders
    returns PayloadFormatVersion: "2.0".
  - Probe: Lambda logs show "SyntaxError: Unexpected token in JSON" at
    JSON.parse(event.body) with event.isBase64Encoded: true and
    event.body starting with "eyJ..." (base64-encoded JSON).
  - Probe: GET /orders shows event.isBase64Encoded: false and
    event.body as raw JSON — small GET query strings are not base64-
    encoded, explaining why GET works.
  - Passing: AutoDeploy true (deployment is not the issue); JWT
    authorizer Audience matches the token (authorizer is not the
    issue); CORS AllowOrigins includes the browser origin (CORS is
    not the issue); stage last deployment status is SUCCESSFUL.
REMEDIATION:
  1. Update the handler to check isBase64Encoded and decode:
     if (event.isBase64Encoded) {
       event.body = Buffer.from(event.body, 'base64').toString('utf-8');
     }
     const payload = JSON.parse(event.body);
  2. Redeploy the Lambda function:
     aws lambda update-function-code --function-name fn-orders-api \
       --zip-file fileb://deploy.zip --profile <p>
  3. Verify by sending a POST /orders with a 2 KB JSON body and
     confirming 200 response.
  4. Alternative: switch PayloadFormatVersion to 1.0 if the handler
     is shared with a REST API that uses v1.0:
     aws apigatewayv2 update-integration --api-id api-payments-orders \
       --integration-id int-xyz --payload-format-version 1.0
CONFIRM: Before updating the integration, emit and await:
  "CONFIRM: About to update integration PayloadFormatVersion on api
   api-payments-orders. Proceed? (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **Identified the payload format version as the root cause, not the
   handler code.** A generic assistant says "fix your JSON parsing."
   The skill recognises that PayloadFormatVersion 2.0 base64-encodes
   large/binary bodies — the handler is correct for v1.0 but breaks
   on v2.0 because it doesn't check `isBase64Encoded`.

2. **Explained why GET works but POST fails.** GET query strings are
   small and text-only, so API Gateway delivers them as raw strings
   (`isBase64Encoded: false`). POST bodies exceeding 1 KB trigger
   base64 encoding on v2.0. The skill's evidence section explicitly
   contrasts the two to confirm the diagnosis.

3. **Ruled out deployment, JWT, and CORS.** The skill verified
   AutoDeploy is true, JWT audience matches, and CORS is configured.
   This eliminates the other plausible causes before declaring the
   payload format version as the root cause.

4. **Recommended the handler-side fix first, CLI fix second.** The
   primary fix is making the handler base64-aware (more resilient).
   The secondary option is switching to v1.0 (quicker but less
   future-proof if the handler is also used on REST APIs).

## Slash-command invocation

```
/aws:troubleshoot-apigateway-http
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why POST /orders returns 502 on api-payments-orders"
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the integration:

```bash
# Confirm the integration payload format version
aws apigatewayv2 get-integration --api-id api-payments-orders \
  --integration-id int-xyz --output json --profile default \
  | jq '.PayloadFormatVersion'

# Confirm Lambda error rate dropped
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=fn-orders-api \
  --start-time $(date -d '-30 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum \
  --profile default --output json

# Confirm API Gateway 5XX rate dropped
aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiId,Value=api-payments-orders \
  --start-time $(date -d '-30 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum \
  --profile default --output json
```

Then monitor for 1-2 hours to confirm the 502 count drops to zero.
