# Worked examples - CodePipeline V2 Deployer (load on demand)

## Step 2 - Source action: CodeCommit config example

**CodeCommit source:**
```yaml
- Name: Source
  Actions:
    - Name: Source
      ActionTypeId: {Category: Source, Owner: AWS, Provider: CodeCommit, Version: 1}
      Configuration: {RepositoryName: my-service, BranchName: main}
      OutputArtifacts: [{Name: SourceOutput}]
```

## Step 2 - Source action: GitHub via CodeConnections example

**GitHub via CodeConnections:**
```yaml
- Name: Source
  Actions:
    - Name: Source
      ActionTypeId: {Category: Source, Owner: AWS, Provider: CodeStarSourceConnection, Version: 1}
      Configuration:
        ConnectionArn: arn:aws:codeconnections:us-east-1:111111111111:connection/abc-123
        FullRepositoryId: my-org/my-service
        BranchName: main
      OutputArtifacts: [{Name: SourceOutput}]
```

## Step 3 - Trigger configuration example (event-driven filter)

```yaml
Triggers:
  - ProviderType: CodeStarSourceConnection
    GitConfiguration:
      SourceActionName: Source
      Push:
        - Branches: {Includes: [main, "release/*"]}
          FilePaths: {Includes: [src/**], Excludes: [docs/**, README.md]}
          Tags: {Includes: ["deploy=prod"]}
```

## Step 4 - Build action example (CodeBuild + Namespace)

```yaml
- Name: Build
  Actions:
    - Name: Build
      ActionTypeId: {Category: Build, Owner: AWS, Provider: CodeBuild, Version: 1}
      Configuration: {ProjectName: my-service-build}
      InputArtifacts: [{Name: SourceOutput}]
      OutputArtifacts: [{Name: BuildOutput}]
      Namespace: BuildVars
```

## Step 4 - buildspec exported-variables example

```yaml
env:
  exported-variables: [IMAGE_TAG, BUILD_VERSION]
phases:
  build:
    commands:
      - export IMAGE_TAG=$(git rev-parse --short HEAD)
```

## Step 5 - CloudFormation deploy action example

**CloudFormation deploy action:**
```yaml
- Name: Deploy
  Actions:
    - Name: DeployCFN
      ActionTypeId: {Category: Deploy, Owner: AWS, Provider: CloudFormation, Version: 1}
      Configuration:
        ActionMode: CREATE_REPLACE
        StackName: prod-my-service
        TemplatePath: BuildOutput::template.yaml
        Capabilities: CAPABILITY_IAM,CAPABILITY_NAMED_IAM
        RoleArn: arn:aws:iam::<target-account>:role/CloudFormationExecution
      InputArtifacts: [{Name: BuildOutput}]
      Namespace: DeployVars
```

## Step 6 - Manual approval gate example

```yaml
- Name: Approval
  Actions:
    - Name: ApproveProd
      ActionTypeId: {Category: Approval, Owner: AWS, Provider: Manual, Version: 1}
      Configuration:
        ExternalEntityLink: https://internal.example.com/change-record/CHG12345
        CustomData: "Approve to deploy to prod. SNS topic arn:aws:sns:us-east-1:111111111111:prod-approval"
```

