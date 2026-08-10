# Eval prompt: shield-advanced-marketing-site

Optimize the CloudFront distribution for cost. Walk the nine-dimension
optimization logic and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

DistributionId: E-shield-advanced-marketing-site
Region: us-east-1 (distribution); viewers 95% US
PriceClass: PriceClass_100
Origins:
  - S3 origin with OAC: s3-marketing (us-east-1)
Default cache behavior:
  Target origin: s3-marketing
  Cache policy: CachingOptimized
  Compress: true
WAF: 5 rules
Shield: Advanced ($3,000/month on this distribution)
Metrics (last 30 days):
  CacheHitRate: 94%
  Requests: 50,000,000
  BytesDownloaded: 400 GB
Workload context: corporate marketing website; no transaction
processing; no login; no commerce. Traffic is steady, no history of
DDoS.
