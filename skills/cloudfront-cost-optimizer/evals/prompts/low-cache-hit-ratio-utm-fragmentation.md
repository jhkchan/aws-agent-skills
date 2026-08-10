# Eval prompt: low-cache-hit-ratio-utm-fragmentation

Optimize the CloudFront distribution for cost. Walk the nine-dimension
optimization logic and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

DistributionId: E-low-cache-hit-ratio-utm-fragmentation
Region: us-east-1 (distribution); viewers 90% US/EU
PriceClass: PriceClass_100
Origins:
  - S3 origin with OAC: s3-prod-cdn (us-east-1)
Default cache behavior:
  Target origin: s3-prod-cdn
  Cache policy: custom-utm-whitelist (TTL 86400 default, query
    strings whitelisted: utm_source, utm_medium, utm_campaign,
    utm_term, utm_content, version, format)
  Origin request policy: AllViewerExceptInternal
  Compress: true
WAF: 5 rules
Shield: Standard
Metrics (last 30 days):
  CacheHitRate: 58%
  Requests: 500,000,000
  BytesDownloaded: 3,000 GB
  OriginLatency: 120ms p50
Notes: CloudFront access logs show ~50 unique UTM combinations per
product page URL, each producing a separate cache entry.
