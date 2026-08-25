# Usage Plans, VPC Link, and Canary Deployments Reference

Supplementary reference for the API Gateway REST Deployer skill. Use when
configuring usage plans with API keys, deploying VPC Link for private
NLB-backed integrations, setting up canary deployments with traffic
shifting, or structuring CloudWatch access logs.

## Usage plans and API keys

A usage plan defines per-consumer throttling and quotas. API keys map
consumers to plans. The plan is enforced at the API stage level.

### Plan structure

```json
{
  "name": "prod-consumer-tier-1",
  "description": "Tier 1 consumers: 500 rps, 10M req/month",
  "throttle": {"burstLimit": 1000, "rateLimit": 500},
  "quota": {"limit": 10000000, "period": "MONTH"},
  "apiStages": [{"apiId": "<api-id>", "stage": "prod"}]
}
```

### Throttle semantics

| Field | Definition |
|---|---|
| `rateLimit` | Steady-state requests per second. Sustained rate allowed. |
| `burstLimit` | Short-burst capacity. Tokens refill at `rateLimit` per second. Peak rate. |

**Rule of thumb:** `burstLimit` should be 2-4x `rateLimit` to absorb
client-side concurrency without throttling. A `burstLimit` lower than
`rateLimit` makes the burst meaningless.

### Quota periods

| Period | Resets at |
|---|---|
| `DAY` | Midnight UTC |
| `WEEK` | Midnight UTC Monday |
| `MONTH` | Midnight UTC, first day of month |

Quotas do NOT carry over — they reset to zero at the boundary.

### API key to plan linkage

```bash
aws apigateway create-api-key --name "consumer-a-key" --enabled
aws apigateway create-usage-plan-key \
  --usage-plan-id <plan-id> \
  --key-id <key-id> --key-type API_KEY
```

Multiple API keys can map to the same plan (e.g., 10 consumers all on
"tier 1"). Each key gets its OWN throttle and quota bucket — the plan
defines the limits, the key identifies the consumer.

### Method requirement

For the usage plan to enforce, the method must have `apiKeyRequired: true`:

```bash
aws apigateway update-method --rest-api-id <id> --resource-id <rid> \
  --http-method GET \
  --patch-operations op=replace,path=/apiKeyRequired,value=true
```

Without this, the method is callable without an API key, and the usage
plan is bypassed.

## VPC Link

A VPC Link is an API Gateway-managed ENI collection in your VPC that
enables private HTTP/HTTPS integrations to NLB-backed resources without
internet exposure.

### Requirements

- **Target must be an NLB.** ALB is NOT directly supported. Front the
  ALB with an NLB, or target the ALB's underlying EC2 instances directly
  via an NLB target group.
- **NLB must be in the API's region.** Cross-region VPC Link is not
  supported.
- **NLB should span multiple AZs** for HA. A single-AZ NLB is a single
  point of failure.
- **Listener must be TCP or TLS.** HTTP listeners are not supported as
  VPC Link targets (TCP terminates at NLB; HTTPS is passed through).

### Deployment

```bash
aws apigateway create-vpc-link \
  --name prod-nlb-link \
  --target-arns arn:aws:elasticloadbalancing:<region>:<account>:loadbalancer/net/prod-nlb/abc123 \
  --description "VPC Link to prod NLB"

# Wait for AVAILABLE (2-5 min)
aws apigateway get-vpc-link --vpc-link-id <id> --query 'status'
```

### Integration configuration

```bash
aws apigateway put-integration \
  --rest-api-id <id> --resource-id <rid> --http-method GET \
  --type HTTP_PROXY \
  --connection-type VPC_LINK \
  --connection-id <vpc-link-id> \
  --integration-http-method GET \
  --uri "https://internal.prod-nlb.<region>.elb.amazonaws.com/api/users"
```

The `uri` field MUST use the NLB's DNS name (not the ALB's). The path in
the URI is the base path forwarded to the NLB.

### Security groups

The NLB's target instances (or ALB fronted by NLB) must allow inbound
on the listener port from the VPC Link's security group. The VPC Link
creates ENIs in your subnets; the source IP is the ENI's private IP.

## Canary deployments

A canary shifts a percentage of stage traffic to a new deployment. The
remaining traffic stays on the stage's current deployment. Used for
safe production rollouts.

### Enable canary

```bash
aws apigateway create-deployment \
  --rest-api-id <id> --stage-name prod \
  --canary-settings percentTraffic=10,useStageCache=true
```

This creates a new deployment and immediately routes 10% of traffic to
it. 90% stays on the previous deployment.

### Monitor canary

CloudWatch metrics include `Count4xx` `Count5xx` for both stable and
canary deployments. Watch canary 5xx; if elevated, abort:

```bash
aws apigateway update-stage \
  --rest-api-id <id> --stage-name prod \
  --patch-operations op=replace,path=/canarySettings/percentTraffic,value=0
```

Setting `percentTraffic` to 0 reverts all traffic to stable. The canary
deployment remains for inspection but serves no traffic.

