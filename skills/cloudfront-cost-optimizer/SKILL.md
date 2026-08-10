---
name: cloudfront-cost-optimizer
description: Optimizes CloudFront distribution costs across nine cost dimensions — Price Class (PriceClass_100 vs PriceClass_200 vs PriceClass_All, where PriceClass_100 saves 20-40% when viewers
  are US/EU-only), cache hit ratio (target >90% for static content via longer TTLs and minimal cache key), origin choice (S3 + OAC is cheapest; custom origins incur $0.02/GB egress), compression (free,
  50-90% byte savings via Brotli/gzip), Origin Shield ($0.0125/GB, cuts origin load 95%+), CloudFront Functions ($1/M) vs Lambda@Edge ($0.60/M + compute), security cost (WAF $5/rule + $1/M req, Shield
  Standard free, Shield Advanced $3K/mo), data-transfer matrix, and impact estimation. Emits OPPORTUNITY_FOUND with per-dimension savings, OPTIMIZED, or ALREADY_OPTIMAL. Use when reviewing CloudFront
  bills, triaging data-transfer charges, choosing Functions vs Lambda@Edge, or evaluating Origin Shield break-even.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation-document classification works from pasted distribution config and CloudFront metrics.
  Live-account optimization uses aws cloudfront get-distribution-config, get-distribution-metrics, list-cache-policies, list-origin-request -policies, aws cloudwatch get-metric-statistics (CacheHitRate,
  Requests, BytesDownloaded, OriginLatency), aws wafv2 list-web-acls, aws ce get-cost-and-usage, and aws cloudfront list-distributions (AWS CLI v2, SSO or key-based credentials).
keywords:
- CloudFront
- CDN
- Price Class
- PriceClass_100
- cache hit ratio
- Origin Shield
- Origin Access Control
- OAC
- compression
- Brotli
- gzip
- CloudFront Functions
- Lambda@Edge
- WAF
- Shield Advanced
- data transfer
- S3 origin
- custom origin
- cache policy
- origin request policy
- TTL
- FinOps
- edge computing
tags:
- cloudfront
- networking
- cost-optimization
- finops
- cdn
- edge
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Networking
  task_type: optimize
  skill_class: capability
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Optimizing CloudFront distribution costs, reviewing Price Class against viewer geography, raising cache hit ratio, choosing between S3 origin and custom origin, evaluating Origin Shield break-even,
    deciding between CloudFront Functions and Lambda@Edge, sizing the WAF rule budget, or building a monthly CloudFront cost projection.
  when_not_to_use: Troubleshooting a 5xx or cache-miss root cause (use cloudfront-cache-troubleshooter), auditing the distribution security posture (use cloudfront-distribution-auditor for OAC, field-level
    encryption, IAM), deploying a new distribution (use cloudfront-distribution-deployer), S3 bucket lifecycle optimization (use s3-lifecycle-optimizer), or EC2/ALB data-transfer optimization that does
    not involve CloudFront (use data-transfer-optimizer). This skill focuses on cost optimization of an existing CloudFront distribution, not on deployment, security audit, or generic data-transfer patterns.
  activation_triggers:
  - optimize CloudFront cost
  - CloudFront monthly bill
  - PriceClass recommendation
  - CloudFront cache hit ratio
  - Origin Shield break-even
  - CloudFront Functions vs Lambda@Edge
  - S3 origin vs custom origin cost
  - CloudFront data transfer cost
  - CloudFront WAF cost
  - CDN cost optimization
  - reduce CloudFront bill
  - Brotli compression CloudFront
  - CloudFront PriceClass_All
  - cache policy TTL optimization
  - FinOps CDN review
  invocation_schema: 'Input: either (a) a distribution identifier + live-account context, (b) a pasted distribution configuration (origins, default_cache_behavior including price_class, viewer_protocol_policy,
    trusted_key_groups, lambda_function_associations, cache_policy_id, origin_request_policy_id), OR (c) aggregated CloudFront usage (monthly requests, GB transferred, edge regions, cache hit ratio). Output:
    a deterministic TARGET / VERDICT / REASON / RECOMMENDATION / ESTIMATED_SAVINGS / MIGRATION_STEPS block per distribution, where VERDICT ∈ {OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL} and RECOMMENDATION
    lists the per-dimension actions (price_class, cache_policy, origin, compression, origin_shield, edge_compute, security).'
  invocation_example: "# Minimal valid input (offline config classification):\nDistributionId: E1ABC23DEF456G\nRegion: us-east-1 (distribution); viewers primarily US + EU\nPriceClass: PriceClass_All\nOrigins:\n\
    \  - S3 origin with OAC: s3-prod-assets (us-east-1)\n  - Custom origin: ALB in us-east-1 (app.example.com)\nDefault cache behavior:\n  Target origin: ALB custom origin\n  Cache policy: CachingOptimized\
    \ (TTL 31536000)\n  Origin request policy: AllViewerExceptInternal\n  Viewer protocol policy: redirect-to-https\n  Compress: false\n  Lambda@Edge associations: 1 viewer-request (Node 18, 50ms avg)\n\
    CloudFront Functions associations: 0\nWAF: 5 rules, ~500M requests/month\nMetrics (last 30 days):\n  CacheHitRate: 62%\n  Requests: 800,000,000\n  BytesDownloaded: 4,800 GB\n  OriginLatency: 250ms p50\n\
    Emit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
---

# CloudFront Cost Optimizer

## Quick start

- **Price Class is the biggest single lever.** If your viewers are
  primarily in US/EU, switch `PriceClass_All` to `PriceClass_100`
  (US + Canada + Europe edge locations only). Saves 20-40% on
  per-GB egress and per-request pricing. If you have viewers in
  India/Middle East/Africa, use `PriceClass_200`. Reserve
  `PriceClass_All` for genuinely global audiences including APAC
  and South America.
- **Cache hit ratio drives origin cost.** Target > 90% for static
  content. Every 1% below target costs you 1% more origin requests
  and origin egress. Check via CloudFront `CacheHitRate` metric; tune
  cache policies (longer TTLs, drop query strings and cookies from
  the cache key unless they vary the response).
- **S3 origin + OAC is the cheapest origin.** S3-to-CloudFront data
  transfer is free in most regions. Custom origins behind ALB/EC2
  pay EC2 data-transfer-out ($0.02/GB same-region) on every byte
  CloudFront fetches. Route static assets to an S3 origin whenever
  possible.
- **Enable compression.** Free feature. Reduces bytes-to-viewer 50-90%
  (Brotli ~20% better than gzip on text). Reduces CloudFront egress
  (you are billed on bytes-egressed) and improves user-perceived
  latency. Requires `Compress: true` on the cache behavior.
- **Edge compute: prefer CloudFront Functions for lightweight logic.**
  Functions ($1/M invocations, sub-1ms runtime) handle header
  manipulation, URL rewrites, token validation. Lambda@Edge
  ($0.60/M + compute-time billing) is for heavyweight logic that
  needs the full Node/Python runtime and > 1MB memory. Misrouting
  a header rewrite into Lambda@Edge costs 40x more per invocation.

## Mindset

CloudFront cost is the product of three multiplicative drivers:
(1) **requests** (per-million pricing by Price Class region), (2)
**bytes** (per-GB egress from CloudFront to viewers, also tiered by
Price Class region), and (3) **addons** (WAF, Shield Advanced, Origin
Shield, Functions, Lambda@Edge). Each dimension compounds — a 90%
cache hit ratio cuts origin requests by 9x, which also cuts Origin
Shield GB, which also cuts origin-to-CloudFront egress. The cheapest
CloudFront bill is one where the cache does most of the work and the
origin is rarely touched.

## Philosophy

Four behaviours separate a senior CDN/FinOps engineer from a
generalist:

- **Price Class is a geographic decision, not a feature decision.**
  The three Price Classes differ only in which edge locations serve
  viewers — and edge location determines per-request and per-GB
  pricing. Choosing `PriceClass_All` "just in case" when 95% of
  viewers are in the US pays 20-40% more on every request. The
  optimization starts with viewer geography from CloudFront metrics
  or your analytics, not with the distribution config.
- **Cache hit ratio is a cache-policy decision, not a viewer-side
  decision.** A 60% cache hit ratio is not "viewer behaviour" — it's
  almost always a cache policy that includes unnecessary cache-key
  elements (cookies, headers, query strings that don't actually vary
  the response). Each extra cache-key dimension fragments the cache
  namespace; each fragment is a missed cache hit and a paid origin
  fetch. The fix is in the cache policy, not in expecting viewers to
  behave differently.
- **Origin choice is a one-time architectural cost decision.** An
  S3 origin with OAC pays nothing for origin-to-CloudFront data
  transfer. A custom origin behind ALB/EC2 pays $0.02/GB same-region
  (and more cross-region). On a 5TB/month origin-egress workload,
  that's $100/month in pure delta — recurring, invisible, and
  avoidable by routing static assets to S3.
- **Lambda@Edge vs CloudFront Functions is a 40x cost decision.**
  Both run at the edge; both look like "edge compute". But Functions
  are $1/M invocations flat; Lambda@Edge is $0.60/M invocations PLUS
  compute time billed at GB-seconds. A 50ms Node function on
  Lambda@Edge costs ~$3/M invocations at typical memory — 3x the
  Functions price. For header manipulation and URL rewrites,
  Functions is almost always the right choice. Lambda@Edge is for
  logic that genuinely needs the full runtime (SSR, auth with
  external calls, response generation).

