# Eval prompt: disabled-stage-transition

Audit the following CodePipeline pipeline definition for security exposure.
Emit the standard VERDICT block (PIPELINE, VERDICT, REASON, FINDINGS, REMEDIATION).

Pipeline name: disabled-stage-transition
Pipeline definition (JSON):

```json
{
  "pipeline": {
    "name": "disabled-stage-transition",
    "roleArn": "arn:aws:iam::111111111111:role/service-role-AWS-CodePipeline-Service",
    "artifactStore": {
      "type": "S3",
      "location": "codepipeline-us-east-1-111111111111-store",
      "encryptionKey": {
        "id": "arn:aws:kms:us-east-1:111111111111:key/def-456-ghi",
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
              "ConnectionArn": "arn:aws:codestar-connections:us-east-1:111111111111:connection/src-123",
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

Pipeline state (from get-pipeline-state):

```
stageStates:
  - stageName: Source
    inboundTransitionState:
      enabled: true
  - stageName: Deploy
    inboundTransitionState:
      enabled: false
      disabledReason: "Freeze for incident investigation — do not re-enable until INC-1234 is resolved"
```

Artifact bucket SSE: SSE-KMS with the CMK referenced above.
