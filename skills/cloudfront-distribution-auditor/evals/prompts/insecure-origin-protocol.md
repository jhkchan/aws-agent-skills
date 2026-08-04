# Eval prompt: insecure-origin-protocol

Audit the following CloudFront distribution configuration for security
exposure. Emit the standard VERDICT block (DISTRIBUTION, VERDICT, REASON,
FINDINGS, REMEDIATION).

Distribution id: E5E6F7G8H9 (insecure-origin-protocol)
Distribution config:
  Enabled: true
  DefaultCacheBehavior:
    TargetOriginId: custom-origin
    ViewerProtocolPolicy: https-only
    AllowedMethods: {Items: [HEAD, GET], Quantity: 2}
  Origins:
    Items:
      - Id: custom-origin
        DomainName: api.example.com
        CustomOriginConfig:
          OriginProtocolPolicy: http-only
          HTTPPort: 80
          HTTPSPort: 443
  ViewerCertificate:
    MinimumProtocolVersion: TLSv1.2_2021
    SSLSupportMethod: sni-only
  WebACLId: arn:aws:wafv2:us-east-1:111111111111:webacl/api-waf/bbb222
  Logging:
    Enabled: true
    Bucket: cf-logs.s3.amazonaws.com
    Prefix: "api/"
  Restrictions:
    GeoRestriction:
      RestrictionType: blacklist
      Items: [CN, RU]
  DefaultRootObject: index.html
