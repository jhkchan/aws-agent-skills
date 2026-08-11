# Eval prompt: ecr-rescan-ready

Plan the following ECR rescan-on-push enablement for Inspector and
emit the standard VERDICT block.

Operation: configure-ecr-rescan
Repository: prod-app
Region: us-east-1
ScanOnPush: true

```json
{
  "EcrConfig": {
    "ecr.describe-repositories.prod-app": {
      "repositoryArn": "arn:aws:ecr:us-east-1:111111111111:repository/prod-app",
      "registryId": "111111111111",
      "createdAt": "2026-01-15"
    },
    "ecr.describe-image-scanning-configuration.prod-app": {
      "scanOnPush": false
    },
    "region_support": {
      "ecr-enhanced": true,
      "basic": true
    },
    "caller_iam": {
      "role": "InspectorOperatorRole",
      "permissions": ["ecr:PutImageScanningConfiguration"]
    }
  }
}
```
