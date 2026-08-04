# Eval prompt: missing-waf-and-logging

Audit the following CloudFront distribution configuration for security
exposure. Emit the standard VERDICT block (DISTRIBUTION, VERDICT, REASON,
FINDINGS, REMEDIATION).

Distribution id: E3C4D5E6F7 (missing-waf-and-logging)
Distribution config:
  Enabled: true
  DefaultCacheBehavior:
    TargetOriginId: S3-origin
    ViewerProtocolPolicy: redirect-to-https
    AllowedMethods: {Items: [HEAD, GET], Quantity: 2}
  Origins:
    Items:
      - Id: S3-origin
        DomainName: content.s3.amazonaws.com
        OriginAccessControlId: E2OACXYZ9876543
        S3OriginConfig:
          OriginAccessIdentity: ""
  ViewerCertificate:
    MinimumProtocolVersion: TLSv1.2_2021
    SSLSupportMethod: sni-only
  WebACLId: ""
  Logging:
    Enabled: false
  Restrictions:
    GeoRestriction:
      RestrictionType: whitelist
      Items: [US, CA]
  DefaultRootObject: index.html