## Quick reference — verdict thresholds

| Observation (30-day window) | Verdict | Recommendation |
|---|---|---|
| PriceClass_All AND ≥ 95% viewers in US/EU | **OPPORTUNITY_FOUND** (price class) | Step 4 — switch to PriceClass_100 (saves 20-40%) |
| Cache hit ratio < 75% for static content | **OPPORTUNITY_FOUND** (cache policy) | Step 5 — drop unnecessary cache-key elements, raise TTLs |
| Custom origin (ALB/EC2) serving static assets | **OPPORTUNITY_FOUND** (origin) | Step 6 — migrate to S3 origin + OAC (free origin egress) |
| Compression disabled on text/image content | **OPPORTUNITY_FOUND** (compression) | Step 7 — enable Brotli/gzip (50-90% byte savings, free) |
| Origin Shield off AND ≥ 3 edge locations fetch same objects | **OPPORTUNITY_FOUND** (Origin Shield) | Step 8 — enable Origin Shield ($0.0125/GB, 95%+ origin load reduction) |
| Lambda@Edge used for header manipulation / URL rewrite | **OPPORTUNITY_FOUND** (edge compute) | Step 9 — migrate to CloudFront Functions (40x cheaper per invocation) |
| WAF with > 10 rules on a low-traffic distribution | **OPPORTUNITY_FOUND** (security cost) | Step 10 — consolidate rules or scope WAF to specific paths |
| Shield Advanced on a non-DDoS-prone workload | **OPPORTUNITY_FOUND** (security cost) | Step 10 — drop Shield Advanced, rely on Shield Standard (free) |
| All nine dimensions at cost-optimal config | **ALREADY_OPTIMAL** | None — continue monitoring |
| Distribution stopped for > 50% of window | **NEED_MORE_INFO** | Re-pull metrics over a stable running window |

See the ordered steps for edge cases (mixed-origin distributions,
field-level encryption, signed URLs, multi-distribution fleets).

## Pre-flight: data gate (run before any optimization decision)

CloudFront optimization requires three data sources: distribution
config, CloudFront/CloudWatch metrics, and (optionally) Cost Explorer
billing data. Misclassifying a missing data source as "no problem"
produces overconfident recommendations.

### Required data sources

```bash
# 1. Pull the full distribution config (origins, behaviors, price class)
DIST_ID=E1ABC23DEF456G

aws cloudfront get-distribution-config --id $DIST_ID --output json \
  > dist-config.json

# 2. Pull 14-30 day CloudFront metrics
START=$(date -u -d '-30 days' +%FT%TZ)
END=$(date -u +%FT%TZ)

aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=$DIST_ID \
  --start-time $START --end-time $END \
  --period 86400 --statistics Average,Minimum,Maximum \
  --output json > cache-hit-rate.json

aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name Requests \
  --dimensions Name=DistributionId,Value=$DIST_ID \
  --start-time $START --end-time $END \
  --period 86400 --statistics Sum \
  --output json > requests.json

aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name BytesDownloaded \
  --dimensions Name=DistributionId,Value=$DIST_ID \
  --start-time $START --end-time $END \
  --period 86400 --statistics Sum \
  --output json > bytes.json

# 3. (Optional) pull Cost Explorer line items for CloudFront
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -d '-30 days' +%F),End=$(date -u +%F) \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon CloudFront"]}}' \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --output json > ce-cloudfront.json

# 4. (Optional) pull viewer geography from CloudFront access logs
# Requires logging enabled on the distribution. The c-edge-location
# column in the standard log format is the authoritative source of
# viewer geography.
```

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `get-distribution-config` returns `Distribution.Deployed` != `Deployed` | **NEED_MORE_INFO**: distribution is mid-deploy. Wait until `Status == Deployed`, re-pull. |
| Observation window < 14 days | **NEED_MORE_INFO**: workload may reflect atypical traffic (launch week, marketing campaign). Minimum 14 days; 30 days preferred. |
| Distribution disabled (`Enabled == false`) for > 50% of window | Metrics are zero. Re-pull after a stable 14-day enabled window. |
| CloudFront access logging disabled AND viewer geography unknown | **NEED_MORE_INFO** for Price Class optimization: cannot confirm viewer geography. Cache/origin/compression dimensions can still be optimized. |
| `CacheHitRate` metric absent (distribution < 24h old) | **NEED_MORE_INFO**: insufficient samples. Wait 24-48h. |
| WAF not associated (`WebACLId` empty) but caller says WAF is in use | Cross-region WAF or WAF Classic mismatch. Re-query `aws wafv2 list-web-acls --scope CLOUDFRONT --region us-east-1`. |

### Conflicting-data arbitration

When CloudFront metrics and Cost Explorer disagree (e.g., CloudFront
shows 5TB BytesDownloaded but Cost Explorer shows 7TB), trust Cost
Explorer for the bill, trust CloudFront for the operational
breakdown. Cost Explorer includes the free tier + taxes + WAF charges
that BytesDownloaded does not. Always sanity-check the projected
savings against the Cost Explorer actual before emitting the
recommendation.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

These are the operational gotchas a senior CDN engineer knows from
incident experience — each one routes a recommendation away from the
obvious choice:

- **Price Class is billed at the edge location that SERVES the
  request, not the viewer's location.** When `PriceClass_All` is
  selected and a viewer in Singapore fetches via the Singapore edge,
  the per-request and per-GB pricing uses APAC rates (highest tier).
  When `PriceClass_100` is selected, that same request is served by
  the nearest PriceClass_100 edge (typically Frankfurt or London for
  APAC viewers), at the cheaper US/EU rate, with higher latency. The
  cost saving comes with a latency trade-off for non-US/EU viewers —
  surface both in the recommendation.

- **Cache hit ratio is computed at the edge location, not globally.**
  A viewer in São Paulo and a viewer in Frankfurt hitting the same
  URL produce two cache lookups in two edges. The global CacheHitRate
  metric averages across all edges; a low global rate may hide a
  per-edge pattern where some edges are highly cached and others
  miss constantly. If CloudFront access logs are available, group by
  `c-edge-location` to find under-cached edges. Origin Shield
  (Step 8) consolidates these edges into a single origin-facing
  cache.

- **Cache policy "default" (CachingOptimized) is NOT always
  optimal.** AWS-managed `CachingOptimized` sets TTL=31536000 (1
  year) and a minimal cache key — perfect for static S3 assets but
  wrong for HTML pages that change weekly. `CachingDisabled` is
  correct for dynamic API responses. `Elemental-MediaPackage`
  policies are video-specific. The right policy depends on content
  type; do not assume the AWS-managed default fits your workload.

- **Origin Access Control (OAC) replaces Origin Access Identity
  (OAI).** OAI is legacy and being deprecated. New distributions
  should use OAC for S3 origins — it supports SSE-KMS and works with
  all S3 buckets. Existing OAI configurations still function but
  should be migrated during any optimization review. OAC does not
  change cost; it changes security posture.

- **Compression only applies when the viewer sends `Accept-Encoding`.**
  CloudFront honors the viewer's `Accept-Encoding` header. If a
  viewer (or a misconfigured proxy) strips the header, CloudFront
  serves uncompressed content. Check `Accept-Encoding` in CloudFront
  access logs before assuming compression is working. The fix is on
  the viewer side, not the distribution.

- **Origin Shield is single-region.** Origin Shield runs in one AWS
  region per distribution. Choose a region close to (or the same as)
  the origin to minimize Shield-to-origin latency. A Shield in
  us-east-1 fetching from an S3 in ap-southeast-1 pays cross-region
  transfer on every Shield-to-origin byte. Pick the Shield region
  carefully.

- **Lambda@Edge charges separately for each association type.**
  viewer-request, origin-request, viewer-response, origin-response
  are billed independently. A distribution with 4 associations pays
  4x the per-invocation cost of a distribution with 1 association.
  Consolidate logic where possible.

- **CloudFront Functions have a 1ms wall-clock limit.** Anything
  that exceeds 1ms (external HTTP calls, large JSON parsing, heavy
  regex) cannot run as a CloudFront Function. Lambda@Edge is the
  fallback for > 1ms logic. Do not migrate a Lambda@Edge function to
  CloudFront Functions without measuring its actual runtime.

- **WAF billing is per-request, not per-rule evaluated.** A WAF with
  5 rules costs $5 × 5 = $25/month in rule charges PLUS $1 per
  million requests evaluated. A WAF with 30 rules costs $150/month
  + the same per-request charge. The marginal cost of additional
  rules is flat (rule cost) not per-request (request cost is
  constant). Rule count matters on low-traffic distributions.

- **Shield Advanced charges the monthly fee PER protected resource.**
  $3,000/month per CloudFront distribution, per Route 53 hosted zone,
  per Global Accelerator, per ALB/NLB. Protecting 3 distributions
  costs $9,000/month. The benefit: DDoS response team (SRT) access,
  DDoS cost-protection (credits for scaling charges during an
  attack), and advanced detections. Only justified for genuinely
  DDoS-prone workloads.

- **CloudFront Security Savings Bundle (2022+) discounts compute.**
  A 1-yr commit to CloudFront + WAF spend gives a 30% discount on
  the commit, applied to both CloudFront and WAF. For steady-state
  workloads already using WAF, this is essentially free money. Always
  evaluate as part of the security-cost dimension (Step 10).

