# Eval prompt: multiple-findings-encryption-wins

Audit the following CodePipeline pipeline definition for security exposure.
Emit the standard VERDICT block (PIPELINE, VERDICT, REASON, FINDINGS, REMEDIATION).

Pipeline name: multiple-findings-encryption-wins
Pipeline definition (JSON):

```json
{
  "pipeline": {
    "name": "multiple-findings-encryption-wins",
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
            "name": "GitHubSource",
            "actionTypeId": {
              "category": "Source",
              "owner": "ThirdParty",
              "provider": "GitHub",
              "version": "1"
            },
            "configuration": {
              "Owner": "my-org",
              "Repo": "app",
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

Pipeline state (from get-pipeline-state):

```
stageStates:
  - stageName: Source
    inboundTransitionState:
      enabled: true
  - stageName: Deploy
    inboundTransitionState:
      enabled: false
      disabledReason: "Temporary freeze"
```

Artifact bucket SSE configuration: none (no server-side encryption configured).
