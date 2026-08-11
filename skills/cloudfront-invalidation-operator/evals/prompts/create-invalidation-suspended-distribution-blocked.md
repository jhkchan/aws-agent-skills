# Eval prompt: create-invalidation-suspended-distribution-blocked

Plan the following CloudFront invalidation and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, COST, NOTES).

Operation: create-invalidation
DistributionId: E3SUSPENDED001
DomainName: d333333suspend.cloudfront.net
Paths: ["/*"]

```json
{
  "Distribution": {
    "Id": "E3SUSPENDED001",
    "Status": "Suspended",
    "DomainName": "d333333suspend.cloudfront.net",
    "DistributionConfig": {
      "Enabled": false,
      "ContinuousDeploymentPolicyId": null
    }
  },
  "CallingIdentity": "arn:aws:iam::111111111111:role/CloudFrontAdmin",
  "IAMPermissions": ["cloudfront:CreateInvalidation"],
  "CallerReference": "inv-20260810-003"
}
```
