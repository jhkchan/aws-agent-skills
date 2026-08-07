# Eval prompt: greenfield-cfn-pipeline-automated

Design a CI/CD pipeline for a Node 18 service and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, REQUIREMENTS,
PIPELINE_TEMPLATE, MANUAL_GAPS, NOTES).

Operation: create
Pipeline name: prod-checkout-pipeline
Source: GitHub (CodeStar Connection)
Repository: acme-org/checkout-service
Branch: main
Language: Node 18
Build image: aws/codebuild/standard:7.0
Deploy target: CloudFormation stack prod-checkout in same account
Approval gate: yes
Template format: CloudFormation

```json
{
  "RequirementChecks": {
    "codestar-connections.get-connection.abc-123": {
      "ConnectionStatus": "Available"
    },
    "iam.get-role.prod-deploy": {
      "TrustPolicy": "cloudformation.amazonaws.com (OK)"
    },
    "kms.describe-key.abc": {
      "KeyPolicy": "grants pipeline role + deploy role (OK)"
    },
    "s3api.get-bucket-versioning.prod-checkout-artifacts": {
      "Status": "Enabled"
    },
    "sns.get-topic-attributes.pipeline-approval": {
      "subscriptions": 2
    },
    "codebuild.list-curated-environment-images.standard:7.0": {
      "supports": ["nodejs:18"]
    }
  }
}
```
