---
name: cloudfront-cost-optimizer
description: Optimizes CloudFront distribution costs across nine cost dimensions — Price Class (PriceClass_100 vs PriceClass_200 vs PriceClass_All, where PriceClass_100 saves 20-40% when viewers are US/EU-only), cache hit ratio (target >90% for static content via longer TTLs and minimal cache key), origin choice (S3 + OAC is cheapest; custom origins incur $0.02/GB egress), compression (free, 50-90% byte savings via Brotli/gzip), Origin Shield ($0.0125/GB, cuts origin load 95%+), CloudFront Functions ($1/M) vs Lambda@Edge ($0.60/M + compute), security cost (WAF $5/rule + $1/M req, Shield Standard free, Shield Advanced $3K/mo), data-transfer matrix, and impact estimation. Emits OPPORTUNITY_FOUND with per-dimension savings, OPTIMIZED, or ALREADY_OPTIMAL. Use when reviewing CloudFront bills, triaging data-transfer charges, choosing Functions vs Lambda@Edge, or evaluating Origin Shield break-even.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation-document classification works from pasted distribution config and CloudFront metrics. Live-account optimization uses aws cloudfront get-distribution-config, get-distribution-metrics, list-cache-policies, list-origin-request -policies, aws cloudwatch get-metric-statistics (CacheHitRate, Requests, BytesDownloaded, OriginLatency), aws wafv2 list-web-acls, aws ce get-cost-and-usage, and aws...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Optimizing CloudFront distribution costs, reviewing Price Class against viewer geography, raising cache hit ratio, choosing between S3 origin and custom origin, evaluating Origin Shield break-even, deciding between CloudFront Functions and Lambda@Edge, sizing the WAF rule budget, or building a monthly CloudFront cost projection.
  when_not_to_use: Troubleshooting a 5xx or cache-miss root cause (use cloudfront-cache-troubleshooter), auditing the distribution security posture (use cloudfront-distribution-auditor for OAC, field-level encryption, IAM), deploying a new distribution (use cloudfront-distribution-deployer), S3 bucket lifecycle optimization (use s3-lifecycle-optimizer), or EC2/ALB data-transfer optimization that does not involve CloudFront (use data-transfer-optimizer). This skill focuses on cost optimization of an existing CloudFront distribution, not on deployment, security audit, or generic data-transfer patterns.
  activation_triggers: optimize CloudFront cost, CloudFront monthly bill, PriceClass recommendation, CloudFront cache hit ratio, Origin Shield break-even, CloudFront Functions vs Lambda@Edge, S3 origin vs custom origin cost, CloudFront data transfer cost, CloudFront WAF cost, CDN cost optimization, reduce CloudFront bill, Brotli compression CloudFront, CloudFront PriceClass_All, cache policy TTL optimization, FinOps CDN review
  invocation_schema: 'Input: either (a) a distribution identifier + live-account context, (b) a pasted distribution configuration (origins, default_cache_behavior including price_class, viewer_protocol_policy, trusted_key_groups, lambda_function_associations, cache_policy_id, origin_request_policy_id), OR (c) aggregated CloudFront usage (monthly requests, GB transferred, edge regions, cache hit ratio). Output: a deterministic TARGET / VERDICT / REASON / RECOMMENDATION / ESTIMATED_SAVINGS / MIGRATION_STEPS block per distribution, where VERDICT ∈ {OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL} and RECOMMENDATION lists the per-dimension actions (price_class, cache_policy, origin, compression, origin_shield, edge_compute, security).'
  invocation_example: "# Minimal valid input (offline config classification):\nDistributionId: E1ABC23DEF456G\nRegion: us-east-1 (distribution); viewers primarily US + EU\nPriceClass: PriceClass_All\nOrigins:\n  - S3 origin with OAC: s3-prod-assets (us-east-1)\n  - Custom origin: ALB in us-east-1 (app.example.com)\nDefault cache behavior:\n  Target origin: ALB custom origin\n  Cache policy: CachingOptimized (TTL 31536000)\n  Origin request policy: AllViewerExceptInternal\n  Viewer protocol policy: redirect-to-https\n  Compress: false\n  Lambda@Edge associations: 1 viewer-request (Node 18, 50ms avg)\nCloudFront Functions associations: 0\nWAF: 5 rules, ~500M requests/month\nMetrics (last 30 days):\n  CacheHitRate: 62%\n  Requests: 800,000,000\n  BytesDownloaded: 4,800 GB\n  OriginLatency: 250ms p50\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudFront, CDN, Price Class, PriceClass_100, cache hit ratio, Origin Shield, Origin Access Control, OAC, compression, Brotli, gzip, CloudFront Functions, Lambda@Edge, WAF, Shield Advanced, data transfer, S3 origin, custom origin, cache policy, origin request policy, TTL, FinOps, edge computing
  tags: cloudfront, networking, cost-optimization, finops, cdn, edge
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

Senior FinOps philosophy (price class as geography, hit ratio as policy, origin as architecture, 40x edge-compute decision) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when justifying a recommendation's economics.

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

Required data-source pull commands (config, 30-day metrics, Cost Explorer, viewer geography) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Run them before any optimization decision; apply the data-quality short-circuits below.

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

