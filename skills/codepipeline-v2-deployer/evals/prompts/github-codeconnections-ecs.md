# Eval prompt: github-codeconnections-ecs

Design a deployment plan for a V2 pipeline with GitHub source via
CodeConnections and ECS deploy. Emit the standard VERDICT block.

Requirements:

- Pipeline type: V2
- Region: us-east-1
- Pipeline name: my-service-github-ecs-pipeline
- Source: GitHub via CodeConnections
  - ConnectionArn:
    arn:aws:codeconnections:us-east-1:111111111111:connection/abc-123
    (state: AVAILABLE)
  - FullRepositoryId: my-org/my-service
  - BranchName: main
- Build: CodeBuild `my-service-build`, exports IMAGE_URI and IMAGE_TAG
  via buildspec exported-variables (builds and pushes Docker image to
  ECR)
- Deploy: ECS
  - ClusterName: prod-cluster
  - ServiceName: my-service
  - Image1: #{BuildVars.IMAGE_URI}
- Trigger: branch main, Tags Includes=["deploy=prod"] (only tagged
  releases deploy)
- Artifact bucket: my-pipeline-artifacts (block-public-access + KMS)
- Pipeline role: my-pipeline-role

Existing-account context: the CodeConnections connection was created
in us-east-1 and authorized via the GitHub OAuth flow. The CodeBuild
project, ECS cluster, ECS service, task definition family, KMS key,
and pipeline role all exist. The pipeline does NOT exist yet. The ECR
repository exists and the CodeBuild project has ecr:BatchCheckLayerAvailability
/ PutImage permissions.
