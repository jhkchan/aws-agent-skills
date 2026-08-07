# Baseline (no-skill) response: greenfield-cfn-pipeline-automated

This file captures what a generic assistant produces WITHOUT the
cicd-pipeline-automator skill loaded.

---

To create a CI/CD pipeline for your Node 18 service, use:

```bash
aws codepipeline create-pipeline --cli-input-json file://pipeline.json
```

Here's a basic pipeline.json with Source (GitHub), Build (CodeBuild),
and Deploy (CloudFormation) stages.

```json
{
  "pipeline": {
    "name": "prod-checkout-pipeline",
    "roleArn": "arn:aws:iam::111111111111:role/AWS-CodePipeline-Service",
    "artifactStore": {
      "type": "S3",
      "location": "prod-checkout-artifacts"
    },
    "stages": [
      {
        "name": "Source",
        "actions": [{
          "name": "Source",
          "actionTypeId": {
            "category": "Source",
            "owner": "ThirdParty",
            "provider": "GitHub",
            "version": "1"
          },
          "configuration": {
            "Owner": "acme-org",
            "Repo": "checkout-service",
            "Branch": "main"
          }
        }]
      },
      {
        "name": "Build",
        "actions": [{
          "name": "Build",
          "actionTypeId": {
            "category": "Build",
            "owner": "AWS",
            "provider": "CodeBuild",
            "version": "1"
          }
        }]
      },
      {
        "name": "Deploy",
        "actions": [{
          "name": "Deploy",
          "actionTypeId": {
            "category": "Deploy",
            "owner": "AWS",
            "provider": "CloudFormation",
            "version": "1"
          }
        }]
      }
    ]
  }
}
```
