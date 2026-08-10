# CloudFront Pricing & Cost-Decision Reference

Supplementary reference for the CloudFront Cost Optimizer skill. Loaded
on-demand when the optimizer needs the detailed pricing matrix,
Origin Shield break-even math, Lambda@Edge vs CloudFront Functions
cost comparison, or WAF/Shield pricing detail.

## Price Class pricing matrix (us-east-1 baseline, 2026)

CloudFront bills at the edge location that SERVES the request. The
Price Class controls which edge locations are eligible; the per-
request and per-GB rates follow the edge region.

### HTTPS request pricing (per million)

| Price Class | Edge region | First 10T req/month | 10-50T | 50-100T | > 100T |
|---|---|---|---|---|---|
| PriceClass_100 | US, Canada, Europe | $0.225 | $0.180 | $0.160 | $0.120 |
| PriceClass_200 | + India, MEA | $0.270 | $0.220 | $0.200 | $0.150 |
| PriceClass_All | + SAM, AU, APAC | $0.285 (US/EU) / $0.330 (APAC) | varies | varies | varies |

### Egress pricing (per GB, CloudFront-to-viewer)

| Price Class | Edge region | First 10TB | 10-50TB | 50-150TB | > 150TB |
|---|---|---|---|---|---|
| PriceClass_100 | US, Canada, Europe | $0.085 | $0.070 | $0.060 | $0.040 |
| PriceClass_200 | + India, MEA | $0.120 | $0.100 | $0.080 | $0.060 |
| PriceClass_All | + SAM, AU, APAC | $0.140 (APAC) / $0.085 (US/EU) | varies | varies | varies |

### Worked Price Class migration example

Distribution with 800M requests/month and 4.8TB egress/month, viewers
98% US/EU. Currently `PriceClass_All`.

- Current (PriceClass_All, US/EU tier applied): 800 × $0.225 + 4800 × $0.085 = $180 + $408 = $588/month
- Wait — actually PriceClass_All bills at the edge that served; if
  98% US/EU edges served, the request tier is mostly US/EU rate.
  The 2% APAC viewers cost $0.285/M × 16M + $0.140/GB × 96GB =
  $4.56 + $13.44 = $18/month at APAC rates. The rest at US/EU:
  $0.225 × 784 + $0.085 × 4704 = $176.40 + $399.84 = $576.24.
  Total ~$594.24/month.
- Switched to PriceClass_100: APAC viewers now served from US/EU
  edges at US/EU rates. Total = 800 × $0.225 + 4800 × $0.085 =
  $180 + $408 = $588/month. The 16M APAC requests now pay US rate
  but incur higher latency (no APAC edge).
- Savings: $6.24/month on this distribution. **Price Class savings
  are small when viewer geography is already well-matched to the
  Price Class.** The big savings come when PriceClass_All is set
  with US-only viewers AND significant APAC-tier billing.

Recompute for a distribution with 30% APAC viewers, 4.8TB egress:

- Current (PriceClass_All): 30% APAC-tier = 240M × $0.330 + 1440GB
  × $0.140 = $79.20 + $201.60 = $280.80 APAC tier. 70% US/EU tier
  = 560M × $0.225 + 3360GB × $0.085 = $126 + $285.60 = $411.60.
  Total = $692.40/month.
- Switched to PriceClass_100: APAC viewers served from US edges.
  Total = 800 × $0.225 + 4800 × $0.085 = $588/month.
- Savings: $104.40/month (15% reduction). Latency increase for
  APAC viewers must be weighed.

## Origin Shield break-even math

Origin Shield is a regional intermediate cache between CloudFront
edges and the origin. It costs $0.0125/GB for bytes Shield sends to
origin (the Shield-to-edge transfer is bundled into the Shield
price). The benefit: edges fetch from Shield, Shield fetches from
origin. If N edges each fetch the same object, origin sees N
requests without Shield and 1 request with Shield.

```
Shield cost = $0.0125 × (Shield-to-origin GB)
Shield savings =
  (origin-egress-without-shield GB
   - origin-egress-with-shield GB)
  × origin-egress-rate
+ (origin-requests-without-shield
   - origin-requests-with-shield)
  × origin-request-rate
```

### Per-origin-type break-even thresholds

| Origin type | Origin egress rate | Origin request rate | Shield worth it? |
|---|---|---|---|
| S3 (free egress) | $0/GB | $0.0004 per 1,000 GET | Only if S3 GET savings > $0.0125/GB. Requires ~30M+ requests per GB served, i.e., very small objects. |
| ALB / EC2 same-region | $0.02/GB | (origin compute cost varies) | Almost always worth it if Shield reduces origin egress > 60%. |
| ALB / EC2 cross-region | $0.02-0.09/GB | (origin compute cost varies) | Always worth it; egress savings alone justify Shield. |
| API Gateway | $0.02/GB + per-request | API Gateway pricing | Worth it if origin requests > 1M/month. |
| MediaPackage / MediaStore | per-hour + per-GB streaming | n/a | Mandatory — origins cannot handle multi-edge fan-out. |

