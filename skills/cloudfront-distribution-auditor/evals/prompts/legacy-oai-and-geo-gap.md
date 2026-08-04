# Eval prompt: legacy-oai-and-geo-gap

Audit the following CloudFront distribution configuration for security
exposure. Emit the standard VERDICT block (DISTRIBUTION, VERDICT, REASON,
FINDINGS, REMEDIATION).

Distribution id: E6F7G8H9I0 (legacy-oai-and-geo-gap)
Distribution config:
  Enabled: true
  DefaultCacheBehavior:
    TargetOriginId: S3-origin
    ViewerProtocolPolicy: redirect-to-https
    AllowedMethods: {Items: [HEAD, GET], Quantity: 2}
  Origins:
    Items:
      - Id: S3-origin
        DomainName: legacy-bucket.s3.amazonaws.com
        OriginAccessControlId: ""
        S3OriginConfig:
          OriginAccessIdentity: origin-access-identity/cloudfront/E1A2B3C4D5
  ViewerCertificate:
    MinimumProtocolVersion: TLSv1.2_2021
    SSLSupportMethod: sni-only
  WebACLId: arn:aws:wafv2:us-east-1:111111111111:webacl/app-waf/ccc333
  Logging:
    Enabled: true
    Bucket: cf-logs.s3.amazonaws.com
    Prefix: "legacy/"
  Restrictions:
    GeoRestriction:
      RestrictionType: none
      Items: []
  DefaultRootObject: index.html
