# Eval prompt: create-invalidation-bulk-cost-advisory

Plan the following CloudFront invalidation with cost analysis and emit
the standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, COST, NOTES).

Operation: create-invalidation
DistributionId: E2XYZ5678GHIJ9
DomainName: d222222bcdefg9.cloudfront.net
Paths: 1,247 individual object paths (provided in invalidation-batch.json)

```json
{
  "Distribution": {
    "Id": "E2XYZ5678GHIJ9",
    "Status": "Deployed",
    "DomainName": "d222222bcdefg9.cloudfront.net",
    "DistributionConfig": {
      "Enabled": true,
      "ContinuousDeploymentPolicyId": null
    }
  },
  "MonthlyCumulativePathCount": 1247,
  "FreeTierLimit": 1000,
  "PathsBeyondFreeTier": 247,
  "CostPerPathBeyondFreeTier": 0.005,
  "CallerReference": "inv-20260810-002",
  "CallingIdentity": "arn:aws:iam::111111111111:role/CloudFrontAdmin",
  "IAMPermissions": ["cloudfront:CreateInvalidation"]
}
```
