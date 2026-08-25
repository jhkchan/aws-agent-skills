# Advanced Patterns (load on demand) — CloudFront Distribution Deployer

Deep-dive material moved verbatim from SKILL.md: Step 0 non-obvious CloudFront behaviors, the SNI/VIP note, the Step 6 WAF CLI, the Step 13 logging ACL + real-time config, the Step 14 staging CLI, the edge-case catalog, and the 2024-2026 feature notes.


---

## Step 0: Expert knowledge — non-obvious CloudFront behaviors that change the plan (moved from SKILL.md)

- **TLSv1.2_2021 vs TLSv1.2_2019 is a cipher-suite difference.** Both
  negotiate TLS 1.2+, but `_2021` removes all CBC-mode ciphers (keeps AEAD
  only). `_2019` still permits `ECDHE-RSA-AES128-SHA256` (CBC) which is
  vulnerable to padding-oracle variants. Always set `MinimumProtocolVersion:
  TLSv1.2_2021` for new distributions.

- **OAC signing behavior `always` vs `no-override`.** `always` signs every
  origin request (recommended for private S3). `no-override` signs only if
  no `Authorization` header is present (use when the origin also accepts
  its own auth). For S3 REST origins serving static content, use `always`.

- **OAC does NOT replace the bucket policy.** OAC is the CloudFront-side
  configuration. The S3 bucket must STILL grant `s3:GetObject` to
  `Service: cloudfront.amazonaws.com` with the
  `AWS:SourceArn` condition matching the distribution ARN. Without the
  bucket policy update, every object GET returns 403.

- **WAFv2 Web ACL for CloudFront MUST be in us-east-1 with CLOUDFRONT scope.**
  `aws wafv2 list-web-acls --scope CLOUDFRONT --region us-east-1` is the
  only way to enumerate them. A Web ACL in eu-west-1, even with CLOUDFRONT
  scope, cannot be associated.

- **Lambda@Edge functions MUST be in us-east-1 (and replicated).** You
  create the Lambda function in us-east-1; CloudFront replicates it to
  regional edge caches worldwide. A function created in any other region
  cannot be attached to a distribution.

- **CloudFront Functions are region-less (global).** They are deployed
  directly to all edge locations. No region constraint.

- **Cache policy and origin request policy are SEPARATE.** Cache policy
  controls which headers/cookies/query strings CloudFront caches
  (determines cache key). Origin request policy controls which
  headers/cookies/query strings CloudFront forwards to the origin
  (determines what the origin sees). Use managed policies as starting
  points; do not blindly forward everything (kills cache hit ratio).

- **Default cache behavior applies to unmatched paths.** Path-specific
  cache behaviors override for matched patterns (`/api/*`, `*.jpg`). Always
  configure the default behavior with the broadest applicable policy.

- **Origin group failover triggers on HTTP status codes.** Configure the
  failover criteria (e.g., 403, 404, 500, 502, 503, 504). The primary is
  tried first; on a matching status code, CloudFront switches to the
  secondary. Active-active requires a different setup (weighted routing at
  Route 53).

- **Price class controls cost but also latency.** `PriceClass_100` uses
  only North America + Europe edges — Asian users see higher latency.
  `PriceClass_All` includes all 600+ edge locations but has a higher
  per-GB rate in some regions.

- **Standard logging uses ACLs (not bucket policies).** The logging S3
  bucket must grant WRITE and READ_ACP to the `awslogsdelivery` account
  canonical ID (`c4c1ede66af53448b93ce283fc5b7c73`). A bucket with ACLs
  disabled (BucketOwnerEnforced) silently rejects logs. For new deployments,
  prefer real-time logging (`RealtimeLogConfigArn`) over standard logging.

- **Continuous deployment (staging distributions) requires a primary.**
  You create a staging distribution that mirrors the primary and shifts a
  percentage of traffic. After validation, you promote the staging config
  to the primary. The primary must exist first.

- **Response headers policy is REQUIRED for security headers.** Without an
  explicit policy, CloudFront passes through whatever the origin sends. If
  the origin does not send HSTS, CSP, or X-Frame-Options, the edge does
  not add them.


---

## Step 5: SNI vs VIP (moved from SKILL.md)

**SNI vs VIP:** `sni-only` is the modern default (requires SNI-capable
client — all modern browsers). `vip` is legacy, costs $600/month, reserved
for ancient clients (Java 6, Windows XP). Use SNI unless you have a
specific SNI-incompatible client.


---

## Step 6: WAFv2 Web ACL CLI (moved from SKILL.md)

