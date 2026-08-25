# Advanced Patterns (load on demand) — CloudFront Distribution Auditor

Expert knowledge moved verbatim from SKILL.md: Step 0 non-obvious behaviors, the edge-case catalog, and the 2024-2026 feature notes.


---

## Step 0: Expert knowledge — non-obvious CloudFront behaviors (moved from SKILL.md)

These behaviors are easy to misjudge without operational CloudFront experience.
Each changes a verdict if ignored:

- **TLSv1.2_2021 vs TLSv1.2_2019 is a cipher-suite difference, not a protocol
  difference.** Both policies negotiate TLS 1.2+, but `_2021` removes all CBC-mode
  ciphers, keeping only AEAD suites (GCM). `TLSv1.2_2019` still permits
  `ECDHE-RSA-AES128-SHA256` (CBC), which is vulnerable to padding-oracle
  variants under specific conditions. The threshold for INSECURE_TLS is anything
  below `TLSv1.2_2021`. A policy of `TLSv1.2_2018` or `TLSv1.2_2019` looks
  "TLS 1.2" but silently includes weak ciphers. Do NOT treat TLSv1.2_2019 as
  acceptable — the year suffix is the cipher policy, not the TLS version.

- **ViewerProtocolPolicy `redirect-to-https` still accepts the initial HTTP
  request.** The 301 redirect happens server-side after CloudFront receives the
  request. The request URL (including query parameters) travels over HTTP
  before the redirect. For strict environments (PII in query strings, tokens in
  URLs), `https-only` is the only policy that rejects HTTP at the edge.
  `redirect-to-https` is acceptable for most workloads but flag the distinction.

- **OriginProtocolPolicy `match-viewer` propagates the viewer's protocol to the
  origin.** If the viewer connected over HTTP (before a redirect-to-https), and
  the origin protocol is `match-viewer`, CloudFront connects to the origin over
  HTTP too. This double-exposure (viewer AND origin on HTTP) is why
  `match-viewer` on custom origins is classified as INSECURE_TLS, not
  CONFIG_GAP.

- **OAC vs OAI is not cosmetic.** Origin Access Control (OAC) replaced Origin
  Access Identity (OAI) in 2022. OAC supports SSE-KMS (OAI does not — OAI
  cannot pass the KMS Decrypt permission, breaking encrypted S3 origins). OAC
  also supports IPv6. An S3 origin with OAI but no OAC on an SSE-KMS bucket
  silently fails (403 Access Denied on object GETs). The presence of OAI does
  NOT satisfy the OAC requirement — it is a legacy mechanism that should be
  migrated. However, OAI does keep the bucket private, so it is classified as
  CONFIG_GAP (should migrate), not NO_OAC (bucket is public).

- **S3 website endpoint as origin forces a public bucket.** The S3 website
  endpoint (`bucket.s3-website-us-east-1.amazonaws.com`) serves content only
  if the bucket has public read access — it bypasses S3 access policies
  entirely. Using it as a CloudFront origin means the bucket is publicly
  listable and readable. This is categorically different from the S3 REST
  endpoint, which works with OAC/OAI and private buckets. Always classify a
  website-endpoint origin as INSECURE_TLS (Step 4) — the remediation is to
  switch to the REST endpoint and configure OAC.

- **CloudFront WAF Web ACLs must be in us-east-1.** CloudFront is a global
  service, but the associated Web ACL must exist in us-east-1. A Web ACL in
  any other region cannot be associated. This is an AWS hard constraint, not
  a best practice. When verifying WAF association in a live account, check
  `aws wafv2 list-web-acls --scope CLOUDFRONT --region us-east-1` — the
  `CLOUDFRONT` scope only exists in us-east-1.

- **WebACLId field stores the ARN for WAFv2.** Even when using WAFv2 (not
  WAF Classic), the distribution config field is named `WebACLId` and contains
  the full Web ACL ARN (`arn:aws:wafv2:us-east-1:...:webacl/name/id`). An
  empty string means no WAF is associated. Do not confuse `WebACLId: ""`
  with "WAFv2 not supported" — it simply means no association.

