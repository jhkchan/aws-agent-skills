# Eval prompt: tls-v1-allow-all

Audit the following CloudFront distribution configuration for security
exposure. Emit the standard VERDICT block (DISTRIBUTION, VERDICT, REASON,
FINDINGS, REMEDIATION).

Distribution id: E1A2B3C4D5 (tls-v1-allow-all)
Distribution config:
  Enabled: true
  DefaultCacheBehavior:
    TargetOriginId: S3-origin
    ViewerProtocolPolicy: allow-all
    AllowedMethods: {Items: [HEAD, GET], Quantity: 2}
  Origins:
    Items:
      - Id: S3-origin
        DomainName: mybucket.s3.amazonaws.com
        OriginAccessControlId: E2QWERTY1234567
        S3OriginConfig:
          OriginAccessIdentity: ""
  ViewerCertificate:
    MinimumProtocolVersion: TLSv1
    SSLSupportMethod: sni-only
  WebACLId: arn:aws:wafv2:us-east-1:111111111111:webacl/prod-waf/abc123
  Logging:
    Enabled: true
    Bucket: cf-logs.s3.amazonaws.com
    Prefix: "tls-v1/"
  Restrictions:
    GeoRestriction:
      RestrictionType: whitelist
      Items: [US, CA]
  DefaultRootObject: index.html
