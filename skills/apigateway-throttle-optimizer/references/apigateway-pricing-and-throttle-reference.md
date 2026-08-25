# API Gateway Pricing and Throttle Reference

Supplementary reference for the API Gateway Throttle Optimizer skill.
Loaded on-demand when detailed pricing math, throttle limit ranges,
cache sizing, WAF/VPC endpoint cost calculations, or CLI sequences are
needed.

## API Gateway pricing (us-east-1, 2026, USD)

### Request pricing by API type

| API type | $/1M requests | Notes |
|---|---|---|
| REST API (REGIONAL) | $3.50 | Full feature set: caching, validation, mapping templates |
| REST API (EDGE) | $3.50 + CloudFront data transfer | Optimized for global latency via CloudFront |
| REST API (PRIVATE) | $3.50 + VPC endpoint | Accessible only within VPC |
| HTTP API | $1.00 | Proxy-only: Lambda proxy, HTTP proxy, VPC Link. No caching, no mapping templates |

### Key pricing insight

HTTP API is 3.5x cheaper than REST API for the same request volume. The
trade-off is feature availability: HTTP API lacks caching, mapping
templates, request validation, and other REST-specific features.

### Cache pricing

| Cache size | $/hour | $/month (730 hr) | Approx unique keys (100 KB avg) |
|---|---|---|---|
| 0.5 GB | $0.02 | $14.60 | ~5,000 |
| 1.3 GB | $0.03 | $21.90 | ~13,000 |
| 6.1 GB | $0.13 | $94.90 | ~61,000 |
| 13.5 GB | $0.25 | $182.50 | ~135,000 |
| 28.4 GB | $0.50 | $365.00 | ~284,000 |
| 58.2 GB | $1.00 | $730.00 | ~582,000 |
| 118 GB | $1.90 | $1,387.00 | ~1,180,000 |
| 237 GB | $3.80 | $2,774.00 | ~2,370,000 |

### WAF pricing

| Component | Cost | Notes |
|---|---|---|
| Per rule | $5.00/month | Billed per rule in the Web ACL |
| Per request inspected | $1.00/1M requests | Applies to all requests routed through the WAF |

### VPC endpoint (private API) pricing

| Component | Cost | Notes |
|---|---|---|
| Per endpoint per hour | $0.01 | Billed continuously while endpoint exists |
| Per GB data processed | $0.01 | Applies to traffic through the endpoint |

### Data transfer pricing

| Direction | $/GB | Notes |
|---|---|---|
| Out to internet (DTO) | $0.09 | First 100 TB/month, then $0.085 |
| Out via CloudFront | $0.085 | Slightly cheaper than direct DTO |
| Inter-AZ | $0.01 | API Gateway to Lambda in different AZ |

### Free tier

- 1,000,000 requests/month free (REST API, first 12 months)
- No free tier for HTTP API (as of 2026)
- Cache and WAF are NOT included in the free tier

## Throttle limits

### Default account-level throttle

| Dimension | Default | Adjustable |
|---|---|---|
| Rate | 10,000 rps | Yes (via quota increase) |
| Burst | 5,000 rps | Yes (via quota increase) |

### Stage-level throttle overrides

Stage-level throttle can be set lower than account-level. The most
specific throttle (method > stage > account) wins.

| Level | Scope | How to set |
|---|---|---|
| Account | All APIs in region | AWS account config |
| Stage | All methods in a stage | `update-stage` patch /throttle/rateLimit |
| Method | Single method | `update-method` patch /throttle/rateLimit |

### Usage plan throttle

| Dimension | How to set | Notes |
|---|---|---|
| Rate (rps) | `create-usage-plan --throttle rateLimit` | Per-API-key enforcement |
| Burst | `--throttle burstLimit` | Per-API-key enforcement |
| Quota | `--quota limit=N,period=MONTH` | Monthly request cap per key |

## REST-only features (blocks HTTP API migration)

| Feature | REST API | HTTP API |
|---|---|---|
| Response caching | YES (stage-level) | NO |
| Mapping templates (Velocity) | YES | NO |
| Request validation (schema) | YES | NO |
| Method-level auth (Lambda authorizer) | YES | Partial (2025, select regions) |
| Client certificates to backend | YES | NO |
| API Gateway-managed CORS | YES (per-method) | YES (API-level config, different model) |
| WAF Web ACL | YES | Partial (2024+) |
| Request/response transformation | YES | NO |
| Mock integration | YES | NO |

