# Advanced Patterns (load on demand) — CloudFront Cost Optimizer

Expert knowledge and deep dives moved verbatim from SKILL.md: philosophy, Step 0 gotchas, the Step 1-11 decision matrices/probes/worked math, hit-ratio targets, the 60-second triage, and recent AWS features.


---

## Philosophy — four separating behaviours (moved from SKILL.md)

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


---

## Step 0: Non-obvious behaviours that change the recommendation (moved from SKILL.md)

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


---

## Process step deep dives (moved from SKILL.md)

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


---

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


---

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


---

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


---

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


---

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


---

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


---

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


---

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


---

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


---

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


---

## Cache-hit-ratio improvement targets — concrete formula (moved from SKILL.md)

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


---

## Expert heuristic — the 60-second triage (moved from SKILL.md)

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


---

## Recent AWS features (2024-2026) (moved from SKILL.md)

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