Step 0 gotchas (edge-location billing, per-edge hit ratio, managed policy fit, OAC/OAI, Accept-Encoding, single-region Shield, association billing, 1ms limit, WAF/Shield billing, Savings Bundle, MRAP, config parse gates) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a recommendation routes away from the obvious choice.

### Step 1: Validate input and data sufficiency

Data-sufficiency gates and partial-verdict output templates moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Verdict: NEED_MORE_INFO when CacheHitRate samples are absent or viewer geography is unknown; the other dimensions still emit.

### Step 2: Cost Explorer reconciliation

Cost Explorer reconciliation command and USAGE_TYPE decode table moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Signal: `-TF-` APAC usage types with supposedly US-only viewers prove PriceClass_All serves from APAC edges.

### Step 3: Distribution classification

Distribution classification table (seven shapes and their optimization emphasis) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Use the shape to weight price class vs cache vs origin vs edge-compute emphasis.

### Step 4: Price Class optimization

Price Class decision matrix and the APAC-egress proxy check moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Verdict: OPPORTUNITY_FOUND (price class) — >= 95% US/EU viewers on PriceClass_All -> PriceClass_100 saves 20-40%.

### Step 5: Cache hit ratio optimization

Cache-policy probe commands, change table, and the UTM worked example moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Verdict: OPPORTUNITY_FOUND (cache policy) — static CacheHitRate < 75% means cache-key bloat or TTL too short.

### Step 6: Origin optimization

Origin decision matrix and the custom-origin-to-S3 migration runbook moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Verdict: OPPORTUNITY_FOUND (origin) — custom origin serving static assets -> S3 + OAC saves $0.02/GB egress.

### Step 7: Compression optimization

Compression probe, content-type decision matrix, and Accept-Encoding caveat moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Verdict: OPPORTUNITY_FOUND (compression) — Compress false on text/image content is a free 50-90% byte saving.

### Step 8: Origin Shield optimization

Origin Shield break-even formula, decision matrix, and 3-edge math moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Verdict: OPPORTUNITY_FOUND (Origin Shield) — enable for custom origins and high request counts; skip low-volume S3.

### Step 9: Edge compute optimization (Functions vs Lambda@Edge)

Edge-compute probe, decision matrix, cost math, and migration steps moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Verdict: OPPORTUNITY_FOUND (edge compute) — sub-1ms Lambda@Edge header/rewrite logic -> Functions; measure runtime first.

### Step 10: Security cost optimization

WAF/Shield probes, security decision matrix, and Savings Bundle math moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Verdict: OPPORTUNITY_FOUND (security cost) — Shield Advanced on a non-DDoS-prone workload is $3,000/month recoverable.

### Step 11: Impact estimation

Impact-estimation formula and 2026 pricing notes moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Output: sum per-dimension savings into ESTIMATED_SAVINGS (current minus projected monthly cost).

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

Secondary worked example (ALREADY_OPTIMAL) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when emitting an ALREADY_OPTIMAL verdict.

### Worked example — NEED_MORE_INFO (viewer geography unknown)

Secondary worked example (NEED_MORE_INFO, viewer geography unknown) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when the data gate blocks the Price Class dimension.

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

Target hit-ratio formula and per-content-type target table moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when setting per-content-type targets or quantifying the savings from closing the gap.

## Error handling — CLI and data-source failures

API failure tables (CloudFront config, CloudWatch, Cost Explorer, WAF/Shield) and the aggregate retry policy moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when a data-source CLI call fails.

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

The 60-second triage (six checks on config, hit rate, CE usage types, Lambda@Edge, Shield, WAF rules) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Run it before deep-diving any single dimension.

## Pre-flight safety checks (run before any remediation CLI)

Pre-flight safety checks (CONFIRMATION GATE, snapshot, one-dimension-per-deploy, fleet batching, invalidation cost, replica deletion) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load them before emitting any remediation CLI.

## Remediation guidance

Per-dimension remediation CLI sequences (price class, cache policy, compression, origin, shield, edge compute, security, already-optimal) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when writing the MIGRATION_STEPS block.

## Deep reference: CloudFront pricing and limit cheat sheet

Pricing tiers, quota reference, and the Functions-vs-Lambda@Edge capability matrix moved verbatim to [references/cloudfront-pricing-reference.md](references/cloudfront-pricing-reference.md).
Load on demand for pricing math and limit checks.

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when scoping Savings Bundle, OAC, KeyValueStore, continuous deployment, MRAP, or VPC origins.

## References (load on demand)

- [references/cloudfront-pricing-reference.md](references/cloudfront-pricing-reference.md) — pricing matrix, Origin Shield break-even, WAF/Shield pricing; now also the pricing cheat sheet (tiers, quotas, Functions vs Lambda@Edge) moved from SKILL.md
- [references/advanced-patterns.md](references/advanced-patterns.md) — philosophy, Step 0 gotchas, Step 1-11 deep dives (matrices, probes, worked math), hit-ratio targets, 60-second triage, recent AWS features moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — required data-source pulls and pre-flight safety checks moved from SKILL.md
- [references/error-handling.md](references/error-handling.md) — CLI/data-source failure tables, retry policy, and per-dimension remediation CLI moved from SKILL.md
- [references/worked-examples.md](references/worked-examples.md) — ALREADY_OPTIMAL and NEED_MORE_INFO worked examples moved from SKILL.md

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
