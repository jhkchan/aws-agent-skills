# Eval prompt: fully-secured-distribution

Audit the following CloudFront distribution configuration for security
exposure. Emit the standard VERDICT block (DISTRIBUTION, VERDICT, REASON,
FINDINGS, REMEDIATION).

Distribution id: E4D5E6F7G8 (fully-secured-distribution)
Distribution config:
  Enabled: true
  DefaultCacheBehavior:
    TargetOriginId: S3-origin
    ViewerProtocolPolicy: https-only
    AllowedMethods: {Items: [HEAD, GET], Quantity: 2}
  Origins:
    Items:
      - Id: S3-origin
        DomainName: prod-content.s3.us-east-1.amazonaws.com
        OriginAccessControlId: E2OACPROD1234567
        S3OriginConfig:
          OriginAccessIdentity: ""
  ViewerCertificate:
    MinimumProtocolVersion: TLSv1.2_2021
    SSLSupportMethod: sni-only
  WebACLId: arn:aws:wafv2:us-east-1:111111111111:webacl/prod-acl/aaa111
  Logging:
    Enabled: true
    Bucket: prod-cf-logs.s3.amazonaws.com
    Prefix: "prod/"
  Restrictions:
    GeoRestriction:
      RestrictionType: whitelist
      Items: [US, CA, GB, AU]
  DefaultRootObject: index.html
