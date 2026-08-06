# Eval prompt: overpermissive-cross-account-role

Audit the following CodePipeline pipeline definition for security exposure.
Emit the standard VERDICT block (PIPELINE, VERDICT, REASON, FINDINGS, REMEDIATION).

Pipeline name: overpermissive-cross-account-role
Pipeline definition (JSON):

```json
{
  "pipeline": {
    "name": "overpermissive-cross-account-role",
    "roleArn": "arn:aws:iam::111111111111:role/service-role-AWS-CodePipeline-Service",
    "artifactStore": {
      "type": "S3",
      "location": "codepipeline-us-east-1-111111111111-store",
      "encryptionKey": {
        "id": "arn:aws:kms:us-east-1:111111111111:key/abc-123-def",
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
              "ConnectionArn": "arn:aws:codestar-connections:us-east-1:111111111111:connection/xyz-789",
              "FullRepositoryId": "org/app",
              "BranchName": "main"
            },
            "outputArtifacts": [{"name": "SourceOutput"}]
          }
        ]
      },
      {
        "name": "Deploy",
        "actions": [
          {
            "name": "DeployCrossAccount",
            "actionTypeId": {
              "category": "Deploy",
              "owner": "AWS",
              "provider": "CloudFormation",
              "version": "1"
            },
            "configuration": {
              "ActionMode": "CREATE_UPDATE",
              "StackName": "app-stack",
              "RoleArn": "arn:aws:iam::222222222222:role/CrossAccountDeploy",
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
