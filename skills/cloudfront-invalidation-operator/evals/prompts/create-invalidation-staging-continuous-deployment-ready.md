# Eval prompt: create-invalidation-staging-continuous-deployment-ready

Plan the following CloudFront invalidation on a continuous deployment
staging distribution and emit the standard VERDICT block (OPERATION,
VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY, COST, NOTES).

Operation: create-invalidation
DistributionId: E1ABC2DEF3GHI4 (primary)
DomainName: d111111abcdef8.cloudfront.net
Paths: ["/api/v2/*"]

```json
{
  "Distribution": {
    "Id": "E1ABC2DEF3GHI4",
    "Status": "Deployed",
    "DomainName": "d111111abcdef8.cloudfront.net",
    "DistributionConfig": {
      "Enabled": true,
      "ContinuousDeploymentPolicyId": "CDP1XYZ"
    }
  },
  "ContinuousDeploymentPolicy": {
    "Id": "CDP1XYZ",
    "StagingDistribution": {
      "Id": "E5STAGING123",
      "DnsName": "d555555staging.cloudfront.net"
    },
    "TrafficConfig": {
      "Type": "SingleWeight",
      "SingleWeight": {
        "Weight": 0.1,
        "SessionStickiness": false
      }
    }
  },
  "CallingIdentity": "arn:aws:iam::111111111111:role/CloudFrontAdmin",
  "IAMPermissions": ["cloudfront:CreateInvalidation"],
  "CallerReference": "stg-20260810-001"
}
```
