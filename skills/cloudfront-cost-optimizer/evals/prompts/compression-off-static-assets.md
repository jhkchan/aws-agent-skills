# Eval prompt: compression-off-static-assets

Optimize the CloudFront distribution for cost. Walk the nine-dimension
optimization logic and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

DistributionId: E-compression-off-static-assets
Region: us-east-1 (distribution); viewers 99% US
PriceClass: PriceClass_100
Origins:
  - S3 origin with OAC: s3-static-site (us-east-1)
Default cache behavior:
  Target origin: s3-static-site
  Cache policy: CachingOptimized
  Compress: false
WAF: 3 rules
Shield: Standard
Metrics (last 30 days):
  CacheHitRate: 88%
  Requests: 300,000,000
  BytesDownloaded: 2,500 GB
  OriginLatency: 95ms p50
Content profile: mostly text (HTML 40%, CSS 20%, JS 30%, images
10%). Images already compressed.