## Regional pricing multipliers (selected)

| Region | REST $/M | HTTP $/M | Notes |
|---|---|---|---|
| us-east-1 (N. Virginia) | $3.50 | $1.00 | Baseline |
| us-west-2 (Oregon) | $3.50 | $1.00 | Same as us-east-1 |
| eu-west-1 (Ireland) | $3.50 | $1.00 | Same |
| ap-southeast-1 (Singapore) | $4.20 | $1.20 | ~20% premium |
| ap-northeast-1 (Tokyo) | $4.20 | $1.20 | ~20% premium |

## CloudWatch metrics reference

| Metric | What it measures | Key threshold |
|---|---|---|
| Count | Total requests to the API | Cost allocation basis |
| 4xx | Client errors (including 429 throttle) | > 5% → investigate usage plans |
| 5xx | Server errors (backend failures) | > 0.1% → backend issue |
| Latency | Total response time (API Gateway + backend) | Compare to SLO |
| IntegrationLatency | Backend processing time only | > 100 ms → caching candidate |

### Cache hit ratio calculation

```
cache_hit_ratio = cached_requests / total_cacheable_requests

Note: CloudWatch does not directly report cache hit ratio. Estimate from:
  cache_hits = CacheHitCount (API Gateway metric)
  cache_misses = CacheMissCount
  hit_ratio = CacheHitCount / (CacheHitCount + CacheMissCount)
```

## Cost calculation worked examples

### Example 1: REST-to-HTTP migration

```
Current state:
  API type: REST
  Requests: 200M/month
  Monthly cost: 200M / 1M × $3.50 = $700.00

Projected state:
  API type: HTTP
  Requests: 200M/month
  Monthly cost: 200M / 1M × $1.00 = $200.00

Monthly saving: $500.00
Annual saving: $6,000.00
```

### Example 2: Cache enablement

```
Current state:
  API type: REST
  Requests: 100M/month
  Caching: disabled
  API cost: 100M / 1M × $3.50 = $350.00
  Lambda backend cost: 100M × $0.0000043 = $430.00
  Total: $780.00

Projected state:
  Caching: enabled (1.3 GB, TTL 3600s)
  Cache cost: $21.90/month
  Cacheable requests (70% of 100M): 70M
  Estimated cache hit ratio: 60% (hourly TTL, hourly change)
  Backend calls eliminated: 70M × 60% = 42M
  Lambda cost: (100M − 42M) × $0.0000043 = $249.40
  API cost: $350.00 (unchanged — API Gateway still receives all requests)
  Total: $350.00 + $249.40 + $21.90 = $621.30

Monthly saving: $780.00 − $621.30 = $158.70
```

### Example 3: Payload compression

```
Current state:
  Avg payload: 180 KB
  Requests: 50M/month
  DTO: 50M × 180 KB = 8,790 GB
  DTO cost: 8,790 × $0.09 = $791.10

Projected state (gzip at 30% ratio):
  Compressed payload: 54 KB (180 KB × 0.30)
  DTO: 50M × 54 KB = 2,637 GB
  DTO cost: 2,637 × $0.09 = $237.33

Monthly saving: $791.10 − $237.33 = $553.77
```

## AWS CLI quick reference

### Get API configuration (REST)

```bash
aws apigateway get-rest-apis --profile <profile> --region <region>
aws apigateway get-stages --rest-api-id <api-id>
aws apigateway get-resources --rest-api-id <api-id>
aws apigateway get-usage-plans
```

### Get API configuration (HTTP)

```bash
aws apigatewayv2 get-apis --profile <profile> --region <region>
aws apigatewayv2 get-stages --api-id <api-id>
```

