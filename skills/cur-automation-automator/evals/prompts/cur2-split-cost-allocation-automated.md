# Eval prompt: cur2-split-cost-allocation-automated

Migrate to CUR 2.0 with Split Cost Allocation Data and emit the standard
VERDICT block.

Operation: migrate-cur2
Stack name: prod-cur2-sca
Caller: payer 111111111111
Goal: EKS per-pod cost attribution via SCAD
EKS cluster: prod-eks-cluster

```json
{
  "RequirementChecks": {
    "organizations.describe-organization": {
      "MasterAccountId": "111111111111"
    },
    "ce.list-cost-allocation-tags": {
      "aws:eks:clusterName": "Active"
    },
    "eks.describe-addon.prod-eks-cluster.amazon-cloudwatch-observability": {
      "status": "ACTIVE"
    },
    "iam.get-role.AWSServiceRoleForBCMDataExports": {
      "Exists": true
    },
    "bcm-data-exports.list-exports": []
  }
}
```
