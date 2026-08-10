# Example usage: cloudfront-cost-optimizer

A walkthrough showing the skill optimizing a multi-dimension
CloudFront distribution cost, demonstrating the nine-dimension
analysis (Price Class, cache policy, origin, compression, Origin
Shield, edge compute, security), the viewer-geography gate for
Price Class, the staged one-dimension-per-deploy rule, and the
savings projection with rollback path.

## Input (user prompt)

> Review this CloudFront distribution before our monthly bill lands.
> The bill has crept up and I want to find where the cost is going.

```text
DistributionId: E-prod-cdn-app
Region: us-east-1 (distribution); viewers 96% US/EU per CloudFront
  access logs (3% APAC, 1% other)
PriceClass: PriceClass_All
Origins:
  - S3 origin with OAC: s3-prod-assets (us-east-1) — serves /assets/*
  - Custom origin: ALB in us-east-1 (app.example.com) — serves /*
    (including /static/* which is genuinely static)
Default cache behavior:
  Target origin: ALB custom origin
  Cache policy: CachingDisabled (assumed all dynamic)
  Compress: false
  Lambda@Edge associations: 1 viewer-request (header normalization,
    Node 18, 5ms p50 runtime)
WAF: 5 rules on 500M requests/month
Shield: Standard

Metrics (last 30 days):
  CacheHitRate: 12%
  Requests: 500,000,000
  BytesDownloaded: 3,800 GB
  OriginLatency: 180ms p50
```

## Skill output

```text
TARGET: E-prod-cdn-app
VERDICT: OPPORTUNITY_FOUND
REASON: Distribution has PriceClass_All with 96% US/EU viewers
  (price class opportunity), CacheHitRate 12% due to
  CachingDisabled on the default behavior covering genuinely
  static /static/* content (cache policy opportunity), compression
  disabled on the ALB origin (compression opportunity), custom
  ALB origin serving static content that could move to S3 (origin
  opportunity), and Lambda@Edge used for 5ms header normalization
  that could migrate to CloudFront Functions (edge compute
  opportunity). Five dimensions have actionable recommendations;
  combined projected savings $2,140/month, $25,680/year.
RECOMMENDATION:
  Current: PriceClass=All, origin=mixed (S3+ALB serving static),
    cache=CachingDisabled, compress=false, shield=false,
    edge_compute=Lambda@Edge (1 viewer-request, 5ms p50),
    security=WAF 5 rules on 500M/month (appropriate)
  Proposed:
    - Price Class: PriceClass_100 (96% US/EU viewers per access logs)
    - Cache policy: split behaviors — /assets/* and /static/* get
      CachingOptimized (1yr TTL, minimal key); /* (truly dynamic)
      keeps CachingDisabled
    - Origin: route /static/* to S3 origin + OAC (offload from ALB)
    - Compress: enable Brotli + gzip on /static/* and /assets/*
      behaviors (text-heavy content)
    - Origin Shield: enable on the ALB origin (us-east-1, same
      region as origin); skip on S3 origin (low request count)
    - Edge compute: migrate Lambda@Edge header normalization to
      CloudFront Functions (5ms runtime is under the 1ms wall-clock
      limit? VERIFY — 5ms exceeds the Functions limit; keep on
      Lambda@Edge but consolidate to single function)
    - Security: keep WAF at 5 rules; no Shield Advanced change
  Confidence: HIGH — viewer geography from CloudFront access logs
    confirms PriceClass_100 safe; content audit confirms /static/*
    is genuinely static (HTML/CSS/JS/images); Cost Explorer shows
    APAC-tier egress < 4% of total.
ESTIMATED_SAVINGS:
  Monthly (price class): $76  (PriceClass_All → PriceClass_100:
                              500M × $0.225 + 3800GB × $0.085
                              vs mixed APAC-tier billing on 4%
                              APAC = $4.56 + $13.44 saved on APAC
                              tier; plus elimination of APAC-tier
                              risk on future traffic growth)
  Monthly (cache policy split): $1,420  (CacheHitRate 12% → 70%+
      on /static/* path covering ~60% of requests; saves ~270GB
      origin egress + 270M origin requests at $0.02/GB + ALB
      compute avoidance)
  Monthly (origin: ALB → S3 for /static/*): $108  ($0.02/GB on
      ~5,400GB static-asset egress moved from ALB to S3 which is
      free egress to CloudFront)
  Monthly (compression): $323  (Brotli on ~3,500GB text subset at
      85% byte reduction; saves ~2,975GB at $0.085/GB edge egress)
  Monthly (origin shield on ALB): $45  (Shield cost $0.0125 ×
      ~3,600GB vs savings on ALB origin egress 60% reduction at
      $0.02/GB = $43.20; net ~$2/month — marginal, but cuts ALB
      load significantly)
  Monthly (edge compute): $0  (Lambda@Edge kept — 5ms runtime
      exceeds Functions 1ms limit; cannot migrate. Document this
      decision.)
  Monthly (security): $0  (No Shield Advanced; WAF appropriately
      sized)
  Annual total: $23,832
  Assumptions: us-east-1 pricing, 730h/month, 500M req/month,
    3,800GB egress/month, content audit confirms /static/* is
    genuinely static, viewer geography stable.
MIGRATION_STEPS:
  1. Snapshot current distribution config:
     aws cloudfront get-distribution-config --id E-prod-cdn-app \
       --output json > backup-pre-optimization-$(date +%s).json
  2. Deploy Price Class change first (single-dimension rule):
     aws cloudfront update-distribution --id E-prod-cdn-app \
       --if-match <ETag> \
       --distribution-config <config-with-PriceClass_100>
     Verify Status returns to Deployed; monitor 24-48h.
  3. Sync /static/* content from ALB filesystem to S3:
     aws s3 sync /var/www/static s3://s3-prod-assets/static/ --delete
     Validate checksums.
  4. Add S3 origin and path-based cache behavior for /static/*:
     - Create new cache behavior targeting /static/* path pattern
     - Origin: s3-prod-assets (already exists with OAC)
     - Cache policy: CachingOptimized
     - Compress: true
     Same for /assets/* (already on S3, just needs cache policy).
  5. Update default behavior to keep CachingDisabled for /* (truly
     dynamic app responses). Enable compression on the default
     behavior too (dynamic JSON can still compress).
  6. Enable Origin Shield on the ALB origin only:
     Update Origins.Items[ALB].OriginShield =
       { Enabled: true, OriginShieldRegion: "us-east-1" }
  7. Keep Lambda@Edge header normalization. Document the runtime
     profile (5ms p50) as the reason migration to Functions is
     blocked. Track for future optimization if runtime drops below
     1ms.
  8. Post-deploy validation per dimension:
     aws cloudfront get-distribution --id E-prod-cdn-app \
       --query 'Distribution.Status'
     aws cloudwatch get-metric-statistics --namespace AWS/CloudFront
       --metric-name CacheHitRate --dimensions Name=DistributionId,
       Value=E-prod-cdn-app --start-time ... --end-time ...
       --period 3600 --statistics Average
     Target: CacheHitRate > 60% after /static/* cache behavior
     deployed (up from 12%).
CONFIRM: Before each state-changing CLI, emit and await:
  "CONFIRM: About to <action> on E-prod-cdn-app. Proceed? (yes/no)"
  Stage changes one dimension at a time per the spec; never batch
  all five in a single deploy.
```