### Get CloudWatch metrics

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=<api-name> Name=Stage,Value=prod \
  --start-time $(date -d '-30 days' +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --period 86400 --statistics Sum \
  --profile <profile> --region <region>
```

### Enable stage caching (REST only)

```bash
aws apigateway update-stage \
  --rest-api-id <api-id> \
  --stage-name prod \
  --patch-operations \
    op=replace,path=/caching/enabled,value=true \
    op=replace,path=/caching/cacheClusterStatus,value=AVAILABLE \
    op=replace,path=/caching/sizeInGB,value=1.3 \
    op=replace,path=/caching/ttlInSeconds,value=3600
```

### Create usage plan

```bash
aws apigateway create-usage-plan \
  --name "pro-tier" \
  --throttle burstLimit=100,rateLimit=50 \
  --quota limit=50000000,period=MONTH \
  --api-stages apiId=<api-id>,stage=prod
```

### Enable compression (REST)

```bash
aws apigateway update-rest-api \
  --rest-api-id <api-id> \
  --patch-operations op=add,path=/minimumCompressionSize,value=1024
```

# Step-by-step savings math and CLI (moved from SKILL.md)

### Step 1 — API type selection: savings math

**Savings math:**
```
monthly_saving = (monthly_requests / 1M) × ($3.50 − $1.00)
              = (monthly_requests / 1M) × $2.50

Example: 200M requests/month → 200 × $2.50 = $500/month
```


### Step 2 — throttle tuning: backend-capacity math and update-stage CLI

**Setting throttle to match backend capacity:**
```
max_rate = backend_max_concurrent / avg_integration_latency_s

Example: Lambda reserved concurrency = 200, avg latency = 0.1s
  max_rate = 200 / 0.1 = 2000 rps
  Set stage throttle: rate=2000, burst=1000
```

```bash
aws apigateway update-stage \
  --rest-api-id <api-id> \
  --stage-name prod \
  --patch-operations op=replace,path=/throttle/rateLimit,value=2000 op=replace,path=/throttle/burstLimit,value=1000
```


### Step 4 — response caching: cache cost vs benefit math

**Cache cost vs benefit:**
```
cache_cost = cache_size_GB × $0.02 × 730 hours/month

Example: 1.3 GB cache = $18.98/month

backend_saving = cached_requests × backend_cost_per_request
Example: 100M cached requests × $0.0000043 (Lambda avg) = $430/month

Net monthly saving: $430 − $18.98 = $411.02/month
```


### Step 4 — response caching: TTL tuning and update-stage CLI

**TTL tuning:**
- Default TTL: 300 seconds. Start here for most read APIs.
- Product catalog (changes hourly): TTL 3600 (1 hour).
- Configuration API (changes daily): TTL 86400 (1 day).
- User-specific data: TTL 0 (no cache) or use cache key variation.

```bash
aws apigateway update-stage \
  --rest-api-id <api-id> \
  --stage-name prod \
  --patch-operations op=replace,path=/caching/enabled,value=true \
                    op=replace,path=/caching/cacheClusterStatus,value=AVAILABLE \
                    op=replace,path=/caching/sizeInGB,value=1.3 \
                    op=replace,path=/caching/ttlInSeconds,value=300
```


### Step 5 — payload optimization: compression math

**Compression math:**
```
uncompressed_transfer = requests × avg_payload_KB / 1024
compressed_transfer = uncompressed_transfer × 0.3 (typical gzip ratio for JSON)

Example: 100M requests × 200 KB = 19,531 GB uncompressed
  Compressed (30%): 5,859 GB
  DTO saving: 13,672 GB × $0.09/GB = $1,230.48/month
```


### Step 5 — payload optimization: enable-gzip CLI

**Enable gzip on REST API (backend must send Content-Encoding: gzip):**
```bash
aws apigateway update-rest-api \
  --rest-api-id <api-id> \
  --patch-operations op=add,path=/minimumCompressionSize,value=1024
```


### Step 6 — WAF on API Gateway: cost math

**WAF on API Gateway:**
```
waf_cost = (rules × $5/month) + (requests_inspected / 1M × $1)

Example: 5 rules, 100M requests/month
  Rule cost: 5 × $5 = $25/month
  Request cost: 100 × $1 = $100/month
  Total: $125/month
```


### Step 6 — private API via VPC endpoint: cost math
**Private API via VPC endpoint:**
```
vpc_endpoint_cost = ($0.01 × 730 hours) + (data_transfer_GB × $0.01)

Example: $7.30/month + 10 GB × $0.01 = $7.40/month
```


