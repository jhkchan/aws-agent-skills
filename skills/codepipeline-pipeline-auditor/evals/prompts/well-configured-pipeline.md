# Eval prompt: well-configured-pipeline

Audit the following CodePipeline pipeline definition for security exposure.
Emit the standard VERDICT block (PIPELINE, VERDICT, REASON, FINDINGS, REMEDIATION).

Pipeline name: well-configured-pipeline
Pipeline definition (JSON):

```json
{
  "pipeline": {
    "name": "well-configured-pipeline",
    "roleArn": "arn:aws:iam::111111111111:role/service-role-AWS-CodePipeline-Service",
    "artifactStore": {
      "type": "S3",
      "location": "codepipeline-us-east-1-111111111111-store",
      "encryptionKey": {
        "id": "arn:aws:kms:us-east-1:111111111111:key/jkl-012-mno",
        "type": "KMS"
      }
    },
    "stages": [
      {
        "name": "Source",
        "actions": [
          {
            "name": "Source",
            "actionTypeId": {
              "category": "Source",
              "owner": "AWS",
              "provider": "CodeStarConnection",
              "version": "1"
            },
            "configuration": {
              "ConnectionArn": "arn:aws:codestar-connections:us-east-1:111111111111:connection/clean-123",
              "FullRepositoryId": "org/app",
              "BranchName": "main"
            },
            "outputArtifacts": [{"name": "SourceOutput"}]
          }
        ]
      },
      {
        "name": "Approval",
        "actions": [
          {
            "name": "ManualApproval",
            "actionTypeId": {
              "category": "Approval",
              "owner": "AWS",
              "provider": "Manual",
              "version": "1"
            },
            "configuration": {
              "NotificationArn": "arn:aws:sns:us-east-1:111111111111:pipeline-approval-topic",
              "CustomData": "Review and approve production deployment"
            }
          }
        ]
      },
      {
        "name": "Deploy",
        "actions": [
          {
            "name": "DeployCFN",
            "actionTypeId": {
              "category": "Deploy",
              "owner": "AWS",
              "provider": "CloudFormation",
              "version": "1"
            },
            "configuration": {
              "ActionMode": "CREATE_UPDATE",
              "StackName": "app-stack",
              "RoleArn": "arn:aws:iam::111111111111:role/CloudFormationDeploy",
              "TemplatePath": "SourceOutput::template.yaml"
            },
            "inputArtifacts": [{"name": "SourceOutput"}]
          }
        ]
      }
    ]
  }
}
```

Pipeline state: all stage transitions enabled.
Artifact bucket SSE: SSE-KMS with the CMK referenced above.
