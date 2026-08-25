# CloudFront Diagnostic Commands — Reference

Supplementary reference for the CloudFront Cache Troubleshooter skill.
The canonical command script per cache issue category, with sample
outputs and interpretation notes.

## Universal first commands (run for any cache issue)

```bash
# 1. Distribution config — identify cache behaviors, policies, origins.
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.{status:Enabled,origins:Origins.Items[*].{id:Id,domain:DomainName,type:DomainName},default:DefaultCacheBehavior.{target:TargetOriginId,policy:CachePolicyId,lam:LambdaFunctionAssociations,ttl:DefaultTTL},behaviors:CacheBehaviors.Items[*].{path:PathPattern,target:TargetOriginId,policy:CachePolicyId,lam:LambdaFunctionAssociations},webACL:WebACLId,logging:Logging}' \
  --output json

# 2. Test caching — request the same URL twice, check x-cache.
curl -sI https://<distribution-domain>/path | grep -iE 'x-cache|age|cache-control|set-cookie'
curl -sI https://<distribution-domain>/path | grep -iE 'x-cache|age|cache-control|set-cookie'

# 3. Test the origin directly (bypass CloudFront).
curl -sI https://<origin-domain>/path | grep -iE 'cache-control|expires|pragma|set-cookie|content-type'
```

The first `curl -I` to CloudFront shows whether the edge cached the
response. The second shows whether a repeat request hits the cache. The
origin `curl -I` shows what `Cache-Control` the origin sends — the most
common cache-miss cause.

## Per-category command scripts

### Category A: CACHE_MISS_ALWAYS

```bash
# 1. Origin Cache-Control (the #1 cause of cache miss).
curl -sI https://<origin-domain>/path | grep -iE 'cache-control|expires|pragma|set-cookie'

# 2. Cache policy TTL and settings.
aws cloudfront get-cache-policy --id <policy-id> \
  --query 'CachePolicy.CachePolicyConfig.{minTTL:MinTTL,defaultTTL:DefaultTTL,maxTTL:MaxTTL,originCC:OriginCacheControlHeaders,params:ParametersInCacheKeyAndForwardedToOrigin}' \
  --output json

# 3. Identify the cache policy ID from the distribution.
aws cloudfront get-distribution-config --id <dist-id> \
  --query 'DistributionConfig.DefaultCacheBehavior.CachePolicyId' --output text

# 4. For S3 origins, check the object metadata.
aws s3api head-object --bucket <bucket> --key <key> \
  --query 'CacheControl' --output text

# 5. CloudFront access logs: count Miss vs Hit for the path.
#     (If logs are in S3, use aws s3 cp to download and grep/awk.)
#     Look for: x-edge-result-type field value distribution.
```

**Interpretation:** if the origin sends `Cache-Control: no-store`,
CloudFront will not cache regardless of the policy. If the policy TTL is
0 or the policy is `CachingDisabled`, caching is off by design. Fix the
origin header or the policy TTL.

### Category B: STALE_CONTENT

```bash
# 1. Origin Cache-Control max-age.
curl -sI https://<origin-domain>/path | grep -i 'cache-control'

# 2. Recent invalidations.
aws cloudfront list-invalidations --distribution-id <id> \
  --query 'InvalidationList.Items[*].{id:Id,status:Status,paths:InvalidationBatch.Paths.Items,created:CreateTime}' \
  --output json

# 3. Check a specific invalidation status.
aws cloudfront get-invalidation --distribution-id <id> --id <invalidation-id> \
  --query 'Invalidation.{status:Status,paths:InvalidationBatch.Paths.Items,created:CreateTime}' \
  --output json

# 4. Cache policy: does it respect or override origin headers?
aws cloudfront get-cache-policy --id <policy-id> \
  --query 'CachePolicy.CachePolicyConfig.{originCC:OriginCacheControlHeaders,minTTL:MinTTL,defaultTTL:DefaultTTL,maxTTL:MaxTTL}' \
  --output json

# 5. CloudFront Age header (how long the object has been cached).
curl -sI https://<dist-domain>/path | grep -i 'age'
```

