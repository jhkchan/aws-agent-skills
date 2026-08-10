# Eval prompt: already-optimal-distribution

Optimize the CloudFront distribution for cost. Walk the nine-dimension
optimization logic and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

DistributionId: E-already-optimal-distribution
Region: us-east-1 (distribution); viewers 98% US/EU
PriceClass: PriceClass_100
Origins:
  - S3 origin with OAC: s3-prod-app (us-east-1)
Default cache behavior:
  Target origin: s3-prod-app
  Cache policy: custom-minimal-key (TTL 604800 default, query
    strings: none, cookies: none, headers: Accept, Accept-Encoding)
  Compress: true (Brotli + gzip)
  CloudFront Functions associations: 1 viewer-request (header
    normalization, < 1ms runtime verified)
  Lambda@Edge associations: 0
WAF: 5 rules on 200M requests/month (consistent with traffic)
Shield: Standard (no Advanced — distribution is internal app)
Origin Shield: enabled, us-east-1 region (close to S3 origin)
CloudFront Security Savings Bundle: 1-yr commit at $5K/month
  steady-state, 30% discount applied

Metrics (last 30 days):
  CacheHitRate: 94%
  Requests: 200,000,000
  BytesDownloaded: 1,500 GB
  OriginLatency: 75ms p50
