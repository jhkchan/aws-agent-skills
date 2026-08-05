# Eval prompt: weak-source-no-approval

Audit the following CodePipeline pipeline definition for security exposure.
Emit the standard VERDICT block (PIPELINE, VERDICT, REASON, FINDINGS, REMEDIATION).

Pipeline name: weak-source-no-approval
Pipeline definition (JSON):

```json
{
  "pipeline": {
    "name": "weak-source-no-approval",
    "roleArn": "arn:aws:iam::111111111111:role/service-role-AWS-CodePipeline-Service",
    "artifactStore": {
      "type": "S3",
      "location": "codepipeline-us-east-1-111111111111-store",
      "encryptionKey": {
        "id": "arn:aws:kms:us-east-1:111111111111:key/ghi-789-jkl",
        "type": "KMS"
      }
    },
    "stages": [
      {
        "name": "Source",
        "actions": [
          {
            "name": "GitHubSource",
            "actionTypeId": {
              "category": "Source",
              "owner": "ThirdParty",
              "provider": "GitHub",
              "version": "1"
            },
            "configuration": {
              "Owner": "my-org",
              "Repo": "production-app",
              "Branch": "main",
              "OAuthToken": "{{resolve:secretsmanager:github-token:SecretString:token}}",
              "PollForSourceChanges": "true"
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
              "StackName": "production-app",
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