### Promote canary

When metrics are green:
```bash
aws apigateway update-stage \
  --rest-api-id <id> --stage-name prod \
  --patch-operations op=replace,path=/canarySettings/percentTraffic,value=100
```

Then delete the canary (which makes the new deployment the stable):
```bash
aws apigateway delete-canary --rest-api-id <id> --stage-name prod
```

## CloudWatch access logging

JSON format with `$context` variables enables Athena/Insights queries.

### Recommended format

```json
{
  "requestId": "$context.requestId",
  "accountId": "$context.accountId",
  "apiId": "$context.apiId",
  "stage": "$context.stage",
  "requestTime": "$context.requestTime",
  "requestTimeEpoch": "$context.requestTimeEpoch",
  "httpMethod": "$context.httpMethod",
  "resourcePath": "$context.resourcePath",
  "status": "$context.status",
  "protocol": "$context.protocol",
  "responseLength": "$context.responseLength",
  "responseLatency": "$context.responseLatency",
  "sourceIp": "$context.identity.sourceIp",
  "userAgent": "$context.identity.userAgent",
  "errorMessage": "$context.error.message",
  "authorizerError": "$context.authorizer.error"
}
```

### Insights queries

Top 10 slowest requests:
```
fields @timestamp, requestId, resourcePath, responseLatency
| sort responseLatency desc
| limit 10
```

Error rate by route:
```
stats count(*) by resourcePath, status
| filter status >= 400
```

P99 latency by stage:
```
stats pct(responseLatency, 99) by stage
```

## Stage variables

Stage variables enable per-stage configuration without code changes.

### Common use cases

- **Per-stage Lambda function:** `arn:aws:lambda:<region>:<account>:function:${stageVariables.functionName}`
- **Per-stage endpoint:** `https://${stageVariables.endpointHost}/api`
- **Per-stage feature flag:** passed to Lambda via header in mapping template

### Set stage variables

```bash
aws apigateway update-stage --rest-api-id <id> --stage-name prod \
  --patch-operations \
    op=replace,path=/variables/functionName,value=prod-handler \
    op=replace,path=/variables/endpointHost,value=internal.prod.example.com
```

### Caching stage variables

Enable stage variable caching (`cacheClusterEnabled: true`) for high-
traffic APIs to avoid re-resolving the variable per request. Cache TTL
defaults to 300 seconds.

### Step 6: Usage plans and API keys

```bash
aws apigateway create-usage-plan --name prod-consumer-plan \
  --description "Per-consumer rate limiting for prod API" \
  --throttle burstLimit=200,rateLimit=100 \
  --quota limit=1000000,period=MONTH \
  --api-stages apiId=<api-id>,stage=prod
```

```bash
aws apigateway create-api-key --name consumer-a-key --description "Consumer A" --enabled
aws apigateway create-usage-plan-key --usage-plan-id <plan-id> \
  --key-id <key-id> --key-type API_KEY
```

**Per-method requirement:**
```bash
aws apigateway update-method --rest-api-id <id> --resource-id <rid> \
  --http-method GET \
  --patch-operations op=replace,path=/apiKeyRequired,value=true
```


### Step 7: Stage throttling

```bash
aws apigateway update-stage --rest-api-id <id> --stage-name prod \
  --patch-operations \
    op=replace,path=/methods/GET/throttling/rateLimit,value=100 \
    op=replace,path=/methods/GET/throttling/burstLimit,value=50 \
    op=replace,path=/*/throttling/rateLimit,value=1000 \
    op=replace,path=/*/throttling/burstLimit,value=500
```

The stage-level `*` (default) applies to all methods without explicit
overrides. Method-level overrides take precedence. Always set both rate
and burst — burst must be ≤ 25% of rate for sustained traffic.


### Step 9: VPC Link for private integrations

```bash
aws apigateway create-vpc-link --name prod-nlb-link \
  --target-arns arn:aws:elasticloadbalancing:<region>:<account>:loadbalancer/net/<nlb-name>/<nlb-id> \
  --description "VPC Link to prod NLB"
```

Wait for VPC Link status `AVAILABLE` (2-5 minutes). Then configure
HTTP or HTTP_PROXY integration with `connectionId: <vpc-link-id>` and
`connectionType: VPC_LINK`.

**Anti-pattern:** NEVER target an ALB directly via VPC Link — it is not
supported. Front the ALB with an NLB, or use HTTP integration with the
ALB DNS (which exposes the ALB to internet egress).


### Step 11: Canary deployments

```bash
aws apigateway update-stage --rest-api-id <id> --stage-name prod \
  --patch-operations \
    op=replace,path=/canarySettings/percentTraffic,value=10 \
    op=replace,path=/canarySettings/deploymentId,value=<new-deployment-id> \
    op=replace,path=/canarySettings/useStageCache,value=true
```

Canary routes 10% of traffic to the new deployment; 90% stays on the
current. Promote by setting `percentTraffic` to 100, then deleting the
canary (which makes the new deployment the stage's stable version).


