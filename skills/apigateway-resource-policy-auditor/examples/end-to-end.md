# End-to-end usage scenario: apigateway-resource-policy-auditor

A walkthrough showing the skill auditing a REST API that has a method
with `authorizationType: NONE` (PUBLIC_NO_AUTH), no usage plan
(NO_RATE_LIMIT), and no WAF (CONFIG_GAP), demonstrating the worst-verdict
aggregation and the API-key-is-not-auth expert knowledge delta.

## Input (user prompt)

> Review this API Gateway configuration before we go to production.
> The API serves our order-management backend.

```
API id: prod-order-api
Protocol type: REST
Endpoint type: REGIONAL
Resource policy: (none)
Stage: prod (deployed)
Usage plans: (none associated)
WAF Web ACL: (not associated)

Methods:
  Resource: /orders
    GET:  authorizationType: AWS_IAM, apiKeyRequired: false
    POST: authorizationType: NONE, apiKeyRequired: true
  Resource: /health
    GET:  authorizationType: NONE, apiKeyRequired: false
```

## Skill output

```text
API: prod-order-api
VERDICT: PUBLIC_NO_AUTH
REASON: Two methods have authorizationType NONE on a REGIONAL endpoint with
no resource-policy restriction. POST /orders relies on apiKeyRequired which
is NOT authentication (Step 2b). GET /health is fully unauthenticated
(Step 2a). No usage plan or WAF compounds the exposure.
FINDINGS:
  - [PUBLIC_NO_AUTH] POST /orders authorizationType NONE + apiKeyRequired true
    on REGIONAL endpoint — API key is not auth (Step 2b)
  - [PUBLIC_NO_AUTH] GET /health authorizationType NONE on REGIONAL endpoint
    — callable by anyone on the internet (Step 2a)
  - [NO_RATE_LIMIT] No usage plan associated with stage prod — no per-key
    throttling (Step 3)
  - [CONFIG_GAP] No WAF Web ACL on stage prod (Step 5)
  - [OK] GET /orders authorizationType AWS_IAM — properly authenticated
REMEDIATION:
  1. Set POST /orders authorizationType to AWS_IAM or COGNITO_USER_POOLS.
     apiKeyRequired provides usage-plan identification, NOT access control.
  2. Set GET /health authorizationType to AWS_IAM, or restrict via resource
     policy with aws:SourceIp conditions. A health check does not need to
     be public if monitoring uses AWS credentials.
  3. Create a usage plan and associate it with stage prod.
  4. Associate a WAF Web ACL with the stage for defense-in-depth.
```

## What the skill caught that a generic assistant misses

1. **API key is NOT authentication.** A generic assistant sees
   `apiKeyRequired: true` on POST /orders and says "the API key provides
   some protection." The skill recognises that API keys are plaintext
   tokens for usage-plan identification — shareable, leakable, and
   extractable from client-side code. The method is PUBLIC_NO_AUTH.

2. **Per-method auth evaluation.** A generic assistant may assess the API
   as "partially secured" because GET /orders uses AWS_IAM. The skill
   identifies that the weakest method determines the API's exposure —
   two methods with NONE auth make the entire API PUBLIC_NO_AUTH,
   regardless of the one secured method.

3. **Worst-verdict aggregation.** The verdict is PUBLIC_NO_AUTH (worst),
   but the FINDINGS list shows individual severities: two
   PUBLIC_NO_AUTH findings, one NO_RATE_LIMIT, one CONFIG_GAP, and one
   OK. This lets the operator triage each finding independently.

4. **The health-check anti-pattern.** A generic assistant may suggest
   leaving GET /health as public because "health checks need to be
   accessible." The skill notes that monitoring infrastructure can use
   AWS credentials — a public health endpoint leaks service status to
   attackers reconnoitering the API.

## Slash-command invocation

```
/aws:audit-apigateway-resource-policy
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this API Gateway before we go to production"
```

The orchestrator emits
`[Phase: Audit | Skills routed: apigateway-resource-policy-auditor]` and
hands off to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the configuration, validate the API posture:

```bash
# Verify the method authorization types
aws apigateway get-method --rest-api-id prod-order-api \
  --resource-id <rid> --http-method POST --profile default \
  | jq '.authorizationType'

# Confirm usage plan is associated
aws apigateway get-usage-plans --profile default \
  | jq '.items[] | select(.apiStages[].apiId=="prod-order-api")'

# Verify WACL association
aws apigatewayv2 get-web-acl-for-resource \
  --resource-arn arn:aws:apigateway:us-east-1::/restapis/prod-order-api/stages/prod \
  --profile default

# Deploy changes
aws apigateway create-deployment --rest-api-id prod-order-api \
  --stage-name prod --profile default
```

Then monitor CloudWatch metrics for `4xx` and `5xx` errors for 1-2 hours
after the auth change to catch any broken consumers.