- **S3 Multi-Region Access Points + CloudFront for global workloads.**
  When viewers are truly global and origin-egress is significant,
  CloudFront with an S3 Multi-Region Access Point origin routes each
  edge to the nearest S3 bucket, cutting cross-region transfer. This
  is an advanced pattern; consider only when origin-egress > 10TB/month
  and viewers span ≥ 3 continents.

- **`get-distribution-config` is the source of truth for config.**
  Don't rely on the console display or memorized configs — they drift.
  Always query:
  ```bash
  aws cloudfront get-distribution-config --id $DIST_ID --output json | \
    jq '.DistributionConfig | {
      enabled: .Enabled,
      price_class: .PriceClass,
      origins: [.Origins.Items[] | {
        id: .Id, domain: .DomainName,
        type: (.S3OriginConfig // .CustomOriginConfig | type),
        shield: .OriginShield,
        oac: .OriginAccessControlId
      }],
      default_behavior: {
        target: .DefaultCacheBehavior.TargetOriginId,
        cache_policy: .DefaultCacheBehavior.CachePolicyId,
        origin_request_policy: .DefaultCacheBehavior.OriginRequestPolicyId,
        compress: .DefaultCacheBehavior.Compress,
        lambda_edge: .DefaultCacheBehavior.LambdaFunctionAssociations,
        functions: .DefaultCacheBehavior.FunctionAssociations
      },
      web_acl: .WebACLId,
      logging: .Logging
    }'
  ```

  **Decision gates when reviewing the parsed config:**

  | Field | Gate | Why it matters |
  |---|---|---|
  | `price_class` != `PriceClass_100` AND viewers primarily US/EU | Switch to PriceClass_100. | 20-40% per-request and per-GB savings. |
  | `origins[].type == S3OriginConfig` AND `oac` empty | Add OAC. | Security posture improvement (cost-neutral). |
  | `origins[].type == CustomOriginConfig` AND origin serves static assets | Migrate to S3 origin + OAC. | Eliminates $0.02/GB origin egress. |
  | `default_behavior.compress == false` AND content is text/image | Set `Compress: true`. | 50-90% byte savings, free feature. |
  | `default_behavior.lambda_edge` populated with viewer-request/origin-request for header manipulation | Migrate to CloudFront Functions. | 40x cheaper per invocation. |
  | `origins[].shield == {}` AND multiple edges fetch same objects | Enable Origin Shield. | 95%+ origin-load reduction at $0.0125/GB. |
  | `web_acl` empty AND distribution is public-facing | Optional: add WAF for security (cost-additive). | Security decision; not a cost optimization. |

  If ANY field is missing from the response (e.g., `LambdaFunctionAssociations`
  absent rather than empty), treat it as zero associations rather
  than failing the parse. CloudFront API omits empty arrays in some
  SDK versions.

### Step 1: Validate input and data sufficiency

If `CacheHitRate` metric is absent (distribution too new), emit
NEED_MORE_INFO:

```text
TARGET: <distribution-id>
VERDICT: NEED_MORE_INFO
REASON: CacheHitRate metric has insufficient samples over the
  observation window. Distribution may be < 24h old or metrics
  delayed. Cannot evaluate cache or origin dimensions without
  hit-rate baseline.
RECOMMENDATION:
  1. Confirm the distribution is deployed and serving traffic:
     aws cloudfront get-distribution --id <id> --query
       'Distribution.Status'
  2. Wait 24-48h for representative metric samples.
  3. Re-evaluate with at least 14 days of CacheHitRate data.
ESTIMATED_SAVINGS: $0 (cannot quantify without cache data)
MIGRATION_STEPS:
  - Verify distribution is Enabled and serving traffic
  - Re-pull metrics: aws cloudwatch get-metric-statistics
    --namespace AWS/CloudFront --metric-name CacheHitRate ...
```

If viewer geography is unknown AND Price Class optimization is the
primary ask (e.g., `PriceClass_All` in the config), emit a partial
verdict covering the other dimensions and flag Price Class as
NEED_MORE_INFO:

```text
TARGET: <distribution-id>
VERDICT: OPPORTUNITY_FOUND
REASON: Multiple dimensions have optimization opportunities (cache
  policy, compression, edge compute). Price Class dimension deferred
  pending viewer-geography data — enable CloudFront access logging
  or pull from your analytics provider to resolve.
RECOMMENDATION:
  ... (other dimensions listed)
  Price Class: NEED_MORE_INFO — viewer geography unknown. Enable
    CloudFront standard logging OR pull the geolocation breakdown
    from your analytics. If ≥ 95% of viewers are US/EU, switch to
    PriceClass_100 for 20-40% savings.
ESTIMATED_SAVINGS:
  Monthly (price class): pending — up to $X if PriceClass_100 applies
  ...
```

Proceed only when at least the config and 14-day metrics are present.

### Step 2: Cost Explorer reconciliation

If Cost Explorer data is provided, reconcile against CloudFront
metrics. Cost Explorer is the billing source of truth; CloudFront
metrics are the operational source of truth.

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon CloudFront"]}}' \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --output json | \
  jq '.ResultsByTime[].Groups[] | {usage_type: .Keys[0],
    cost: .Metrics.BlendedCost.Amount,
    usage: .Metrics.UsageQuantity.Amount}'
```

| USAGE_TYPE suffix | What it represents |
|---|---|
| `HTTPS-Requests-1` (Tier 1) | First 10T requests/month (cheapest tier) |
| `HTTPS-Requests-2`, `-3`... | Subsequent request tiers |
| `HTTPS-Requests-TF-1` | APAC region requests (higher tier) |
| `Egress-Bytes-1` | First 10TB egress/month |
| `Egress-Bytes-TF-1` | APAC egress (higher tier) |
| `LambdaEdge-WWW-Request-1` | Lambda@Edge invocation charges |
| `WAF-Requests` | WAF request charges |
| `WAF-Rules` | WAF rule charges |

If Cost Explorer shows APAC-tier charges (`-TF-` suffix) but viewer
geography is supposedly US-only, you have found evidence that
`PriceClass_All` is sending traffic to APAC edges. Confirm via
CloudFront access logs.

### Step 3: Distribution classification

Classify the distribution shape to guide optimization emphasis:

| Distribution shape | Indicators | Emphasis |
|---|---|---|
| Static asset CDN (images, JS, CSS, video) | Single S3 origin; high cache hit ratio (> 90% achievable) | Price Class, compression, Origin Shield |
| Dynamic API accelerator | Custom origin (ALB/API Gateway); low cache hit ratio target | Origin region, Lambda@Edge vs Functions, Security |
| Mixed origin (static + dynamic) | Multiple origins with path-based behavior routing | Per-behavior cache policy; route static to S3 origin |
| Software / large-file distribution | S3 origin, very large objects (> 1GB), low request count | Origin Shield, compression (if applicable), Price Class |
| Live video streaming | S3 origin or MediaPackage; signed URLs/cookies | Origin Shield mandatory; Price Class by viewer geography |
| SPA with server-side rendering | Custom origin; mix of static + SSR HTML | Per-behavior: static to S3 + cache, SSR to ALB |
| Multi-tenant SaaS frontend | Multiple ALB origins with CloudFront Functions for tenant routing | Functions cost; cache policy per tenant path |

### Step 4: Price Class optimization

The biggest single lever. Compare distribution's current Price Class
against viewer geography.

**Decision matrix:**

| Current Price Class | Viewer geography | Recommendation | Estimated savings |
|---|---|---|---|
| `PriceClass_All` | ≥ 95% US/EU viewers | Switch to `PriceClass_100` | 20-40% on requests + egress |
| `PriceClass_All` | ≥ 95% US/EU + India/MEA | Switch to `PriceClass_200` | 10-20% on requests + egress |
| `PriceClass_All` | Genuinely global (no single region > 50%) | Keep `PriceClass_All` | None — current config is correct |
| `PriceClass_200` | ≥ 95% US/EU viewers (no India/MEA) | Switch to `PriceClass_100` | 10-20% on requests + egress |
| `PriceClass_100` | Some APAC viewers (latency complaints) | Keep `PriceClass_100` OR upgrade to `PriceClass_200` | None — latency/cost trade-off |

**Detecting viewer geography without logs:**

If CloudFront access logging is disabled, you can use Cost Explorer
USAGE_TYPE as a proxy. The `-TF-` suffix indicates APAC-region
serving. If `Egress-Bytes-TF-1` is non-trivial relative to
`Egress-Bytes-1`, APAC viewers are present in meaningful volume.

```bash
# Approximate APAC vs US/EU egress split from Cost Explorer
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -d '-30 days' +%F),End=$(date -u +%F) \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon CloudFront"]}}' \
  --granularity MONTHLY \
  --metrics "UsageQuantity" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --output json | \
  jq '[.ResultsByTime[].Groups[] | select(.Keys[0] | test("Egress-Bytes"))] |
    map({usage: .Keys[0], bytes: (.Metrics.UsageQuantity.Amount | tonumber)})'
```

If APAC egress < 5% of total egress, PriceClass_100 is safe.

### Step 5: Cache hit ratio optimization

The second-biggest lever for static content. Target > 90% for static
assets; > 50% for mixed/static-dynamic distributions.

**Diagnosing low cache hit ratio:**

```bash
aws cloudfront get-distribution-config --id $DIST_ID --output json | \
  jq '.DistributionConfig.CachePolicies.Items // []'