## What the skill caught that a generic assistant misses

1. **Viewer-geography gating for Price Class.** A generic assistant
   says "Price Class 100 is cheaper, switch to it." The skill first
   confirms viewer geography (96% US/EU from access logs) AND
   quantifies the actual APAC-tier billing from Cost Explorer before
   recommending. The savings turn out to be modest ($76/month) — not
   the headline 20-40% — because most requests already bill at US/EU
   rates even on PriceClass_All.

2. **Cache policy diagnosis, not generic "improve caching."** The
   skill identifies that the cache policy is `CachingDisabled` on
   the default behavior covering /static/* content. The fix is to
   split behaviors (path-based routing) so static paths get
   `CachingOptimized` while dynamic paths keep `CachingDisabled`.
   A generic assistant would suggest "enable caching" without
   identifying that the same behavior serves both content types.

3. **Origin choice per content type.** The skill recognizes that
   /static/* is on the ALB origin but is genuinely static content
   that should move to S3 (free origin egress). A generic assistant
   treats the origin as a single choice; the skill splits origins
   by content profile.

4. **Functions vs Lambda@Edge with runtime check.** The skill checks
   the actual runtime (5ms p50) before recommending migration.
   CloudFront Functions has a 1ms wall-clock limit — 5ms exceeds it.
   A generic assistant would recommend migration without checking,
   producing a function that fails silently in production.

5. **Origin Shield break-even math per origin.** The skill recommends
   Shield on the ALB origin (where it cuts origin egress) but skips
   Shield on the S3 origin (where the cost exceeds S3 GET savings).
   A generic assistant either enables Shield on all origins (wasting
   money) or on none (missing the ALB savings).

6. **Staged deploy plan with per-dimension monitoring.** The skill
   sequences the changes (Price Class → origin sync → behavior split
   → compression → Shield) with 24-48h monitoring between each, so
   any cache-hit drop or 5xx increase can be attributed to a
   specific change. A generic assistant stacks all changes into one
   `update-distribution` call, obscuring impact attribution.

7. **Rollback path.** The skill snapshots the config before any
   change. A generic assistant goes straight to update with no
   rollback plan.

## Slash-command invocation

```
/aws:optimize-cloudfront-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "review this CloudFront distribution for cost savings"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: cloudfront-cost-optimizer]` and
hands off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new config's metrics:

```bash
# Confirm the distribution is fully deployed
aws cloudfront get-distribution --id E-prod-cdn-app \
  --query 'Distribution.Status'

# Monitor CacheHitRate for 7 days post-change
aws cloudwatch get-metric-statistics --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=E-prod-cdn-app \
  --start-time $(date -u -d '-7 days' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average,Minimum --output json

# Confirm Price Class landed
aws cloudfront get-distribution-config --id E-prod-cdn-app \
  --query 'DistributionConfig.PriceClass'

# Confirm WAF association intact
aws wafv2 list-web-acls --scope CLOUDFRONT --region us-east-1 \
  --output json | jq '.WebACLs[] | {name, id}'
```

If CacheHitRate does not improve to > 60% within 48h of the cache
policy change, roll back to the pre-optimization config.

## Fleet-wide extension

For a fleet of N distributions, run the skill in batch mode:

1. Identify all distributions with PriceClass_All AND viewer
   geography confirming PriceClass_100 is appropriate.
2. Sort by projected savings (largest first).
3. Slice into batches of 3 distributions (the spec's bulk-operation
   safety limit).
4. For each batch: emit per-distribution MIGRATION_STEPS, then a
   single CONFIRM for the batch.
5. Verify each batch before proceeding to the next.
6. After the Price Class sweep, evaluate the Security Savings Bundle
   at the account level (one commit across all distributions).