- **Default root object absence leaks S3 listings.** If `DefaultRootObject`
  is empty and the origin is S3, a request to the distribution root path
  returns the S3 XML bucket listing (in REST mode) or the website index
  (in website mode). The REST listing exposes object keys, sizes, and last-
  modified timestamps — an information disclosure that aids enumeration
  attacks. Set `DefaultRootObject` to `index.html` (or equivalent) even if
  the distribution serves only API paths.

- **CloudFront access logging requires a bucket ACL grant.** The logging
  target bucket must grant WRITE and READ_ACP permissions to the
  `awslogsdelivery` account canonical ID. CloudFront does not use bucket
  policies for log delivery — it uses ACLs. A bucket with ACLs disabled
  (BucketOwnerEnforced) will silently reject logs. This is the most common
  cause of "logging enabled but no logs appearing."

- **Field-level encryption is deprecated.** Removed in 2024. Any distribution
  still referencing a field-level encryption profile is relying on a
  decommissioned feature. Flag as a CONFIG_GAP and recommend CloudFront
  Functions for request-body encryption.

- **TrustedKeyGroups empty does not always mean no access control.** Signed
  URLs/cookies require trusted key groups OR trusted signers (legacy). An
  empty list means no signed-URL protection on the cache behavior — but only
  flag this if the content is intended to be access-controlled (paywalled,
  authenticated). Public content does not need signed URLs.


---

## Edge-case handling (moved from SKILL.md)

- **Partially malformed config.** If the config JSON parses but individual
  sections are missing (e.g., `Origins` exists but `DefaultCacheBehavior` is
  absent), classify the available dimensions and emit an ERROR note for the
  missing section. Do NOT classify the entire distribution as ERROR when only
  one dimension is unparseable.

- **Multiple cache behaviors.** Only the **default** cache behavior's
  `ViewerProtocolPolicy` drives the verdict. Path-specific cache behaviors
  may have tighter policies, but the default behavior applies to all paths
  that do not match a pattern — it is the broadest exposure surface.

- **Multiple S3 origins.** Audit each origin independently. If ANY S3 origin
  lacks OAC, the distribution verdict is NO_OAC (or worse). A single exposed
  origin compromises the entire distribution.

- **Distribution with both S3 and custom origins.** Evaluate each origin by
  its type — S3 origins go through Steps 4-5, custom origins go through Step 3.
  Both findings contribute to the aggregate verdict.

- **ACM certificate in non-us-east-1 region.** Note as a deployment risk but
  do not change the verdict. CloudFront will reject the association at deploy
  time; this finding surfaces the issue before the operator attempts deployment.

- **Real-time logging vs standard logging.** `Logging.Enabled` covers standard
  access logging. Real-time logging is configured separately
  (`DistributionConfig.RealtimeLogConfigArn`). If real-time logging is
  configured but standard logging is disabled, note that real-time logging
  is present but do not flag the CONFIG_GAP — real-time logging satisfies the
  visibility requirement.


---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **VPC origins (2024-2025):** CloudFront now supports VPC origins, enabling distribution of private content from VPC-attached ALBs, NLBs, EC2 instances, and ECS services without internet exposure. Auditors should check whether distributions using VPC origins have appropriate origin security groups and that the VPC origin is not inadvertently exposed.
- **KeyValueStore (2024):** CloudFront KeyValueStore allows serverless key-value data for CloudFront Functions. This does not change the audit verdict but auditors should note that KVS data is mutable and could be used to inject configuration that bypasses origin checks.
- **Continuous deployment (2024):** CloudFront continuous deployment allows traffic shifting between distribution versions (canary, blue/green). Auditors should verify that the staging distribution has equivalent security configuration (WAF, TLS, OAC) as the primary — a security regression during traffic shifting is a real risk.
- **TLS 1.3 viewer support (2024):** CloudFront now supports TLS 1.3 for viewer connections. Auditors should recommend upgrading the minimum TLS version to TLSv1.2_2021 or TLSv1.3 where applicable.
- **Origin Access Control (OAC) for Lambda and MediaStore (2024-2025):** OAC now supports Lambda Function URLs and MediaStore origins in addition to S3. Auditors should verify OAC coverage on all origin types, not just S3.
