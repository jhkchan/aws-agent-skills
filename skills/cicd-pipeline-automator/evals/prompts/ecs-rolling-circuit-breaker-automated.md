# Eval prompt: ecs-rolling-circuit-breaker-automated

Design a CloudFormation CI/CD pipeline for an ECS service deploy with
circuit breaker rollback. Emit the standard VERDICT block.

Operation: create
Pipeline name: ecs-rolling-pipeline
Template format: CloudFormation
Source: CodeCommit
Repository: checkout-service
Branch: main
Build image: aws/codebuild/standard:8.0
Deploy target: ECS cluster prod-cluster, service checkout-service
  (DeploymentCircuitBreaker: Enable=true, Rollback=true)

```json
{
  "RequirementChecks": {
    "codecommit.get-repository.checkout-service": {"exists": true},
    "ecr.describe-repositories.checkout-service": {"exists": true},
    "ecs.describe-services.prod-cluster.checkout-service": {
      "deploymentConfiguration": {
        "deploymentCircuitBreaker": {"enable": true, "rollback": true}
      }
    },
    "iam.get-role.checkout-ecs-deploy": {
      "TrustPolicy": "ecs-tasks.amazonaws.com (OK)",
      "Policies": ["AmazonECSTaskExecutionRolePolicy", "custom ecr:GetAuthorizationToken"]
    },
    "kms.describe-key": {
      "policy_grants": ["pipeline role", "deploy role"]
    },
    "s3api.get-bucket-versioning": {"Status": "Enabled"}
  }
}
```
