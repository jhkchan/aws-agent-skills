# Example usage: apigateway-throttle-optimizer

A walkthrough showing the skill optimizing a REST API used purely as a
Lambda proxy, demonstrating the REST-to-HTTP migration decision, caching
analysis, usage plan evaluation, the dollar savings math, and the staged
migration with verification.

## Input (user prompt)

> Review this API Gateway before our Q3 FinOps review. It is an
> e-commerce product catalog and order API running on REST API and
> the bill seems high.

```text
ApiName: product-catalog-api
ApiType: REST (REGIONAL)
Region: us-east-1
Stage: prod
Stage throttle: rate=10000 rps, burst=5000
Caching: disabled
Usage plans: none (single internal client)
Compression: disabled
WAF: not configured
VPC endpoint: not configured (REGIONAL)

Resources/Methods:
  - GET /products → Lambda proxy integration (no mapping template)
  - GET /products/{id} → Lambda proxy integration (no mapping template)
  - POST /orders → Lambda proxy integration (no mapping template)
  - No request validation schemas
  - No client certificates
  - Authorizer: Cognito User Pool (JWT)

Metrics (last 30 days):
  - Count: 200,000,000/month
  - 4xx: 5,000,000/month (2.5%)
  - 5xx: 100,000/month (0.05%)
  - Latency avg: 120 ms, p95: 250 ms
  - IntegrationLatency avg: 95 ms

Cost data:
  - Monthly cost: $700.00 (200M × $3.50/M)

Workload context: e-commerce product catalog + order submission.
All methods use Lambda proxy integration. No mapping templates,
no request validation, no stage caching. Cognito JWT authorizer
is used (supported on HTTP API).
```

## Skill output

```text
TARGET: product-catalog-api
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: REST API used purely as Lambda proxy — no mapping templates, no
  request validation, no stage caching, no client certificates. Cognito
  JWT authorizer is supported on HTTP API. HTTP API charges $1.00/M vs
  REST $3.50/M (71% reduction). No REST-only features block migration.
RECOMMENDATION:
  Current: REST (REGIONAL), rate=10000/burst=5000, no cache, no usage plans, no compression
  Proposed: HTTP API, rate=10000/burst=5000, no cache, no usage plans, no compression
  Dimensions changed: api-type (Step 1)
  Dimensions checked: api-type → (REST to HTTP)  throttle ✓ (10000 rps adequate)
    usage-plans ✓ (single internal client)  caching ✓ (HTTP API — evaluate CloudFront separately)
    payload ✓ (not reported)  waf ✓ (not configured)  vpc-endpoint ✓ (REGIONAL, not private)
  Confidence: HIGH — CloudWatch Count 200M/month directly measured;
    resource inventory confirms no REST-only features in use; Cognito
    JWT authorizer fully supported on HTTP API.
ESTIMATED_SAVINGS:
  Current monthly: $700.00
    requests: 200M / 1M × $3.50 = $700.00
  Projected monthly: $200.00
    requests: 200M / 1M × $1.00 = $200.00
  Monthly saving: $500.00
    ($700.00 − $200.00 = $500.00 ✓)
  Annual saving: $6,000.00
MIGRATION_STEPS:
  1. Create HTTP API with the same routes and Lambda proxy:
     aws apigatewayv2 create-api --name product-catalog-http --protocol-type HTTP --target <lambda-arn>
  2. Configure Cognito JWT authorizer on the HTTP API.
  3. Deploy the HTTP API and create a prod stage.
  4. Run side-by-side for 7 days, monitoring Count, 4xx, 5xx, Latency.
  5. Cutover traffic to the HTTP API (update DNS or API endpoint).
  6. Verify for 7 more days, then decommission the REST API:
     aws apigateway delete-rest-api --rest-api-id <rest-api-id>
CONFIRM: About to create a new HTTP API (product-catalog-http) and
  migrate traffic from product-catalog-api. Monthly saving $500.00 (71%
  reduction). REST API will be decommissioned after 14-day verification.
  Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **The REST-only feature check is the gating step.** A generic assistant
   says "switch to HTTP API, it is cheaper." The skill verifies the
   resource inventory — no mapping templates, no request validation, no
   client certificates, Cognito JWT (supported on HTTP API) — before
   recommending migration. If any REST-only feature were in use, the skill
   would block the migration and explain why.

2. **Caching is evaluated separately for HTTP API.** A generic assistant
   might say "enable caching." The skill notes that HTTP API does not
   support native response caching and recommends CloudFront as a separate
   optimization step, rather than incorrectly recommending stage caching
   on an API type that does not support it.

3. **All seven dimensions are checked and reported.** The skill shows
   `Dimensions checked` with all seven dimensions, each marked. A generic
   assistant focuses on one dimension (API type) and ignores WAF, VPC
   endpoint, usage plans, and payload.

4. **Side-by-side migration with verification.** The skill deploys the
   HTTP API alongside the REST API, runs side-by-side for 7 days, then
   cuts over. A generic assistant goes straight to creating the new API
   without a verification plan.

5. **Cost arithmetic is shown explicitly.** The skill shows the formula
   (`200M / 1M × $3.50 = $700.00` vs `200M / 1M × $1.00 = $200.00`) so
   the operator can verify. A generic assistant says "HTTP API is cheaper"
   without showing the math.

## Slash-command invocation

```
/aws:optimize-apigateway-throttle
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our API Gateway for the Q3 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: apigateway-throttle-optimizer]` and
hands off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new configuration:

```bash
# Confirm HTTP API is deployed and receiving traffic
aws apigatewayv2 get-api --api-id <http-api-id> \
  --profile default --region us-east-1

# Monitor Count, 4xx, 5xx for 7 days post-cutover
aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiId,Value=<http-api-id> Name=Stage,Value=prod \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 86400 --statistics Sum --output json

# Monitor 5xx for backend errors
aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway \
  --metric-name 5xx \
  --dimensions Name=ApiId,Value=<http-api-id> Name=Stage,Value=prod \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Sum --output json
```

If 5xx spikes or Latency regresses beyond the REST API baseline, roll
back by routing traffic to the REST API endpoint (keep it active for at
least 14 days before decommissioning).

## Fleet-wide extension

For a fleet of N API Gateway APIs, run the skill in batch mode:

1. Pull all REST APIs with `aws apigateway get-rest-apis`.
2. Pull all HTTP APIs with `aws apigatewayv2 get-apis`.
3. For each REST API, check for REST-only features in the resource
   inventory. Flag APIs with no REST-only features as migration candidates.
4. Sort REST APIs by request volume (largest first — savings scale with
   volume).
5. Slice into batches of 5 APIs.
6. For each batch: emit per-API MIGRATION_STEPS, then a single CONFIRM
   for the batch.
7. Verify each batch before proceeding to the next.
8. After the migration sweep, evaluate caching for remaining REST APIs
   that require REST-only features.
