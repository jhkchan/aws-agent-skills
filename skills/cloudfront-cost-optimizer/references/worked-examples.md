# Worked Examples (load on demand) — CloudFront Cost Optimizer

Secondary worked examples moved verbatim from SKILL.md: the ALREADY_OPTIMAL and NEED_MORE_INFO output examples.


---

## Worked example — already optimal (moved from SKILL.md)

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


---

## Worked example — NEED_MORE_INFO, viewer geography unknown (moved from SKILL.md)

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