### Worked Shield example

Custom ALB origin in us-east-1. 50TB/month origin egress across
3 CloudFront edges (US-East, EU-West, APAC). Without Shield, each
edge fetches independently → 3 × origin-egress fan-out ≈ 50TB to
each edge = 150TB origin egress. With Shield, origin sees only
the unique objects: ~60TB (assuming 80% cache depth at Shield).
Origin egress savings: 90TB × $0.02/GB = $1,800/month. Shield cost:
$0.0125 × 60TB = $750/month. Net savings: $1,050/month.

## Lambda@Edge vs CloudFront Functions cost crossover

```
Lambda@Edge cost per million invocations =
  $0.60  (invocation charge)
  + (memory_GB × duration_seconds × $0.0000166667 × 1,000,000)
  = $0.60 + (memory_GB × duration_ms × 0.0166667)

CloudFront Functions cost per million invocations =
  $1.00 (flat)
```

### Crossover points (where Lambda@Edge = Functions)

| Runtime (duration) | Memory | Lambda@Edge per M | Functions per M | Cheaper option |
|---|---|---|---|---|
| 1 ms | 128 MB | $0.60 + $0.0021 = $0.60 | $1.00 | Lambda@Edge |
| 5 ms | 128 MB | $0.60 + $0.0107 = $0.61 | $1.00 | Lambda@Edge |
| 10 ms | 128 MB | $0.60 + $0.0213 = $0.62 | $1.00 | Lambda@Edge |
| 25 ms | 128 MB | $0.60 + $0.0533 = $0.65 | $1.00 | Lambda@Edge |
| 50 ms | 128 MB | $0.60 + $0.1067 = $0.71 | $1.00 | Lambda@Edge |
| 50 ms | 256 MB | $0.60 + $0.2133 = $0.81 | $1.00 | Lambda@Edge |
| 50 ms | 512 MB | $0.60 + $0.4267 = $1.03 | $1.00 | Functions |
| 100 ms | 128 MB | $0.60 + $0.2133 = $0.81 | $1.00 | Lambda@Edge |
| 100 ms | 256 MB | $0.60 + $0.4267 = $1.03 | $1.00 | Functions |
| 200 ms | 128 MB | $0.60 + $0.4267 = $1.03 | $1.00 | Functions |

The crossover depends on duration AND memory. The "40x cost
differential" rule of thumb applies at 500ms+ durations (typical
for full Node/Python startup with external calls). For sub-100ms
lightweight logic, Lambda@Edge may actually be cheaper per million
invocations.

### Non-cost considerations

- **Functions have a 1ms wall-clock limit.** Anything > 1ms cannot
  run as a Function, regardless of cost.
- **Functions support only a JavaScript subset.** No `require()`,
  no Node built-ins (fs, http). Only the ES language features and
  the CloudFront event object.
- **Functions run at every CloudFront edge (100+ locations).**
  Lambda@Edge runs at regional edge caches (a subset).
- **Functions do not support external HTTP calls** (except via
  KeyValueStore reads in 2024+).

## WAF + Shield pricing detail

### WAF pricing (per ACL, per month)

| Component | Price |
|---|---|
| Per Web ACL | $5.00/month |
| Per rule in the ACL | $1.00/month per rule (NOT per evaluation) |
| Per million requests evaluated | $0.60/month (was $1.00; reduced 2024) |

A WAF with 10 rules on 500M requests/month costs:
- Web ACL: $5
- Rules: 10 × $1 = $10
- Requests: 500 × $0.60 = $300
- Total: $315/month

### Shield Advanced pricing

| Component | Price |
|---|---|
| Monthly fee per protected resource | $3,000 |
| Protected resource types | CloudFront distribution, Route 53 hosted zone, Global Accelerator, ALB/NLB, Elastic IP |
| Data transfer (first 10TB) | $0.025/GB (overage above included) |
| DDoS cost-protection | Yes — credits for scaling charges during a DDoS attack |
| DDoS response team (SRT) access | Yes |

Shield Standard is free for all AWS accounts; covers common L3/L4
attacks. Shield Advanced adds application-layer (L7) protections,
SRT access, and cost-protection credits.

### When Shield Advanced is justified

| Workload profile | Recommendation |
|---|---|
| Public-facing commerce, gaming, finance | Yes — DDoS risk justifies the fee |
| Marketing site, internal-facing app | No — risk too low to justify |
| Election-period government site | Yes — politically motivated attacks likely |
| News site during breaking news | Maybe — viral traffic spike, may attract attacks |
| B2B SaaS with NDA-bound customers | No — typical B2B traffic is low DDoS risk |
| Multi-tenant SaaS with self-signup | Maybe — abusive signup patterns are common |

