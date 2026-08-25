# Error Handling (load on demand) — CloudFront Cost Optimizer

Failure handling and remediation moved verbatim from SKILL.md: CLI/data-source failure tables, aggregate retry policy, and per-dimension remediation CLI sequences.


---

## Error handling — CLI and data-source failures (moved from SKILL.md)

The workflow depends on three live data sources (CloudFront config,
CloudWatch metrics, Cost Explorer). Each can fail independently.

### CloudFront config API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-distribution-config` returns `NoSuchResource` | API error | Distribution ID is wrong or distribution is deleted. Verify with `list-distributions`. Emit BLOCKED with corrected ID suggestion. |
| `Distribution.Status == InProgress` | Status field | Distribution is mid-deploy. Wait 5-15 minutes, retry. Emit BLOCKED if still InProgress after 30 minutes. |
| `ETag` mismatch on `update-distribution` | API error | Another change happened between your get and update. Re-pull config, re-apply your diff, retry. |
| `TooManyDistributionVersions` error on update | API error | CloudFront limits version history. No remediation needed; wait for old versions to age out. |
| `InvalidIfMatchVersion` | API error | Stale ETag. Same handling as above. |

### CloudWatch metric failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-metric-statistics` returns empty `Datapoints` for CacheHitRate | `len(Datapoints) == 0` | Distribution is < 24h old, or disabled. Emit NEED_MORE_INFO. |
| `SampleCount` < window_days × 24 (less than 1h granularity) | Datapoints sparse | Distribution had gaps in traffic. Re-pull with wider window. |
| CloudFront namespace not returning any metrics | `list-metrics` returns no CloudFront metrics | Distribution may not have the `AWS/CloudFront` namespace enabled (rare; CloudFront always emits to this namespace). Check region — CloudFront metrics are in `us-east-1` only. |
| CloudWatch API throttling | `Throttling` error | Retry with exponential backoff. If persistent, reduce period to 3600s. |

### Cost Explorer failures

| Failure mode | Detection | Handling |
|---|---|---|
| `AccessDeniedException` for `ce:GetCostAndUsage` | Exit code non-zero | The role lacks billing permissions. Proceed without CE; flag the gap. The operator can grant `ce:GetCostAndUsage` and re-run. |
| CE returns no CloudFront line items | Empty Results | Account has no CloudFront usage in the window, OR the Cost Explorer API is filtering by linked account. Check `--filter` for linked-account scope. |
| CE usage amounts disagree with CloudFront metrics | Cross-source mismatch | Trust CE for billing, CloudFront metrics for operations. The delta is typically free tier, taxes, or WAF charges bundled under CloudFront. |

### WAF and Shield API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `wafv2 list-web-acls` returns empty | Empty WebACLs | Either no WAF in use, or WAF Classic (different API). Check `waf-regional` namespace for WAF Classic. |
| `wafv2 list-web-acls` returns ACLs but none associated with CloudFront | All scopes are REGIONAL | WAF is protecting ALB/API Gateway, not CloudFront. The distribution has no WAF. |
| `shield list-protections` returns empty | Empty Protections | No Shield Advanced in use. Treat security dimension as ALREADY_OPTIMAL. |
| `AccessDeniedException` for `shield:ListProtections` | Exit code non-zero | Role lacks Shield permissions. Surface in output; do not block. |

### Aggregate behavior

If ANY data source fails with a transient error (throttling,
network), retry up to 3 times with exponential backoff before
treating that dimension as NEED_MORE_INFO. For persistent failures
(IAM denial, missing distribution), emit the appropriate gating
verdict for that dimension and proceed with the remaining
dimensions — do not abort the entire evaluation on a single source
failure.


---

## Remediation guidance (moved from SKILL.md)

### For OPPORTUNITY_FOUND — Price Class

