---
description: Optimize CloudFront distribution costs — applies the nine-dimension optimization logic (Price Class, cache hit ratio, origin, compression, Origin Shield, edge compute, security) with per-dimension savings estimates and staged one-dimension-per-deploy remediation.
nl_triggers:
  - "optimize CloudFront cost"
  - "CloudFront monthly bill"
  - "PriceClass recommendation"
  - "CloudFront cache hit ratio"
  - "Origin Shield break-even"
  - "CloudFront Functions vs Lambda@Edge"
  - "S3 origin vs custom origin cost"
  - "CloudFront data transfer cost"
  - "CloudFront WAF cost"
  - "CDN cost optimization"
  - "reduce CloudFront bill"
  - "Brotli compression CloudFront"
  - "CloudFront PriceClass_All"
  - "cache policy TTL optimization"
  - "FinOps CDN review"
  - "CloudFront Shield Advanced cost"
  - "CloudFront Security Savings Bundle"
routes_to: cloudfront-cost-optimizer
---

# /aws:optimize-cloudfront-cost

Activate the `cloudfront-cost-optimizer` skill and optimize a
CloudFront distribution across the nine cost dimensions.

## What it does

Reads a distribution's config (origins, behaviors, Price Class,
Lambda@Edge/Functions, WAF/Shield) plus 14-30 day CloudFront metrics
(CacheHitRate, Requests, BytesDownloaded, OriginLatency) and
optional Cost Explorer breakdown, then applies the ordered
optimization logic:

1. **Pre-flight** — data sufficiency gate. If viewer geography is
   unknown for Price Class, emits NEED_MORE_INFO for that dimension
   only.
2. **Price Class** — `PriceClass_All` with ≥ 95% US/EU viewers →
   switch to `PriceClass_100` (20-40% savings).
3. **Cache hit ratio** — target > 90% for static content; diagnose
   cache-key fragmenters (cookies, headers, query strings).
4. **Origin** — S3 origin + OAC is cheapest (free origin egress);
   custom origins behind ALB/EC2 pay $0.02/GB same-region.
5. **Compression** — enable Brotli + gzip on text content (50-90%
   byte savings, free feature).
6. **Origin Shield** — $0.0125/GB but cuts origin load 95%+ when
   multiple edges fetch the same objects.
7. **Edge compute** — CloudFront Functions ($1/M, sub-1ms) vs
   Lambda@Edge ($0.60/M + compute time, full runtime).
8. **Security cost** — WAF ($5/rule/month + $1/M requests), Shield
   Standard (free), Shield Advanced ($3,000/month — only for
   DDoS-prone workloads).
9. **Security Savings Bundle** — 1-yr commit, 30% discount on
   CloudFront + WAF spend.
10. **Impact estimation** — per-dimension monthly savings summed
    into a projected bill.
11. **Verdict** — OPPORTUNITY_FOUND (any dimension has a
    recommendation), OPTIMIZED (post-remediation), or
    ALREADY_OPTIMAL.

Emits a deterministic optimization block per distribution:

```text
TARGET: <distribution-id>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: PriceClass=<class>, origin=<type>, cache=<policy>, ...
  Proposed: <per-dimension list of changes>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly (price class): $<amount>
  Monthly (cache policy): $<amount>
  ...
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a distribution's config and metrics and ask any of:

- "why is my CloudFront bill so high?"
- "should I switch Price Class?"
- "is my cache hit ratio good?"
- "should I use CloudFront Functions or Lambda@Edge?"
- "is Origin Shield worth it?"
- "should I keep Shield Advanced?"
- "CloudFront FinOps review"

A bare distribution ID + any optimization verb ("optimize this CDN",
"cost review") also routes here via the orchestrator.

## Inputs

- Distribution metadata: ID, region, current Price Class, origins
  (S3/custom), cache behaviors, Lambda@Edge/Functions associations.
- Metrics (last 14-30 days): CacheHitRate, Requests,
  BytesDownloaded, OriginLatency.
- Optional: CloudFront access logs (for viewer geography), Cost
  Explorer breakdown (USAGE_TYPE granularity), WAF/Shield state.
- Optional: workload context (content type, viewer geography,
  DDoS-risk profile) for Security Savings Bundle and Shield
  Advanced decisions.

## Outputs

- One optimization block per distribution.
- Per-dimension confidence with rationale.
- Per-dimension estimated monthly savings and annual total.
- Staged one-dimension-per-deploy migration plan with CLI commands.
- Rollback path (pre-optimization config snapshot).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill
  is the Phase 3 Optimize specialist for CloudFront cost).
- `/aws:audit-cloudfront-distribution` to audit the distribution's
  security posture (OAC, IAM, TLS) before cost optimization.
- `/aws:troubleshoot-cloudfront-cache` to diagnose a cache-miss
  root cause before optimizing the cache policy.
- `/aws:optimize-data-transfer` for non-CloudFront data-transfer
  optimization (cross-AZ, cross-region, NAT Gateway).
