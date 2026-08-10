# Eval prompt: priceclass-all-us-only-viewers

Optimize the CloudFront distribution for cost. Walk the nine-dimension
optimization logic and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

DistributionId: E-priceclass-all-us-only-viewers
Region: us-east-1 (distribution); viewers 98% US/EU per CloudFront
  access logs (1% APAC, 1% other)
PriceClass: PriceClass_All
Origins:
  - S3 origin with OAC: s3-prod-assets (us-east-1)
Default cache behavior:
  Target origin: s3-prod-assets
  Cache policy: CachingOptimized (TTL 31536000, minimal key)
  Compress: true (Brotli + gzip)
  Lambda@Edge associations: 0
CloudFront Functions associations: 0
WAF: 5 rules, ~200M requests/month
Shield: Standard (no Advanced)
Metrics (last 30 days):
  CacheHitRate: 92%
  Requests: 200,000,000
  BytesDownloaded: 1,200 GB
  OriginLatency: 80ms p50