**Interpretation:** if `Age` is higher than the expected TTL, the object
has been cached too long. If no invalidation was sent, the stale content
is expected within TTL. If the origin `max-age` is too long, lower it.

### Category C: CACHE_KEY_VARIATION

```bash
# 1. Cache policy: what is in the cache key?
aws cloudfront get-cache-policy --id <policy-id> \
  --query 'CachePolicy.CachePolicyConfig.ParametersInCacheKeyAndForwardedToOrigin.{headers:HeadersConfig,cookies:CookiesConfig,query:QueryStringsConfig,gzip:EnableAcceptEncodingGzip,brotli:EnableAcceptEncodingBrotli}' \
  --output json

# 2. Check for User-Agent in the headers whitelist.
aws cloudfront get-cache-policy --id <policy-id> \
  --query 'CachePolicy.CachePolicyConfig.ParametersInCacheKeyAndForwardedToOrigin.HeadersConfig.Headers.Items' \
  --output json

# 3. CloudFront access logs: group Miss by User-Agent / cookie / query.
#     (Download logs from S3, parse with jq/awk.)
#     Look for: high cardinality in cs-user-agent, cs-cookie, or
#     cs-uri-query fields for Miss entries.

# 4. List managed policies for reference.
aws cloudfront list-cache-policies --type managed \
  --query 'CachePolicyList.Items[*].{id:Id,name:Name,desc:Comment}' \
  --output json
```

**Interpretation:** if `HeaderBehavior: whitelist` includes `User-Agent`
or `Authorization`, the cache is fragmented. If `CookieBehavior: all`,
every cookie combination fragments the cache. Switch to `none` or
`whitelist` with only response-affecting values.

### Category D: ERROR_FROM_CACHE

```bash
# 1. WAF on the distribution.
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.WebACLId' --output text

# 2. If WAF is attached, read the web ACL rules.
aws wafv2 get-web-acl --scope CLOUDFRONT --id <web-acl-id> \
  --query 'WebACL.Rules[*].{name:Name,action:Action,priority:Priority,visibility:VisibilityConfig}' \
  --output json

# 3. Lambda@Edge functions on the behavior.
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.DefaultCacheBehavior.LambdaFunctionAssociations.Items[*].{type:EventType,arn:LambdaFunctionARN,includeBody:IncludeBody}' \
  --output json

# 4. Test origin directly vs via CloudFront.
curl -sI https://<origin-domain>/path
curl -sI https://<dist-domain>/path

# 5. Check for cached errors — error response caching TTL.
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.CustomErrorResponses.Items[*].{errorCode:ErrorCode,ttl:ErrorCachingMinTTL,responseCode:ResponseCodePath,responsePagePath:ResponsePagePath}' \
  --output json
```

**Interpretation:**
- If the WAF returns `BLOCK` for the path, the 403 is WAF-caused.
- If Lambda@Edge is on `viewer-response` or `origin-response`, the
  function may be modifying the status code.
- If the origin returns 200 but CloudFront returns 403/404, the issue is
  in the CloudFront layer.
- If `CustomErrorResponses` has a high `ErrorCachingMinTTL` for 404, a
  transient 404 is cached and persists.

### Category E: LOW_HIT_RATIO

```bash
# 1. CloudFront CacheHitRate metric.
aws cloudwatch get-metric-statistics --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=<id> \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average --output json

# 2. Per-behavior metrics (if additional metrics enabled).
aws cloudwatch get-metric-statistics --namespace AWS/CloudFront \
  --metric-name Requests \
  --dimensions Name=DistributionId,Value=<id> \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Sum --output json

# 3. Origin latency (rising latency = more origin requests).
aws cloudwatch get-metric-statistics --namespace AWS/CloudFront \
  --metric-name OriginLatency \
  --dimensions Name=DistributionId,Value=<id> \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average --output json

# 4. Cache policy for the low-ratio behavior.
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.CacheBehaviors.Items[*].{path:PathPattern,policy:CachePolicyId}' \
  --output json
```

