# End-to-end usage scenario: cloudfront-distribution-deployer

A walkthrough showing the skill producing a deployment plan for a
production CloudFront distribution in front of an S3 origin with OAC,
WAFv2, security headers, and CloudFront Functions for SPA routing.
Demonstrates the READY_TO_DEPLOY verdict, architecture checklist, and
ordered deploy-command list.

## Input (user prompt)

> Provision a CloudFront distribution for our marketing site. The origin
> is an S3 bucket `marketing-site-assets` in us-east-1. We need OAC
> configured (no OAI), WAF with managed rules + rate limiting, HSTS
> preload, geo restriction to North America + Europe, and a CloudFront
> Function to rewrite all paths to /index.html for client-side SPA
> routing. Domain is `marketing.example.com`.

## Expected behavior

1. **Pre-flight:** The skill validates the spec — origin (S3 REST),
   viewer protocol requirement, ACM cert ARN in us-east-1, WAF scope.
   No S3 website endpoint (would block). No missing fields.
2. **Origin access:** Plans OAC creation (`signing behavior: always`) +
   S3 bucket policy update to service-principal with `AWS:SourceArn`
   condition.
3. **TLS posture:** Sets MinimumProtocolVersion to TLSv1.2_2021 (not
   `_2019` which still permits CBC).
4. **WAF:** Plans CLOUDFRONT-scope Web ACL in us-east-1 with
   CommonRuleSet + AmazonIpReputationList + rate-based rule.
5. **Edge compute:** Plans a CloudFront Function (not Lambda@Edge) for
   URL rewrite — sub-millisecond, no network needed.
6. **Verdict:** READY_TO_DEPLOY — all 14 checklist dimensions pass.

## Expected output

```text
DISTRIBUTION_SPEC: marketing-cdn
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Origin: S3 REST (marketing-site-assets.s3.us-east-1.amazonaws.com) + OAC
  Viewer protocol: redirect-to-https
  TLS: TLSv1.2_2021 + ACM cert arn:aws:acm:us-east-1:111111111111:certificate/mkt-abc
  WAF: arn:aws:wafv2:us-east-1:111111111111:global/webacl/marketing-waf/xyz-789
  Cache policy: CachingOptimized
  Origin request policy: none (S3 origin, no forwarding)
  Response headers: security-headers-policy (HSTS 2yr preload, CSP, DENY frame)
  Geo: whitelist US, CA, MX, GB, DE, FR, ES, IT, NL, SE, NO, FI, DK
  Price class: PriceClass_100
  Edge compute: CloudFront Function (SPA URL rewrite)
  Logging: S3 standard (marketing-cf-logs.s3.amazonaws.com) + ACL grant
CHECKLIST:
  [x] Origin is S3 REST with OAC (signing behavior: always)
  [x] OriginAccessControlId set on S3 origin
  [x] Bucket policy updated to service-principal with AWS:SourceArn
  [x] Custom origin protocol: N/A (S3 origin)
  [x] ViewerProtocolPolicy: redirect-to-https
  [x] MinimumProtocolVersion: TLSv1.2_2021
  [x] ACM cert in us-east-1, covers marketing.example.com
  [x] WAFv2 Web ACL associated (CLOUDFRONT scope, us-east-1)
  [x] Cache policy: CachingOptimized attached
  [x] Response headers policy: HSTS + CSP + X-Frame-Options DENY
  [x] Origin group: N/A (single origin)
  [x] Geo: whitelist (NA + Europe)
  [x] Price class: 100 (NA + Europe edges)
  [x] Access logging: enabled, ACL grant to awslogsdelivery
FINDINGS:
  - [INFO] Estimated monthly cost: $0 base + $0.085/GB to S3 + $0.02/GB to viewers + $5/WAF
  - [INFO] CloudFront Function at $0.10/M invocations (much cheaper than Lambda@Edge)
  - [NOTE] HSTS preload — browsers will refuse HTTP for 2 years (hard to undo)
DEPLOY_COMMANDS:
  1. aws cloudfront create-origin-access-control (signing behavior: always)
  2. aws s3api put-bucket-policy (service-principal with AWS:SourceArn)
  3. aws acm describe-certificate --region us-east-1 (verify ISSUED)
  4. aws wafv2 create-web-acl --scope CLOUDFRONT --region us-east-1
  5. aws cloudfront create-response-headers-policy (security headers)
  6. aws cloudfront create-function (SPA URL rewrite: /* → /index.html)
  7. aws cloudfront create-distribution (with all attached configs)
  8. aws cloudfront wait distribution-deployed
  9. aws wafv2 associate-web-acl (Web ACL ARN to distribution ARN)
```

## Post-deployment verification

After running the deploy commands, verify the distribution is correctly
provisioned and security posture is enforced:

```bash
# Verify distribution is Deployed
aws cloudfront get-distribution --id <id> \
  --query 'Distribution.Status'

# Verify OAC is attached
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.Origins.Items[0].OriginAccessControlId'

# Verify WAF is associated
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.WebACLId'

# Verify ACM cert is in us-east-1 and ISSUED
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:111111111111:certificate/mkt-abc \
  --region us-east-1 --query 'Certificate.Status'

# Test the distribution
curl -I https://marketing.example.com/
# Expect: HTTP/2 200
# Expect: strict-transport-security: max-age=63072000; includeSubDomains; preload
# Expect: x-frame-options: DENY
# Expect: content-security-policy: default-src 'self'; ...

# Verify S3 bucket is NOT publicly accessible (OAC working)
curl -I https://marketing-site-assets.s3.us-east-1.amazonaws.com/index.html
# Expect: 403 Forbidden (bucket is private; only CloudFront can read via OAC)
```

## Common pitfalls to verify after deployment

1. **Bucket policy uses AWS:SourceArn, not wildcard.** Without the
   distribution ARN in the condition, ANY distribution in the account
   could read the bucket via its own OAC. Always scope to the specific
   distribution ARN.
2. **WAF scope is CLOUDFRONT, not REGIONAL.** A REGIONAL-scope ACL
   cannot be associated with a CloudFront distribution — only
   CLOUDFRONT scope works, and only in us-east-1.
3. **Logging bucket ACL grant is present.** A bucket with ACLs disabled
   (BucketOwnerEnforced) silently rejects CloudFront logs. The grant
   to `awslogsdelivery` canonical ID is required.
4. **CloudFront Function is published (not just created).** A function
   must be deployed (`publish-function`) before it can be attached to
   a cache behavior. An unpublished function is a draft.
5. **HSTS preload is intentional.** Once on the browser preload list,
   the site cannot be served over HTTP even temporarily (e.g., for
   debugging). Confirm before enabling preload.
