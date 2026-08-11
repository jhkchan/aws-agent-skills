# Baseline (no-skill) response: github-codeconnections-ecs

This file captures what a generic assistant produces WITHOUT the
codepipeline-v2-deployer skill loaded. The contrast proves the skill
adds the CodeConnections contract (connection in us-east-1, AVAILABLE
state, FullRepositoryId format), the ECS deploy action namespace
variable contract (Image1=#{BuildVars.IMAGE_URI}), and the buildspec
exported-variables requirement.

---

Here's a plan for your GitHub + ECS pipeline.

Architecture:

- V2 pipeline in us-east-1
- Source: GitHub my-org/my-service
- Build: CodeBuild my-service-build
- Deploy: ECS prod-cluster / my-service

Steps:

1. Create a CodeConnections connection to GitHub.
2. Configure the source action with the connection ARN.
3. Configure CodeBuild to build and push the image.
4. Configure ECS deploy with the new image.

For the ECS deploy, you can reference the image URI from the build
output.

Commands:

```
aws codeconnections create-connection ...
aws codepipeline create-pipeline --cli-input-json file://pipeline.json
```

The connection needs to be authorized via the console before the
pipeline can use it.
