# Eval prompt: create-invalidation-all-paths-ready

Plan the following CloudFront invalidation creation operation and emit
the standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, COST, NOTES).

Operation: create-invalidation
DistributionId: E1ABC2DEF3GHI4
DomainName: d111111abcdef8.cloudfront.net
Paths: ["/*"]

```json
{
  "Distribution": {
    "Id": "E1ABC2DEF3GHI4",
    "Status": "Deployed",
    "DomainName": "d111111abcdef8.cloudfront.net",
    "DistributionConfig": {
      "Enabled": true,
      "Origins": {
        "Items": [
          {"Id": "S3-origin", "DomainName": "prod-bucket.s3.amazonaws.com"}
        ]
      },
      "ContinuousDeploymentPolicyId": null
    },
    "LastModifiedTime": "2026-08-09T14:00:00Z"
  },
  "RecentInvalidations": {
    "TotalThisMonth": 3,
    "TotalPathsThisMonth": 12,
    "CallerReferencesUsed": ["inv-20260715-001", "inv-20260801-001", "inv-20260805-002"]
  },
  "CallingIdentity": "arn:aws:iam::111111111111:role/CloudFrontAdmin",
  "IAMPermissions": ["cloudfront:CreateInvalidation"],
  "CallerReference": "inv-20260810-001"
}
```