**Create the Web ACL (CLOUDFRONT scope, us-east-1):**
```bash
aws wafv2 create-web-acl \
  --name prod-cdn-waf --scope CLOUDFRONT --region us-east-1 \
  --default-action Allow={} \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=prod-cdn-waf \
  --rules file://waf-rules.json
```

**Recommended rule groups:**
- `AWSManagedRulesCommonRuleSet` — OWASP Top 10 baseline.
- `AWSManagedRulesSQLiRuleSet` — SQL injection patterns.
- `AWSManagedRulesAmazonIpReputationList` — known malicious IPs.
- `AWSManagedRulesBotControlRuleSet` — bot/scraper detection.
- Rate-based rule — e.g., 2000 requests per 5 minutes per IP.

**Associate with the distribution:**
Set `WebACLId` in the distribution config to the Web ACL ARN
(`arn:aws:wafv2:us-east-1:<account>:global/webacl/<name>/<id>`).


---

## Step 13: Logging ACL grant and real-time logging (moved from SKILL.md)

**Logging bucket ACL grant (REQUIRED):**
```bash
aws s3api put-object-acl --bucket prod-cf-logs --key cdn-logs/ \
  --grant-write 'id="c4c1ede66af53448b93ce283fc5b7c73"' \
  --grant-read-acp 'id="c4c1ede66af53448b93ce283fc5b7c73"'
```
(The canonical ID `c4c1ede66af53448b93ce283fc5b7c73` is the
`awslogsdelivery` account.)

**Real-time logging (newer, recommended for production):**
```json
"RealtimeLogConfigArn": "arn:aws:cloudfront::<account>:realtime-log-config/prod-cf-rt"
```
Real-time logs stream to Kinesis Data Firehose (S3, OpenSearch, etc.)
within seconds. Better for anomaly detection than the 5-60 minute delay
of standard logging.


---

## Step 14: Continuous deployment CLI (moved from SKILL.md)

```bash
aws cloudfront create-distribution-with-staging-config \
  --staging-config-comment "staging for prod-cdn" \
  --default-cache-behavior ...
# After validation:
aws cloudfront copy-distribution --if-match <etag> --staging-distribution-id <id> --primary-distribution-id <id>
```

Use staging distributions to test config changes (new origins, new WAF
rules, new cache policies) with a small percentage of traffic before
promoting to the primary. Eliminates "deploy and pray" CDN releases.


---

## Edge-case handling (moved from SKILL.md)

- **ACM certificate in wrong region.** PREREQUISITES_MISSING. CloudFront
  can only read ACM certificates from us-east-1. Re-issue the cert in
  us-east-1 or use the default `*.cloudfront.net` domain.

- **S3 website endpoint origin.** PREREQUISITES_MISSING. Switch to REST
  endpoint + OAC. The website endpoint forces a public bucket and bypasses
  S3 access policies.

- **Self-signed origin certificate.** PREREQUECISITES_MISSING. CloudFront
  does not trust self-signed certs. Use ACM (for ALB) or a public CA cert.

- **Lambda@Edge function in non-us-east-1.** PREREQUISITES_MISSING. Move
  the function to us-east-1.

- **WAFv2 Web ACL with REGIONAL scope.** PREREQUISITES_MISSING. Re-create
  with `--scope CLOUDFRONT` in us-east-1.

- **Geo restriction with regulatory overlap.** If the workload is subject
  to multiple regimes (GDPR + OFAC), use a whitelist of explicitly-allowed
  countries. A blacklist of disallowed countries is harder to maintain.


---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **KeyValueStore (2024):** serverless key-value data for CloudFront
  Functions. Use for feature flags, lightweight config, IP allowlists.
  Updates propagate in minutes without function redeploy.

- **Continuous deployment (2024):** staging distributions with
  percentage-based traffic shifting. Promote staging config to primary
  after validation. Eliminates risky CDN releases.

- **VPC origins (2024-2025):** CloudFront can origin from private VPC
  resources (ALB, NLB, EC2, ECS) without internet exposure. Useful for
  internal-only applications needing edge delivery.

- **TLS 1.3 viewer support (2024):** CloudFront supports TLS 1.3 for
  viewer connections. Set `MinimumProtocolVersion: TLSv1.2_2021` as the
  floor; clients negotiate 1.3 if capable.

- **Origin Access Control for Lambda Function URLs and MediaStore
  (2024-2025):** OAC now covers more than S3. Verify OAC on all origin
  types when auditing.

- **CloudFront Metrics (2025):** Enhanced real-time metrics in CloudWatch
  plus additional edge-side dimensions for debugging cache hit ratios.
