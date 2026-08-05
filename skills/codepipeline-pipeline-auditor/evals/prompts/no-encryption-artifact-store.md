# Eval prompt: no-encryption-artifact-store

Audit the following CodePipeline pipeline definition for security exposure.
Emit the standard VERDICT block (PIPELINE, VERDICT, REASON, FINDINGS, REMEDIATION).

Pipeline name: no-encryption-artifact-store
Pipeline definition (JSON):

```json
{
  "pipeline": {
    "name": "no-encryption-artifact-store",
    "roleArn": "arn:aws:iam::111111111111:role/service-role-AWS-CodePipeline-Service",
    "artifactStore": {
      "type": "S3",
      "location": "codepipeline-us-east-1-111111111111-store"
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
              "ConnectionArn": "arn:aws:codestar-connections:us-east-1:111111111111:connection/abc-123",
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
Artifact bucket SSE configuration: none (no server-side encryption configured).
