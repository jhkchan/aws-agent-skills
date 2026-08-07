# Baseline (no-skill) response: ecs-rolling-circuit-breaker-automated

This file captures what a generic assistant produces WITHOUT the
cicd-pipeline-automator skill loaded.

---

To create a CI/CD pipeline for your ECS service with circuit breaker
rollback:

```yaml
Resources:
  Pipeline:
    Type: AWS::CodePipeline::Pipeline
    Properties:
      RoleArn: !GetAtt PipelineRole.Arn
      Stages:
        - Name: Source
          Actions:
            - Name: Source
              ActionTypeId:
                Category: Source
                Owner: AWS
                Provider: CodeCommit
                Version: 1
              Configuration:
                RepositoryName: checkout-service
                BranchName: main
        - Name: Build
          Actions:
            - Name: Build
              ActionTypeId:
                Category: Build
                Owner: AWS
                Provider: CodeBuild
                Version: 1
        - Name: Deploy
          Actions:
            - Name: Deploy
              ActionTypeId:
                Category: Deploy
                Owner: AWS
                Provider: ECS
                Version: 1
              Configuration:
                ClusterName: prod-cluster
                ServiceName: checkout-service
```

The ECS service should have circuit breaker enabled in its deployment
configuration.