## CloudFront Security Savings Bundle math

The bundle is a 1-year commit to a monthly CloudFront + WAF spend
amount, in exchange for a ~30% discount on the committed portion.

```
committed_monthly_spend = $X
bundle_cost = $X × 0.70 (i.e., pay $0.70 on the dollar for committed amount)
uncommitted_usage = (actual - committed) × full rate
total_monthly = bundle_cost + uncommitted_usage
savings = actual - total_monthly = committed × 0.30
```

### Worked example

Steady-state CloudFront + WAF spend: $10,000/month.

- Without bundle: $10,000/month
- With bundle (commit $10,000): $10,000 × 0.70 = $7,000/month
  Savings: $3,000/month, $36,000/year

- With bundle (commit $8,000): $8,000 × 0.70 + $2,000 × 1.00 =
  $5,600 + $2,000 = $7,600/month. Savings: $2,400/month,
  $28,800/year.

Commit to the actual steady-state; do not commit above it (you
pay for unused discount).

## Cache hit ratio target framework

| Content profile | Target hit ratio | Reason |
|---|---|---|
| Static assets (CSS, JS, images, video) | > 90% | Highly cacheable; lower = cache key issue |
| HTML pages (weekly update) | > 80% | Cacheable for hours; lower = TTL too short |
| API JSON responses | 0-50% | Most dynamic; only cache when explicitly cacheable |
| SPA with SSR | 50-70% | HTML dynamic, assets static; split behaviors |
| E-commerce product pages | 70-85% | Mostly static, some personalization |
| Live video (HLS/DASH segments) | > 95% | Segments highly cacheable |
| Manifests (HLS .m3u8, DASH .mpd) | 0-30% | Often dynamic for ABR logic |

### Cache-key fragmenters (the hit-ratio killers)

| Element | Impact | Fix |
|---|---|---|
| `CookieBehavior=all` | Each unique cookie combination = separate cache entry. Session cookies fragment heavily. | Switch to `whitelist` with only the cookies that vary the response. |
| `HeaderBehavior=all` | Each unique header combination = separate cache entry. `User-Agent` is the #1 fragmenter. | Switch to `whitelist`. Whitelist at most `Accept`, `Accept-Encoding`, `Origin`. |
| `QueryStringBehavior=all` | Each unique query string = separate cache entry. UTMs are the #1 fragmenter. | Switch to `allExcept` for known-irrelevant params (UTMs), or `whitelist` for known-relevant. |
| `Forwarded headers from origin request policy` | Same as HeaderBehavior. | Review origin request policy separately from cache policy. |
| Signed URLs / signed cookies | Each signed URL is unique → 0% cache for that content. | Expected for protected content; cannot optimize without changing auth model. |

## CloudFront metric reference (CloudWatch)

| Metric | Namespace | Description | When to use |
|---|---|---|---|
| `Requests` | AWS/CloudFront | Total requests (all HTTP methods) | Volume baseline |
| `BytesDownloaded` | AWS/CloudFront | Bytes sent from CloudFront to viewers | Egress cost |
| `BytesUploaded` | AWS/CloudFront | Bytes received by CloudFront from viewers | Upload egress |
| `CacheHitRate` | AWS/CloudFront | Percentage of requests served from cache | Cache optimization |
| `OriginLatency` | AWS/CloudFront | Time from CloudFront request to origin response | Origin health |
| `TotalErrorRate` | AWS/CloudFront | 4xx + 5xx as percentage of requests | Error monitoring |
| `4xxErrorRate` | AWS/CloudFront | Client errors | Bad URLs, signed URL issues |
| `5xxErrorRate` | AWS/CloudFront | Origin/server errors | Origin health |
| `LambdaExecutionError` | AWS/CloudFront | Lambda@Edge exceptions | Edge compute health |
| `FunctionExecutionErrors` | AWS/CloudFront | CloudFront Function exceptions | Function health |

All CloudFront metrics are in `us-east-1` (global namespace) regardless
of distribution region. Period: 1 minute (high-resolution) or 1 hour
(rollup).

## AWS documentation cross-links

- CloudFront pricing: https://aws.amazon.com/cloudfront/pricing/
- CloudFront Functions pricing: https://aws.amazon.com/cloudfront/pricing/#CloudFront_Functions
- Lambda@Edge pricing: https://aws.amazon.com/cloudfront/pricing/#Lambda_Edge
- WAF pricing: https://aws.amazon.com/waf/pricing/
- Shield Advanced pricing: https://aws.amazon.com/shield/pricing/
- CloudFront Security Savings Bundle: https://aws.amazon.com/cloudfront/security-savings-bundle/