```bash
# Snapshot current config
aws cloudfront get-distribution-config --id $DIST_ID --output json \
  > backup-$(date +%s).json

# Update PriceClass
aws cloudfront update-distribution --id $DIST_ID \
  --if-match <ETag> \
  --distribution-config <updated-json-with-PriceClass_100>

# Verify deploy
aws cloudfront get-distribution --id $DIST_ID \
  --query 'Distribution.Status'
```

### For OPPORTUNITY_FOUND — Cache policy

```bash
# Create a new cache policy with tightened cache key
aws cloudfront create-cache-policy --cache-policy-config '{
  "Name":"optimized-static-v1",
  "Comment":"UTMs excluded; minimal cache key",
  "DefaultTTL":86400,
  "MaxTTL":31536000,
  "MinTTL":0,
  "ParametersInCacheKeyAndForwardedToOrigin":{
    "EnableAcceptEncodingGzip":true,
    "EnableAcceptEncodingBrotli":true,
    "HeadersConfig":{"HeaderBehavior":"none"},
    "CookiesConfig":{"CookieBehavior":"none"},
    "QueryStringsConfig":{
      "QueryStringBehavior":"allExcept",
      "QueryStringNames":{"Items":["utm_source","utm_medium",
        "utm_campaign","utm_term","utm_content"]}
    }
  }
}' --query 'CachePolicy.Id' --output text

# Update distribution to use the new policy ID on the default behavior
aws cloudfront update-distribution --id $DIST_ID --if-match <ETag> \
  --distribution-config <updated-json-with-new-CachePolicyId>
```

### For OPPORTUNITY_FOUND — Compression

```bash
# Just flip the Compress flag
# Update the DefaultCacheBehavior.Compress to true in the config JSON,
# then update-distribution.
```

### For OPPORTUNITY_FOUND — Origin (migrate custom to S3)

```bash
# Sync static files to S3
aws s3 sync /var/www/static s3://static-bucket/ --delete

# Create Origin Access Control
OAC_ID=$(aws cloudfront create-origin-access-control \
  --origin-access-control-config '{
    "Name":"static-bucket-OAC",
    "Description":"OAC for static-bucket",
    "SigningProtocol":"sigv4",
    "SigningBehavior":"always",
    "OriginAccessControlOriginType":"s3"
  }' --query 'OriginAccessControl.Id' --output text)

# Add S3 bucket policy granting CloudFront OAC access
# (see AWS docs for the canonical bucket policy)

# Update distribution: add S3 origin + path behavior for /static/*
```

### For OPPORTUNITY_FOUND — Origin Shield

```bash
# Add OriginShield to the origin in the distribution config
# OriginShield requires a region selection
# Update the Origins.Items[].OriginShield field:
#   { "Enabled": true, "OriginShieldRegion": "us-east-1" }
aws cloudfront update-distribution --id $DIST_ID \
  --if-match <ETag> \
  --distribution-config <config-with-OriginShield-enabled>
```

### For OPPORTUNITY_FOUND — Edge compute migration

```bash
# Test the rewritten CloudFront Function
aws cloudfront test-function \
  --if-match <ETag> \
  --stage DEVELOPMENT \
  --event-object fileb://test-event.json \
  --name <function-name>

# Publish the function
aws cloudfront publish-function --name <function-name> \
  --if-match <ETag>

# Associate with the cache behavior; disassociate Lambda@Edge
```

### For OPPORTUNITY_FOUND — Security cost

```bash
# Drop Shield Advanced (after confirming SRT not needed)
aws shield delete-protection --protection-id <id>

# Consolidate WAF rules (delete unused rules)
aws wafv2 update-web-acl --scope CLOUDFRONT --region us-east-1 \
  --web-acl-id <id> \
  --name <name> \
  --default-action <action> \
  --rules <consolidated-rule-list>
```

### For ALREADY_OPTIMAL or OPTIMIZED

1. No remediation required for the current posture.
2. Recommend quarterly review of CloudFront metrics and Cost
   Explorer breakdown — workloads drift.
3. For Security Savings Bundle renewals, re-evaluate at the renewal
   date for any CloudFront usage pattern changes.