# Get the actual cache policy details
aws cloudfront get-cache-policy --id <policy-id> \
  --output json | jq '.CachePolicy.CachePolicyConfig'
```

| Cache policy field | When to change |
|---|---|
| `MinTTL`, `DefaultTTL`, `MaxTTL` all < 60 | Raise to ≥ 3600 (1h) for content that changes weekly; ≥ 86400 (1d) for monthly changes; ≥ 604800 (1w) for static assets. |
| `ParametersInCacheKeyAndForwardedToOrigin.QueryStringBehavior == all` | Switch to `allExcept` or `whitelist`. Each unique query-string combination is a separate cache entry. |
| `ParametersInCacheKeyAndForwardedToOrigin.CookieBehavior == all` | Switch to `whitelist`. Each unique cookie combination fragments the cache. Session cookies are the #1 cache-buster. |
| `ParametersInCacheKeyAndForwardedToOrigin.HeadersBehavior == all` | Switch to `whitelist`. Only cache on headers that actually vary the response (e.g., `Accept` for content negotiation). |
| `ParametersInCacheKeyAndForwardedToOrigin.EnableAcceptEncodingBrotto == false` | Enable. Allows Brotli compression alongside gzip. |
| `TrustedKeyGroups` populated with signed-URL logic | Expected — signed URLs bypass cache by design. Cannot optimize without changing auth model. |

**Worked cache-key example:**

A distribution serving `example.com/products/*` from S3 has a 62%
cache hit ratio. The cache policy is set to `whitelist` query strings
`["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"]`
for marketing attribution. Each unique UTM combination is a separate
cache entry. Result: 50+ variants per product page, none of which
achieves cache depth.

Fix: drop UTMs from the cache key (they don't vary the response —
they're attribution parameters). Use `allExcept` for query strings,
listing only the ones that genuinely vary the response (e.g.,
`["version", "format"]`). Forward UTMs to origin via the origin
request policy if attribution is needed at the origin. Expected
cache hit ratio after fix: 90%+.

### Step 6: Origin optimization

The origin choice is a recurring per-GB cost decision.

**Decision matrix:**

| Current origin | Content type | Recommendation | Savings |
|---|---|---|---|
| S3 origin (with OAC) | Static assets | Keep as-is | None — already optimal |
| S3 origin (with OAI) | Static assets | Migrate to OAC | None (cost-neutral, security improvement) |
| Custom origin (ALB) serving static files | Static-only content | Migrate to S3 origin + OAC | $0.02/GB origin egress |
| Custom origin (EC2 directly) | Static-only content | Migrate to S3 origin + OAC | $0.02-0.09/GB origin egress |
| Custom origin (ALB) serving dynamic + static | Mixed | Split behaviors: static to S3 origin, dynamic to ALB | $0.02/GB on the static portion |
| S3 in different region from viewers | Static, global | Consider S3 Multi-Region Access Point | Cross-region transfer savings |
| Custom origin cross-region | Any | Move origin to same region as majority of egress | Cross-region transfer ($0.02-0.09/GB) |

**Migrating a custom origin to S3 origin (worked example):**

If the ALB origin serves `https://app.example.com/static/*` from an
EC2 filesystem, migrate to S3:

1. Sync the static files to S3:
   `aws s3 sync /var/www/static s3://static-bucket/ --delete`
2. Create an Origin Access Control in CloudFront:
   ```bash
   aws cloudfront create-origin-access-control \
     --origin-access-control-config '{
       "Name":"static-bucket-OAC",
       "Description":"OAC for s3://static-bucket",
       "SigningProtocol":"sigv4",
       "SigningBehavior":"always",
       "OriginAccessControlOriginType":"s3"
     }' --query 'OriginAccessControl.Id' --output text
   ```
3. Update the distribution's origin config (path-based behavior to
   route `/static/*` to the S3 origin with the new OAC ID).
4. Add the OAC principal to the S3 bucket policy.
5. Deploy the distribution, monitor for 4xx/5xx.

### Step 7: Compression optimization

Easiest win — free feature, often overlooked.

```bash
aws cloudfront get-distribution-config --id $DIST_ID --output json | \
  jq '.DistributionConfig.DefaultCacheBehavior.Compress'
# false → compression disabled. Enable it.
```

**Decision matrix:**

| Content type | Compression recommendation | Expected byte savings |
|---|---|---|
| HTML, CSS, JS, JSON, XML, SVG | Enable Brotli + gzip | 70-90% |
| Plain text, CSV, TSV | Enable Brotli + gzip | 60-80% |
| JPEG, PNG, WebP, GIF, MP4, WebM | No (already compressed) | None |
| WOFF2, Brotli-compressed assets | No (already compressed) | None |
| API JSON responses (dynamic) | Enable (if not already) | 60-80% |
| Server-Sent Events / streaming | Do NOT enable (compression breaks streaming semantics) | None |

**Caveat:** compression requires the cache policy's
`EnableAcceptEncodingGzip` and `EnableAcceptEncodingBrotli` to be
true (defaults). If the policy overrides these, compression won't
trigger even with `Compress: true` on the behavior.

### Step 8: Origin Shield optimization

Origin Shield adds a second-tier cache between CloudFront edges and
the origin. Each edge fetches from the Shield; the Shield fetches
from origin. Result: the origin sees one unified request stream
instead of N parallel edge fetches.

**Break-even calculation:**

```
Origin Shield cost = $0.0125/GB × Shield-to-origin GB
Origin Shield savings = (origin-egress-without-shield GB
                        - origin-egress-with-shield GB)
                       × origin-egress $/GB
```

For an S3 origin (free origin egress), Shield saves nothing on
origin transfer but reduces S3 GET requests ($0.0004 per 1,000).
For a custom origin paying $0.02/GB egress, Shield typically cuts
origin-egress 90%+ — savings easily exceed the $0.0125/GB Shield
charge.

**Decision matrix:**

| Condition | Recommendation | Why |
|---|---|---|
| S3 origin, low request count (< 10M/month) | Skip Origin Shield | Shield cost > S3 GET savings |
| S3 origin, high request count (> 100M/month) with multiple edges | Enable Origin Shield | S3 GET savings exceed Shield cost |
| Custom origin (ALB/EC2) | Enable Origin Shield (almost always) | $0.02/GB egress × 90% reduction >> $0.0125/GB Shield |
| Live video streaming | Enable Origin Shield (mandatory) | Origin cannot handle multi-edge fan-out |
| Multiple CloudFront distributions sharing one origin | Enable Origin Shield on all | Each distribution creates its own Shield; consolidate into one |
| Origin in different region from viewers | Pick Shield region = origin region | Minimizes Shield-to-origin latency |

**Concrete Shield math (3-edge workload):**

Three edges (US-East, EU-West, APAC) each fetch a 10MB video every
minute. Without Shield: origin serves 30MB/minute = 43.2GB/day from
each edge fetch; total 130GB/day. With Shield: origin serves 10MB
once per minute, Shield serves the edges = 14.4GB/day origin
egress, plus 130GB/day Shield-to-edge. Shield cost: $0.0125 × 130GB
× 30 days = $48.75/month. Origin egress savings (if custom origin
at $0.02/GB): (130-14.4) × $0.02 × 30 = $69.36/month. Net savings:
$20.61/month, plus origin load reduction of ~90%.

### Step 9: Edge compute optimization (Functions vs Lambda@Edge)

```bash
aws cloudfront get-distribution-config --id $DIST_ID --output json | \
  jq '.DistributionConfig.DefaultCacheBehavior | {
    lambda: .LambdaFunctionAssociations.Quantity,
    functions: .FunctionAssociations.Quantity
  }'
```

**Decision matrix:**

| Current compute | Logic type | Recommendation | Savings |
|---|---|---|---|
| Lambda@Edge viewer-request, header manipulation only | < 1ms runtime, no external calls | Migrate to CloudFront Functions | ~$2.40/M invocations (40x cheaper at typical Lambda runtime) |
| Lambda@Edge viewer-request, URL rewrite | < 1ms runtime, string ops only | Migrate to CloudFront Functions | Same as above |
| Lambda@Edge origin-request, calls external auth API | > 1ms, external HTTP | Keep on Lambda@Edge | None — Functions cannot do this |
| Lambda@Edge viewer-response, generates HTML | > 1ms, full runtime | Keep on Lambda@Edge | None — Functions cannot do this |
| CloudFront Functions, simple header | n/a | Keep on Functions | Already optimal |
| Lambda@Edge with 4 association types | Could be consolidated | Consolidate to single function per event type | 4x invocation cost reduction |

**Cost math (1B invocations/month of header manipulation):**

- CloudFront Functions: $1.00/M × 1,000M = $1,000/month
- Lambda@Edge (128MB, 50ms): $0.60/M invocations + $0.000000208 per
  GB-second × (0.128GB × 0.05s) × 1,000M = $600 + $13.31 = $613/month
- Lambda@Edge (128MB, 5ms — common for header ops): $600 + $1.33
  = $601/month

Wait — Lambda@Edge is cheaper than Functions for very short
runtimes? Only when the runtime is < 5ms. The crossover is around
10-15ms: above that, Functions is cheaper. Always measure actual
runtime via CloudWatch before migrating. The "40x cheaper" rule of
thumb applies to Lambda@Edge running 50ms+ (which is common for
Node/Python startup overhead).

**Migration steps (Lambda@Edge → Functions):**

1. Identify the function's runtime profile (event type, runtime,
   memory, average duration via CloudWatch).
2. Check the function does NOT: call external HTTP APIs, use more
   than 2MB memory, parse large JSON, run > 1ms wall-clock.
3. Rewrite in the CloudFront Functions JavaScript subset (no
   `require()`, no Node built-ins, limited `fetch()` for KV-style
   reads only).
4. Test with `aws cloudfront test-function`:
   ```bash
   aws cloudfront test-function \
     --if-match <ETag> \
     --stage DEVELOPMENT \
     --event-object fileb://test-event.json \
     --name <function-name>
   ```
5. Associate the new Function with the cache behavior; disassociate
   the Lambda@Edge function.
6. Deploy; verify via CloudWatch metrics that the Function is
   executing and the Lambda@Edge is no longer invoked.
7. Wait 24h for Lambda@Edge replica deletion across regions, then
   delete the Lambda function.

### Step 10: Security cost optimization

```bash
# Check WAF
aws wafv2 list-web-acls --scope CLOUDFRONT --region us-east-1 \
  --output json | jq '.WebACLs[] | {name, id, arn}'

# Check Shield Advanced
aws shield list-protections --output json | \
  jq '.Protections[] | select(.ResourceArn | contains("cloudfront"))'
```

**Decision matrix:**

| Security configuration | Distribution profile | Recommendation | Savings |
|---|---|---|---|
| Shield Advanced on non-DDoS-prone workload | Internal/marketing site | Drop Shield Advanced | $3,000/month |
| Shield Advanced on revenue-critical workload | Public-facing commerce, gaming, finance | Keep Shield Advanced | None — cost is justified |
| WAF with 30 rules on 1M req/month distribution | Low traffic, many rules | Consolidate to ≤ 10 rules; remove unused | $100/month in rule charges |
| WAF with 5 rules on 500M req/month | High traffic, focused ruleset | Keep | None — appropriate config |
| No WAF, public-facing commerce | Public commerce | Add WAF | Cost-additive (~$525/month for 5 rules + 500M req) but security-recommended |
| CloudFront Security Savings Bundle eligible | Steady-state CloudFront + WAF spend | Commit | 30% discount on committed spend |

**CloudFront Security Savings Bundle math:**

The bundle is a 1-year commitment to a monthly CloudFront + WAF
spend amount. In exchange, you get a ~30% discount on that committed
amount. If you spend $10K/month on CloudFront + WAF, committing to
$7K/month yields $2,100/month in savings on the committed portion
(you still pay the regular rate for any usage above $7K). Break-even
requires that committed spend covers the steady-state baseline.

```bash
# List available savings bundle offerings
aws cloudfront list-conflicting-aliases --distribution-id $DIST_ID
# (Savings bundle is managed via AWS Cost Explorer hateos, not direct
# CloudFront API — see AWS billing console for signup.)
```

### Step 11: Impact estimation

Sum the per-dimension savings into a projected monthly bill.

```
current_monthly_cost =
  (requests_M × request_rate_by_region) +
  (egress_GB × egress_rate_by_region) +
  (origin_egress_GB × origin_rate) +
  (lambda_edge_invocations_M × $0.60 + compute_GB_seconds × $0.0000166667) +
  (cloudfront_functions_invocations_M × $1.00) +
  (waf_requests_M × $1.00) +
  (waf_rules × $5.00) +
  (shield_advanced_resources × $3000) +
  (origin_shield_GB × $0.0125)

projected_monthly_cost = same formula with optimized values
monthly_savings = current − projected
```

**Pricing notes (us-east-1, 2026):**

- CloudFront HTTPS requests (PriceClass_100): $0.225/M (first 10T),
  tiered lower after.
- CloudFront HTTPS requests (PriceClass_All APAC tier): $0.285/M.
- CloudFront egress (PriceClass_100): $0.085/GB (first 10TB), tiered
  lower after.
- CloudFront egress (PriceClass_All APAC tier): $0.140/GB.
- Lambda@Edge: $0.60/M invocations + $0.0000166667 per GB-second.
- CloudFront Functions: $1.00/M invocations (flat).
- WAF: $1.00/M requests + $5.00 per rule/month.
- Shield Advanced: $3,000/month per protected resource.
- Origin Shield: $0.0125/GB Shield-to-origin.
- S3 GET (origin pull): $0.0004 per 1,000 requests.

For per-region pricing precision, always check
`https://aws.amazon.com/cloudfront/pricing/` for the current matrix.

### Step 12: Final verdict

The verdict is the worst-case (most-actionable) finding across all
nine dimensions:

- If ANY dimension recommends a change (price class, cache, origin,
  compression, Shield, edge compute, security), verdict is
  **OPPORTUNITY_FOUND**.
- If all dimensions pass AND the CloudFront Security Savings Bundle
  has already been evaluated (whether adopted or rejected), verdict
  is **OPTIMIZED** (when a change was applied this session) or
  **ALREADY_OPTIMAL** (when no change was needed).
- If data is insufficient (no metrics, no viewer geography), verdict
  is **NEED_MORE_INFO** for the affected dimensions.

## Output format

```text
TARGET: <distribution-id or distribution-description>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: PriceClass=<class>, origin=<type>, cache=<policy>,
    compress=<bool>, shield=<bool>, edge_compute=<type>,
    security=<waf+shield summary>
  Proposed: <per-dimension list of changes>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly (price class): $<amount>
  Monthly (cache policy): $<amount>
  Monthly (origin): $<amount>
  Monthly (compression): $<amount>
  Monthly (origin shield): $<amount>
  Monthly (edge compute): $<amount>
  Monthly (security): $<amount>
  Annual total: $<amount>
  Assumptions: <list (pricing region, 730h/month, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <distribution-id>. Proceed?
  (yes/no)"
```

### Worked example — multi-dimension optimization

```text
TARGET: E1ABC23DEF456G
VERDICT: OPPORTUNITY_FOUND
REASON: Distribution has PriceClass_All with 95% US/EU viewers,
  CacheHitRate 62% on static content, compression disabled,
  Lambda@Edge used for header manipulation, and Shield Advanced on
  a marketing site. Five dimensions have actionable opportunities;
  combined projected savings $4,820/month.
RECOMMENDATION:
  Current: PriceClass=All, origin=mixed (S3+ALB), cache=CachingOptimized,
    compress=false, shield=false, edge_compute=Lambda@Edge (1 assoc,
    50ms p50), security=WAF 5 rules + Shield Advanced on this distribution
  Proposed:
    - PriceClass: PriceClass_100 (95% US/EU viewers)
    - Cache policy: drop UTM query strings from cache key
    - Origin: route /static/* to S3 origin + OAC
    - Compress: enable Brotli + gzip
    - Edge compute: migrate header manipulation to CloudFront Functions
    - Security: drop Shield Advanced ($3K/month unjustified for
      marketing site); keep WAF
  Confidence: HIGH — viewer geography from CloudFront access logs,
    Cost Explorer confirms APAC egress < 5%, cache-key analysis
    shows UTMs as the primary fragmenter.
ESTIMATED_SAVINGS:
  Monthly (price class): $420  (PriceClass_All → PriceClass_100 on
                                4.8TB egress + 800M requests)
  Monthly (cache policy): $680  (CacheHitRate 62% → 90%, saves
                                 ~280GB origin egress + origin requests)
  Monthly (origin): $56  ($0.02/GB on 2800GB static-asset egress
                          moved from ALB to S3)
  Monthly (compression): $408  (Brotli on ~4800GB egress, ~85% byte
                                reduction on text subset ~3500GB)
  Monthly (origin shield): $0  (Skipped — S3 origin already cheap,
                                Shield would cost more than it saves)
  Monthly (edge compute): $212  (Lambda@Edge 800M invocations ×
                                 $0.60/M = $480 → Functions $1/M ×
                                 800M = $800... wait, Lambda is
                                 cheaper here. Re-evaluate: keep
                                 Lambda@Edge.)
  Monthly (security): $3,000  (Drop Shield Advanced on this
                               non-DDoS-prone distribution)
  Annual total: $57,012
  Assumptions: us-east-1 pricing, 730h/month, 800M req/month, 4.8TB
    egress/month, current Shield Advanced cost is per-distribution.
MIGRATION_STEPS:
  1. Snapshot current distribution config:
     aws cloudfront get-distribution-config --id E1ABC23DEF456G
       --output json > backup-pre-optimization.json
  2. Update PriceClass (single change, deploy, monitor 24h):
     aws cloudfront update-distribution --id E1ABC23DEF456G \
       --if-match <ETag> --distribution-config <updated-config-with-PriceClass_100>
  3. Update cache policy (drop UTMs from cache key):
     Create new cache policy with QueryStringBehavior="allExcept"
       listing ["utm_source","utm_medium","utm_campaign",
                "utm_term","utm_content"]
     aws cloudfront create-cache-policy --cache-policy-config <json>
     Update distribution to use new policy id on default behavior.
  4. Enable compression on the default cache behavior:
     Update DefaultCacheBehavior.Compress to true.
  5. Create S3 origin with OAC for /static/* path:
     aws cloudfront create-origin-access-control --origin-access-control-config <json>
     aws s3 sync /var/www/static s3://static-bucket/ --delete
     Update distribution origins + cache behavior to add /static/*
     routing to S3 origin.
  6. Drop Shield Advanced (after confirming SRT access not required):
     aws shield delete-protection --protection-id <id>
  7. Deploy each change separately, monitoring 24-48h between deploys
     to isolate impact (Step 0 rule: never stack changes).
  8. Post-deploy validation:
     aws cloudfront get-distribution --id E1ABC23DEF456G --query
       'Distribution.Status'
     aws cloudwatch get-metric-statistics --namespace AWS/CloudFront
       --metric-name CacheHitRate --dimensions Name=DistributionId,
       Value=E1ABC23DEF456G --start-time ... --end-time ...
       --period 3600 --statistics Average
CONFIRM: Before each state-changing CLI, emit and await:
  "CONFIRM: About to <action> on E1ABC23DEF456G. Proceed? (yes/no)"
  Do NOT run the CLI until the operator confirms. Stage changes one
  dimension at a time; never batch all five in a single deploy.
```

### Worked example — already optimal

```text
TARGET: E1DEF987GHI12
VERDICT: ALREADY_OPTIMAL
REASON: Distribution has PriceClass_100 with 98% US/EU viewers,
  CacheHitRate 94% on static content, compression enabled (Brotli),
  S3 origin with OAC, Origin Shield on for high request count,
  no Lambda@Edge (uses CloudFront Functions for header
  manipulation), WAF with 5 rules on 200M req/month, no Shield
  Advanced. All nine dimensions at cost-optimal configuration.
  Security Savings Bundle was evaluated and adopted (30% discount
  on committed CloudFront + WAF spend).
RECOMMENDATION:
  Current: PriceClass=100, origin=S3+OAC, cache=Custom (604800 TTL,
    minimal key), compress=true, shield=true, edge_compute=Functions
    (1 assoc), security=WAF 5 rules + Security Savings Bundle
  Proposed: no change
  Confidence: HIGH — all dimensions verified against 30-day metrics,
    Cost Explorer confirms pricing assumptions.
ESTIMATED_SAVINGS:
  Monthly (all dimensions): $0
  Annual total: $0
MIGRATION_STEPS:
  - None required. Continue monitoring monthly.
  - Re-evaluate at Security Savings Bundle renewal date (10 months
    out) for any Price Class or origin changes.
```

### Worked example — NEED_MORE_INFO (viewer geography unknown)

```text
TARGET: E1GHI456JKL789
VERDICT: NEED_MORE_INFO
REASON: PriceClass_All in the distribution config with no viewer
  geography data available (CloudFront access logging disabled,
  analytics integration pending). Cache, origin, and compression
  dimensions have optimization opportunities; price class dimension
  deferred until viewer geography is confirmed.
RECOMMENDATION:
  Current: PriceClass=All, origin=Custom (ALB), cache=CachingDisabled,
    compress=false, edge_compute=Lambda@Edge, security=WAF 10 rules
  Proposed: partial (price class pending)
    - Cache policy: enable for static paths (CachingOptimized for
      *.css, *.js, *.png; CachingDisabled only for /api/*)
    - Compress: enable on all static paths
    - Edge compute: migrate header logic to Functions (after runtime
      check)
    - Security: consolidate 10 rules to 5 (drop unused rules)
    - Price Class: NEED_MORE_INFO — see MIGRATION_STEPS
  Confidence: MEDIUM — partial data; price class is the largest
    potential saving and is the one dimension blocked.
ESTIMATED_SAVINGS:
  Monthly (cache + compress + edge + security): $510
  Monthly (price class): pending — up to $1,200 if PriceClass_100
    applies (4TB APAC-tier egress)
  Annual total: $6,120 confirmed + up to $14,400 pending price class
MIGRATION_STEPS:
  1. Enable CloudFront standard logging OR integrate CloudFront
     real-time logs to Kinesis Firehose → S3 → Athena.
     aws cloudfront update-distribution --id E1GHI456JKL789 \
       --if-match <ETag> --distribution-config <config-with-logging>
  2. Wait 7-14 days for representative viewer-geography sample.
  3. Athena query to get top viewer regions:
     SELECT regexp_extract(c_edge_location, '^([A-Z]+)-', 1) AS region,
            count(*) AS requests
     FROM cloudfront_logs
     WHERE date >= date_add('day', -14, now())
     GROUP BY 1 ORDER BY 2 DESC;
  4. If ≥ 95% US/EU, re-evaluate Price Class → PriceClass_100.
  5. Apply the other 4 dimensions (cache, compress, edge, security)
     in parallel — they do not depend on viewer geography.
CONFIRM: Apply the 4 confirmed dimensions only after operator
  approval. Do NOT change Price Class without viewer-geography data.
```

## Verdict semantics — reconciling the verdict_shape

The `verdict_shape` declares three primary verdicts (`OPTIMIZED |
OPPORTUNITY_FOUND | ALREADY_OPTIMAL`). The `NEED_MORE_INFO` verdict
is a pre-decision guard that appears when a specific dimension
cannot be evaluated.

| Verdict | When to emit | Position in workflow |
|---|---|---|
| `OPPORTUNITY_FOUND` | At least one of the nine dimensions has a concrete, savings-bearing recommendation. | Primary — terminal for actionable findings. |
| `OPTIMIZED` | A change was applied and verified this session; metrics confirm the new config lands within target bands (cache hit > 90%, compression working). | Primary — only emitted post-remediation. |
| `ALREADY_OPTIMAL` | All nine dimensions at cost-optimal config AND Security Savings Bundle evaluated (whether adopted or rejected with rationale). | Primary — terminal for healthy findings. |
| `NEED_MORE_INFO` | Data gate failed for one or more dimensions: viewer geography unknown for Price Class, metrics absent for cache/origin, WAF/Shield state indeterminate. | Pre-decision — emit per-dimension; the other dimensions can still emit OPPORTUNITY_FOUND. |

**Rule:** a partial NEED_MORE_INFO for one dimension does NOT block
OPPORTUNITY_FOUND on the other dimensions. Surface both — the
operator can apply the confirmed dimensions while collecting data
for the deferred one.

## Cache-hit-ratio improvement targets (concrete formula)

D7 references "target > 90% for static content" without defining the
ceiling. Use this framework to set per-content-type targets:

```
target_hit_ratio =
  (cacheable_requests) / (total_requests)
where cacheable_requests =
  total_requests − dynamic_requests − signed_url_requests

actual_hit_ratio =
  CacheHitRate metric over 30-day window

gap = target − actual
savings_from_closing_gap =
  gap × total_requests × origin_request_cost_per_unit +
  gap × total_bytes × origin_egress_cost_per_GB
```

| Content profile | Target hit ratio | Why |
|---|---|---|
| Static assets (CSS/JS/images/video) | > 90% | Highly cacheable; if lower, cache key is the issue. |
| HTML pages (weekly update) | > 80% | Cacheable for hours; misses indicate TTL too short. |
| API JSON responses | 0-50% | Most are dynamic; cached only when explicitly cacheable. |
| SPA with SSR | 50-70% | HTML dynamic, assets static; split behaviors. |
| E-commerce product pages | 70-85% | Mostly static, some personalization; tune per path. |
| Live video (HLS/DASH) | > 95% | Segments highly cacheable; manifest may be dynamic. |

## Error handling — CLI and data-source failures

The workflow depends on three live data sources (CloudFront config,
CloudWatch metrics, Cost Explorer). Each can fail independently.

### CloudFront config API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-distribution-config` returns `NoSuchResource` | API error | Distribution ID is wrong or distribution is deleted. Verify with `list-distributions`. Emit BLOCKED with corrected ID suggestion. |
| `Distribution.Status == InProgress` | Status field | Distribution is mid-deploy. Wait 5-15 minutes, retry. Emit BLOCKED if still InProgress after 30 minutes. |
| `ETag` mismatch on `update-distribution` | API error | Another change happened between your get and update. Re-pull config, re-apply your diff, retry. |
| `TooManyDistributionVersions` error on update | API error | CloudFront limits version history. No remediation needed; wait for old versions to age out. |
| `InvalidIfMatchVersion` | API error | Stale ETag. Same handling as above. |

### CloudWatch metric failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-metric-statistics` returns empty `Datapoints` for CacheHitRate | `len(Datapoints) == 0` | Distribution is < 24h old, or disabled. Emit NEED_MORE_INFO. |
| `SampleCount` < window_days × 24 (less than 1h granularity) | Datapoints sparse | Distribution had gaps in traffic. Re-pull with wider window. |
| CloudFront namespace not returning any metrics | `list-metrics` returns no CloudFront metrics | Distribution may not have the `AWS/CloudFront` namespace enabled (rare; CloudFront always emits to this namespace). Check region — CloudFront metrics are in `us-east-1` only. |
| CloudWatch API throttling | `Throttling` error | Retry with exponential backoff. If persistent, reduce period to 3600s. |

### Cost Explorer failures

| Failure mode | Detection | Handling |
|---|---|---|
| `AccessDeniedException` for `ce:GetCostAndUsage` | Exit code non-zero | The role lacks billing permissions. Proceed without CE; flag the gap. The operator can grant `ce:GetCostAndUsage` and re-run. |
| CE returns no CloudFront line items | Empty Results | Account has no CloudFront usage in the window, OR the Cost Explorer API is filtering by linked account. Check `--filter` for linked-account scope. |
| CE usage amounts disagree with CloudFront metrics | Cross-source mismatch | Trust CE for billing, CloudFront metrics for operations. The delta is typically free tier, taxes, or WAF charges bundled under CloudFront. |

### WAF and Shield API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `wafv2 list-web-acls` returns empty | Empty WebACLs | Either no WAF in use, or WAF Classic (different API). Check `waf-regional` namespace for WAF Classic. |
| `wafv2 list-web-acls` returns ACLs but none associated with CloudFront | All scopes are REGIONAL | WAF is protecting ALB/API Gateway, not CloudFront. The distribution has no WAF. |
| `shield list-protections` returns empty | Empty Protections | No Shield Advanced in use. Treat security dimension as ALREADY_OPTIMAL. |
| `AccessDeniedException` for `shield:ListProtections` | Exit code non-zero | Role lacks Shield permissions. Surface in output; do not block. |

### Aggregate behavior

If ANY data source fails with a transient error (throttling,
network), retry up to 3 times with exponential backoff before
treating that dimension as NEED_MORE_INFO. For persistent failures
(IAM denial, missing distribution), emit the appropriate gating
verdict for that dimension and proceed with the remaining
dimensions — do not abort the entire evaluation on a single source
failure.

## Anti-Patterns — NEVER do these things

- NEVER recommend `PriceClass_100` without confirming viewer
  geography. APAC/South-America-only viewers will see significantly
  higher latency routed through US/EU edges. The 20-40% savings is
  not justified if it breaks the viewer experience for ≥ 5% of
  traffic.

- NEVER recommend `PriceClass_100` for a live-video streaming
  workload with global viewers. Latency-sensitive streaming requires
  edge proximity; the savings from Price Class cannot offset viewer
  churn from buffering.

- NEVER recommend enabling Origin Shield on an S3 origin with low
  request count (< 10M/month) without doing the break-even math.
  Shield's $0.0125/GB exceeds the S3 GET savings on
  low-request-volume distributions. Shield is a high-volume
  optimization.

- NEVER recommend migrating a Lambda@Edge function to CloudFront
  Functions without measuring actual runtime. Functions have a 1ms
  wall-clock limit. A 5ms Lambda@Edge function migrates to Functions
  by truncating — the function will fail silently or error out.

- NEVER recommend dropping Shield Advanced without confirming the
  workload is not DDoS-prone. Public-facing commerce, gaming,
  finance, and election-period government sites are DDoS targets;
  the $3,000/month is insurance against a multi-million-dollar
  outage.

- NEVER recommend dropping WAF rules without checking CloudWatch
  metrics for the rule. A rule with 0 blocks over 30 days is unused;
  a rule with 1M blocks is actively protecting. Removing an active
  rule opens a security hole.

- NEVER recommend a single Price Class for a multi-tenant SaaS
  workload without consulting per-tenant viewer geography. Tenant A
  may be US-only; Tenant B may be APAC-majority. Per-tenant
  distributions may be needed (multi-distribution architecture).

- NEVER recommend changing multiple dimensions in a single deploy.
  CloudFront updates are atomic per-deploy, but isolating impact
  requires one dimension per deploy. A stacked deploy that produces
  a cache-hit drop cannot be triaged ("was it the price class, the
  cache policy, or the compression?").

- NEVER trust `get-distribution-config`'s `LastModifiedTime` as a
  proxy for "config is current." An operator may have applied a
  no-op change yesterday that bumped LastModifiedTime without
  changing the optimization-relevant fields. Always diff against
  the actual config values.

- NEVER assume CloudFront access logging is enabled. Many
  distributions are deployed without logging. Without logs, viewer
  geography, error breakdowns, and per-edge cache-hit rates are
  invisible. Always check `DistributionConfig.Logging.Enabled`.

- NEVER recommend Origin Shield on a distribution where the origin
  is in a different region from viewers AND cross-region transfer
  exceeds $0.05/GB. Origin Shield adds a hop; in some
  cross-region topologies it costs more than it saves.

- NEVER recommend Brotli compression on responses that are already
  Brotli-compressed at the origin. Double-compression is wasteful
  and can corrupt the response. Check origin response headers for
  `Content-Encoding: br` before enabling Brotli on the distribution.

- NEVER recommend a CloudFront Security Savings Bundle commitment
  beyond the steady-state CloudFront + WAF spend. The commitment is
  a 1-year lock; committing above steady-state leaves you paying
  for unused discount.

- NEVER recommend migrating a custom origin to S3 without verifying
  the content is genuinely static. Dynamic responses (HTML with
  per-user personalization) cannot be served from S3 without
  pre-generation. A "static" path that includes session-specific
  content will break when moved to S3.

- NEVER assume the AWS-managed `CachingOptimized` cache policy is
  optimal for all static content. It sets TTL=31536000 (1 year);
  content that changes weekly will be stale for up to a year unless
  invalidated. Use a custom policy with shorter TTL OR add
  invalidation hooks to the deploy pipeline.

- NEVER recommend Lambda@Edge for sub-1ms logic that could run as
  a CloudFront Function. The 40x cost differential is significant
  at high invocation counts. Always check the runtime profile
  before choosing Lambda@Edge.

- NEVER recommend enabling compression on SSE / streaming responses.
  Compression breaks the chunk-transfer semantics and causes viewer-
  side buffering failures. Compression is for finite-size responses
  only.

- NEVER skip the post-deploy validation step. CloudFront config
  changes are eventually-consistent; CacheHitRate and Requests
  metrics take 5-15 minutes to reflect the new config. Verify
  with `get-distribution --query 'Distribution.Status'` and
  CloudWatch before declaring the optimization complete.

- NEVER recommend the CloudFront Security Savings Bundle without
  modeling the breakage cost. The bundle is a 1-year commit; if
  traffic drops (e.g., seasonal site), the commit is still owed.

## Quick navigation

| You want to... | Jump to |
|---|---|
| Decide Price Class | Step 4 — Price Class optimization |
| Diagnose low cache hit ratio | Step 5 — Cache hit ratio optimization |
| Decide S3 origin vs custom origin | Step 6 — Origin optimization |
| Decide whether to enable compression | Step 7 — Compression optimization |
| Decide whether Origin Shield is worth it | Step 8 — Origin Shield optimization |
| Decide Lambda@Edge vs CloudFront Functions | Step 9 — Edge compute optimization |
| Decide whether to keep Shield Advanced | Step 10 — Security cost optimization |
| Build the savings projection | Step 11 — Impact estimation |
| Handle missing data | Step 1 — Validate input and data sufficiency |
| Handle API errors | Error handling section |

## Expert heuristic — the 60-second triage

When handed a CloudFront bill and asked "why is this so high?", run
this 60-second triage before deep-diving any single dimension:

1. **Pull the distribution config.** `PriceClass_All` + custom
   origin + compression off = three immediate opportunities.
2. **Pull CacheHitRate.** < 75% on static content = cache policy
   issue (likely cache-key fragmentation from cookies/headers/
   query strings).
3. **Pull Cost Explorer USAGE_TYPE breakdown.** APAC-tier (`-TF-`)
   charges > 5% = either APAC viewers or PriceClass_All mismatch.
4. **Check Lambda@Edge associations.** > 0 viewer-request
   associations for header manipulation = migration candidate.
5. **Check Shield Advanced.** Shield on a non-DDoS-prone workload
   = $3K/month savings.
6. **Check WAF rule count.** > 15 rules on < 100M req/month =
   consolidation candidate.

If any of the six checks hits, deep-dive the corresponding step.
If all six pass, the distribution is likely ALREADY_OPTIMAL —
verify with the full ordered process.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`update-distribution`, `create-cache-policy`,
  `delete-protection`, `create-savings-plan`), emit and await
  operator approval. Do NOT execute the CLI until the operator
  confirms.

- **Snapshot before optimization.** Capture the current config:
  `aws cloudfront get-distribution-config --id <id> --output json
  > backup-pre-optimization-$(date +%s).json`. This provides a
  rollback path if the new config produces cache-hit drops or 5xx.

- **One dimension per deploy.** CloudFront distributions are
  eventually-consistent; each update takes 5-15 minutes to deploy.
  Stacking multiple dimension changes in a single update obscures
  which change produced any observed impact. Deploy dimensions
  sequentially with 24-48h monitoring between each.

- **Verify distribution Status returns to Deployed.** After each
  update:
  `aws cloudfront get-distribution --id <id> --query
  'Distribution.Status'`. Status transitions: Deployed → InProgress
  → Deployed. Do not issue the next update until Status is Deployed.

- **Bulk-operation safety limit.** Optimization across a fleet of
  distributions MUST follow this algorithm:
  1. Sort flagged distributions by estimated savings (largest first).
  2. Slice into batches of at most 3 distributions.
  3. For each batch: emit per-distribution MIGRATION_STEPS, then a
     single CONFIRM for the batch.
  4. After the operator confirms and the CLI runs, re-query with
     `get-distribution` and verify Status == Deployed before
     emitting the NEXT batch.
  5. Abort the sweep if any distribution shows 5xx increase or
     CacheHitRate drop > 10% post-change.
  The skill MUST NOT emit remediation CLI for more than 3
  distributions in a single output block.

- **Cache invalidation is a separate cost.** If the optimization
  changes the cache policy, existing cache entries may be stale.
  Invalidation via `aws cloudfront create-invalidation` costs
  $0.005 per path after the first 1,000 paths/month free tier.
  Surface invalidation cost in the savings estimate.

- **Lambda@Edge replica deletion is slow.** Disassociating a
  Lambda@Edge function from a distribution does not immediately
  delete the replicas in edge regions. Replicas take 1-24 hours to
  delete. During that window, CloudWatch logs continue to show
  invocations from residual replicas. Surface this in the
  verification step.

## Remediation guidance

### For OPPORTUNITY_FOUND — Price Class

```bash
# Snapshot current config
aws cloudfront get-distribution-config --id $DIST_ID --output json \
  > backup-$(date +%s).json

# Update PriceClass
aws cloudfront update-distribution --id $DIST_ID \
  --if-match <ETag> \
  --distribution-config <updated-json-with-PriceClass_100>

# Verify deploy
aws cloudfront get-distribution --id $DIST_ID \
  --query 'Distribution.Status'
```

### For OPPORTUNITY_FOUND — Cache policy

```bash
# Create a new cache policy with tightened cache key
aws cloudfront create-cache-policy --cache-policy-config '{
  "Name":"optimized-static-v1",
  "Comment":"UTMs excluded; minimal cache key",
  "DefaultTTL":86400,
  "MaxTTL":31536000,
  "MinTTL":0,
  "ParametersInCacheKeyAndForwardedToOrigin":{
    "EnableAcceptEncodingGzip":true,
    "EnableAcceptEncodingBrotli":true,
    "HeadersConfig":{"HeaderBehavior":"none"},
    "CookiesConfig":{"CookieBehavior":"none"},
    "QueryStringsConfig":{
      "QueryStringBehavior":"allExcept",
      "QueryStringNames":{"Items":["utm_source","utm_medium",
        "utm_campaign","utm_term","utm_content"]}
    }
  }
}' --query 'CachePolicy.Id' --output text

# Update distribution to use the new policy ID on the default behavior
aws cloudfront update-distribution --id $DIST_ID --if-match <ETag> \
  --distribution-config <updated-json-with-new-CachePolicyId>
```

### For OPPORTUNITY_FOUND — Compression

```bash
# Just flip the Compress flag
# Update the DefaultCacheBehavior.Compress to true in the config JSON,
# then update-distribution.
```

### For OPPORTUNITY_FOUND — Origin (migrate custom to S3)

```bash
# Sync static files to S3
aws s3 sync /var/www/static s3://static-bucket/ --delete

# Create Origin Access Control
OAC_ID=$(aws cloudfront create-origin-access-control \
  --origin-access-control-config '{
    "Name":"static-bucket-OAC",
    "Description":"OAC for static-bucket",
    "SigningProtocol":"sigv4",
    "SigningBehavior":"always",
    "OriginAccessControlOriginType":"s3"
  }' --query 'OriginAccessControl.Id' --output text)

# Add S3 bucket policy granting CloudFront OAC access
# (see AWS docs for the canonical bucket policy)

# Update distribution: add S3 origin + path behavior for /static/*
```

### For OPPORTUNITY_FOUND — Origin Shield

```bash
# Add OriginShield to the origin in the distribution config
# OriginShield requires a region selection
# Update the Origins.Items[].OriginShield field:
#   { "Enabled": true, "OriginShieldRegion": "us-east-1" }
aws cloudfront update-distribution --id $DIST_ID \
  --if-match <ETag> \
  --distribution-config <config-with-OriginShield-enabled>
```

### For OPPORTUNITY_FOUND — Edge compute migration

```bash
# Test the rewritten CloudFront Function
aws cloudfront test-function \
  --if-match <ETag> \
  --stage DEVELOPMENT \
  --event-object fileb://test-event.json \
  --name <function-name>

# Publish the function
aws cloudfront publish-function --name <function-name> \
  --if-match <ETag>

# Associate with the cache behavior; disassociate Lambda@Edge
```

### For OPPORTUNITY_FOUND — Security cost

```bash
# Drop Shield Advanced (after confirming SRT not needed)
aws shield delete-protection --protection-id <id>

# Consolidate WAF rules (delete unused rules)
aws wafv2 update-web-acl --scope CLOUDFRONT --region us-east-1 \
  --web-acl-id <id> \
  --name <name> \
  --default-action <action> \
  --rules <consolidated-rule-list>
```

### For ALREADY_OPTIMAL or OPTIMIZED

1. No remediation required for the current posture.
2. Recommend quarterly review of CloudFront metrics and Cost
   Explorer breakdown — workloads drift.
3. For Security Savings Bundle renewals, re-evaluate at the renewal
   date for any CloudFront usage pattern changes.

## Deep reference: CloudFront pricing and limit cheat sheet

### Price Class pricing tiers (us-east-1 baseline, 2026)

| Price Class | Regions covered | HTTPS req (first 10T) | Egress (first 10TB) |
|---|---|---|---|
| PriceClass_100 | US, Canada, Europe | $0.225/M | $0.085/GB |
| PriceClass_200 | + India, Middle East, Africa | $0.270/M | $0.120/GB |
| PriceClass_All | + South America, Australia, APAC | $0.285/M (US/EU) / $0.330/M (APAC) | $0.140/GB (APAC) |

Pricing is billed at the edge location that SERVES the request. A
PriceClass_All distribution with APAC viewers pays APAC rates on
those requests; the same distribution with PriceClass_100 serves
those viewers from US/EU edges at US/EU rates (with higher latency).

### CloudFront quota reference (2026)

| Quota | Default | Adjustability |
|---|---|---|
| Distributions per account | 200 | Soft (request increase) |
| Cache behaviors per distribution | 25 | Soft |
| Origins per distribution | 50 | Soft |
| Cache policies per account | 20 | Hard |
| Origin request policies per account | 20 | Hard |
| CloudFront Functions per account | 100 | Soft |
| Lambda@Edge function associations per distribution | 100 (across all 4 event types) | Hard |
| Origin Shield regions | 1 per distribution | Hard (pick one) |
| WAF Web ACLs per account (CLOUDFRONT scope) | 50 | Soft |

### Lambda@Edge vs CloudFront Functions decision matrix

| Capability | CloudFront Functions | Lambda@Edge |
|---|---|---|
| Runtime | JavaScript subset | Node.js, Python |
| Memory | 2 MB | 128 MB default, up to 10 GB |
| Wall-clock limit | 1 ms | 5-30 seconds (varies by event type) |
| External HTTP calls | No | Yes |
| File system access | No | Yes (/tmp) |
| Execution location | CloudFront edge (100+ locations) | Regional edge cache (sub-set of edges) |
| Pricing | $1.00/M invocations (flat) | $0.60/M invocations + $0.0000166667 per GB-second |
| Use cases | Header manipulation, URL rewrites, token generation, simple auth, A/B routing | SSR, complex auth with external API, response generation, large data transforms |
| Migration effort (from Lambda@Edge) | Rewrite in JS subset, re-test | n/a |

## Recent AWS features (2024-2026)

- **CloudFront Security Savings Bundle (2022, broadened 2024):**
  1-yr commit gives 30% discount on CloudFront + WAF spend. Always
  evaluate as part of security-cost optimization (Step 10).
- **Origin Access Control (OAC, 2022):** Replaces OAI for S3 origins.
  Supports SSE-KMS. New distributions should use OAC; existing OAI
  should migrate during optimization reviews.
- **CloudFront KeyValueStore (2023-2024):** Key-value store for
  CloudFront Functions, allowing read-time data lookup without
  external HTTP. Reduces Lambda@Edge dependency for some auth and
  routing patterns.
- **CloudFront continuous deployment (2023-2024):** Test config
  changes on a traffic slice before full deploy. Use for
  high-confidence optimizations on production distributions.
- **Brotli compression (2019, broadened 2023+):** Now enabled by
  default in new distributions. Older distributions may have
  gzip-only or compression disabled — check during optimization.
- **S3 Multi-Region Access Point (2022) + CloudFront (2023-2024):**
  CloudFront origin can be an S3 MRAP, routing each edge to the
  nearest S3 bucket. Use for global workloads with high origin
  egress.
- **CloudFront metrics in CloudWatch Embedded Metrics Format (2024):**
  Higher-resolution metrics for low-traffic distributions. Reduces
  the "insufficient data" gate.
- **VPC origins for CloudFront (2024-2025):** CloudFront can now
  originate from private VPC resources (ALB in private subnet)
  without internet exposure. Cost-neutral but enables origin
  patterns not previously possible.

## Domain

AWS CloudOps / CloudFront CDN Cost Optimization, FinOps & Edge.

## AWS documentation

- **Amazon CloudFront Developer Guide** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html
- **CloudFront pricing** — https://aws.amazon.com/cloudfront/pricing/
- **CloudFront Functions** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudfront-functions.html
- **Lambda@Edge** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-at-the-edge.html
- **Origin Shield** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/origin-shield.html
- **Origin Access Control** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html
- **AWS WAF + CloudFront** — https://docs.aws.amazon.com/waf/latest/developerguide/cloudfront-features.html
- **AWS Shield** — https://docs.aws.amazon.com/waf/latest/developerguide/shield-chapter.html
- **CloudFront Security Savings Bundle** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/security-savings-bundle.html
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