**Interpretation:** if `CacheHitRate` is dropping while `Requests` is
stable, the cache key or TTL changed. If `OriginLatency` is rising, the
origin is receiving more requests (cache miss increasing). Check the
cache policy for the affected behavior.

## Combining signals

The richest single diagnostic is a pair of `curl -I` calls: one to the
origin, one to CloudFront. The origin call reveals what `Cache-Control`
the origin sends. The CloudFront call reveals the `x-cache` header (Hit /
Miss / RefreshHit) and the `Age` (how long the object has been cached).

```bash
# Side-by-side comparison.
echo "=== ORIGIN ===" && curl -sI https://origin.example.com/path | grep -iE 'cache-control|set-cookie|content-type'
echo "=== CLOUDFRONT ===" && curl -sI https://d123.cloudfront.net/path | grep -iE 'x-cache|age|cache-control'
```

If the origin sends `Cache-Control: no-store` and CloudFront shows
`x-cache: Miss from cloudfront`, the cause is confirmed: ORIGIN_NO_STORE.

## Output verification commands

After applying a fix:

```bash
# For origin header changes: verify the new Cache-Control.
curl -sI https://<origin-domain>/path | grep -i 'cache-control'

# For cache policy changes: wait for Deployed status.
aws cloudfront get-distribution --id <id> --query 'Distribution.Status' --output text

# For invalidations: wait for Completed status.
aws cloudfront get-invalidation --distribution-id <id> --id <inv-id> --query 'Invalidation.Status' --output text

# Verify caching: request twice, check second is Hit.
curl -sI https://<dist-domain>/path | grep -i 'x-cache'  # Should be Miss or Hit
curl -sI https://<dist-domain>/path | grep -i 'x-cache'  # Should be Hit

# Monitor hit ratio over the next hour.
aws cloudwatch get-metric-statistics --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=<id> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average --output json
```



---

## Step 0: distribution discovery commands (moved from SKILL.md)

```bash
aws cloudfront list-distributions \
  --query 'DistributionList.Items[*].{id:Id,domain:DomainName,aliases:Aliases.Items,enabled:Enabled}' \
  --output json

aws cloudfront get-distribution-config --id <distribution-id> \
  --query 'DistributionConfig.DefaultCacheBehavior.{target:TargetOriginId,cachePolicy:CachePolicyId,lam:LambdaFunctionAssociations,ttl:DefaultTTL}' \
  --output json
```


---

## Diagnostic command quick reference (moved from SKILL.md)

```bash
# Distribution config — cache behaviors, policies, origins, WAF
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.{origins:Origins.Items,behaviors:CacheBehaviors.Items,default:DefaultCacheBehavior,webACL:WebACLId}' \
  --output json

# Cache policy details (the cache key definition)
aws cloudfront get-cache-policy --id <cache-policy-id> \
  --query 'CachePolicy.CachePolicyConfig.{ttl:{min:MinTTL,def:DefaultTTL,max:MaxTTL},params:ParametersInCacheKeyAndForwardedToOrigin}' \
  --output json

# Recent invalidations
aws cloudfront list-invalidations --distribution-id <id> \
  --query 'InvalidationList.Items[*].{id:Id,status:Status,paths:InvalidationBatch.Paths.Items}' \
  --output json

# CloudFront metrics — CacheHitRate
aws cloudwatch get-metric-statistics --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=<id> \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average --output json

# Test caching — request twice, check x-cache
curl -sI https://<distribution-domain>/path | grep -iE 'x-cache|age|cache-control'
curl -sI https://<distribution-domain>/path | grep -iE 'x-cache|age|cache-control'

# Test origin directly (bypass CloudFront)
curl -sI https://<origin-domain>/path | grep -iE 'cache-control|expires|pragma|set-cookie'

# Lambda@Edge functions on the behavior
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.DefaultCacheBehavior.LambdaFunctionAssociations.Items[*].{type:EventType,arn:LambdaFunctionARN}' \
  --output json
```
