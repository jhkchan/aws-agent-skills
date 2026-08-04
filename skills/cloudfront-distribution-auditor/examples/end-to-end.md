# End-to-end usage scenario: cloudfront-distribution-auditor

A walkthrough showing the skill auditing a CloudFront distribution that has
both weak TLS (INSECURE_TLS — TLSv1.2_2019 cipher suite) and a missing OAC
on the S3 origin (NO_OAC), demonstrating severity aggregation, the
cipher-suite-difference concept, and the OAC-migration remediation workflow.

## Input (user prompt)

> Review this CloudFront distribution before we launch the marketing site.
> The origin is an S3 bucket with SSE-KMS encryption. The security team
> flagged TLS and origin access last week.

```yaml
Distribution id: E27QWERTY123
Distribution config:
  Enabled: true
  DefaultCacheBehavior:
    TargetOriginId: marketing-s3
    ViewerProtocolPolicy: redirect-to-https
    AllowedMethods: {Items: [HEAD, GET], Quantity: 2}
  Origins:
    Items:
      - Id: marketing-s3
        DomainName: marketing-assets.s3.amazonaws.com
        OriginAccessControlId: ""
        S3OriginConfig:
          OriginAccessIdentity: ""
  ViewerCertificate:
    MinimumProtocolVersion: TLSv1.2_2019
    SSLSupportMethod: sni-only
  WebACLId: ""
  Logging:
    Enabled: false
  Restrictions:
    GeoRestriction:
      RestrictionType: none
      Items: []
  DefaultRootObject: ""
```

## Skill output

```text
DISTRIBUTION: E27QWERTY123
VERDICT: INSECURE_TLS
REASON: MinimumProtocolVersion is TLSv1.2_2019 — below TLSv1.2_2021; still
permits CBC-mode ciphers vulnerable to padding-oracle variants (Step 2). S3
origin also has no OAC and no OAI — bucket must be publicly readable for
CloudFront to serve content (Step 5).
FINDINGS:
  - [INSECURE_TLS] MinimumProtocolVersion TLSv1.2_2019 includes CBC-mode
    ciphers (ECDHE-RSA-AES128-SHA256); TLSv1.2_2021 restricts to AEAD-only
    (Step 2) — the year suffix is the cipher policy, not the TLS version
  - [NO_OAC] S3 origin "marketing-assets.s3.amazonaws.com" has no OAC and no
    legacy OAI — bucket must be publicly readable; users can bypass CloudFront
    and access objects directly (Step 5)
  - [CONFIG_GAP] No WAF Web ACL associated — OWASP attacks reach origin
    unfiltered (Step 6)
  - [CONFIG_GAP] Logging.Enabled is false — no breach forensics signal (Step 7)
  - [CONFIG_GAP] GeoRestriction RestrictionType is none — serves all countries
    (Step 8)
  - [CONFIG_GAP] DefaultRootObject is empty on S3 origin — root requests return
    S3 XML listing (Step 9)
REMEDIATION:
  1. Update MinimumProtocolVersion to TLSv1.2_2021:
     aws cloudfront get-distribution-config --id E27QWERTY123 --output json > /tmp/cf-backup.json
     ETAG=$(jq -r '.ETag' /tmp/cf-backup.json)
     jq '.DistributionConfig.ViewerCertificate.MinimumProtocolVersion = "TLSv1.2_2021"' /tmp/cf-backup.json | jq '.DistributionConfig' > /tmp/cf-updated.json
     aws cloudfront update-distribution --id E27QWERTY123 --if-match "$ETAG" --distribution-config file:///tmp/cf-updated.json
  2. Create OAC and attach to origin:
     aws cloudfront create-origin-access-control --origin-access-control-config '{"Name":"oac-marketing","Description":"OAC for marketing-assets","SigningProtocol":"sigv4","SigningBehavior":"always"}'
     Then set OriginAccessControlId on the origin and update the S3 bucket policy with the cloudfront.amazonaws.com service principal.
  3. Associate a WAF Web ACL (must be in us-east-1, CLOUDFRONT scope).
  4. Enable access logging to an S3 bucket with awslogsdelivery ACL grant.
  5. Set GeoRestriction to whitelist [US, CA, GB, AU].
  6. Set DefaultRootObject to index.html.
```

## What the skill caught that a generic assistant misses

1. **The TLSv1.2_2019 vs TLSv1.2_2021 cipher-suite difference.** A generic
   assistant says "TLS 1.2 is fine." The skill explains that `_2019` still
   permits CBC-mode ciphers, while `_2021` restricts to AEAD-only (GCM). The
   year suffix is the cipher policy, not the TLS version — the most common
   false-negative in CloudFront TLS audits.

2. **OAC absence on an SSE-KMS bucket compounds the problem.** The user
   mentioned SSE-KMS, and the skill knows that OAI (the legacy mechanism)
   does NOT support SSE-KMS — so even adding OAI would not fix the
   encrypted-bucket case. OAC is the only path.

3. **Severity aggregation with per-finding breakdown.** The verdict is
   INSECURE_TLS (worst finding), but the FINDINGS list shows each dimension:
   INSECURE_TLS (cipher suite), NO_OAC (origin bypass), and three
   CONFIG_GAP items. The operator can triage each independently.

4. **DefaultRootObject empty as an information-disclosure vector.** A
   generic assistant overlooks this. The skill flags that root requests
   return the S3 XML object listing — exposing keys, sizes, and timestamps
   to anyone who hits the distribution root.

## Slash-command invocation

```
/aws:audit-cloudfront-distribution
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this CloudFront distribution before we launch the marketing site"
```

The orchestrator emits
`[Phase: Audit | Skills routed: cloudfront-distribution-auditor]` and hands
off to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the distribution, validate the posture:

```bash
# Verify the minimum protocol version propagated
aws cloudfront get-distribution --id E27QWERTY123 --profile default \
  | jq '.Distribution.DistributionConfig.ViewerCertificate.MinimumProtocolVersion'

# Confirm OAC is attached
aws cloudfront get-distribution-config --id E27QERTY123 --profile default \
  | jq '.DistributionConfig.Origins.Items[].OriginAccessControlId'

# Check WAF association
aws cloudfront get-distribution-config --id E27QWERTY123 --profile default \
  | jq '.DistributionConfig.WebACLId'

# Wait for global propagation (5-60 min)
aws cloudfront get-distribution --id E27QWERTY123 --profile default \
  | jq '.Distribution.Status'
# Wait for "Deployed"
```

Then verify the S3 bucket is no longer public and that object GETs return
200 through CloudFront but 403 directly.
