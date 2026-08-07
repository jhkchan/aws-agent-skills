# Eval prompt: cdk-pipeline-with-blue-green-lambda-automated

Design a CDK pipeline that deploys a Lambda function with CodeDeploy
canary 10%/5min blue/green traffic shifting. Emit the standard
VERDICT block.

Operation: create
Pipeline name: cdk-lambda-bluegreen-pipeline
Template format: CDK (TypeScript)
Source: GitHub via CodeStar Connection (Available)
Deploy target: Lambda function with CodeDeploy canary 10%/5min
PreTrafficHook: pre-traffic-validator
PostTrafficHook: post-traffic-smoke-test
CodeDeploy application: prod-lambda-deploy
CodeDeploy deployment group: prod-lambda-dg
Deploy role: arn:aws:iam::111111111111:role/lambda-deploy

```json
{
  "RequirementChecks": {
    "codestar-connections.get-connection": {"ConnectionStatus": "Available"},
    "codedeploy.get-application.prod-lambda-deploy": {
      "computePlatform": "Lambda"
    },
    "codedeploy.get-deployment-group.prod-lambda-dg": {
      "deploymentStyle": {"deploymentType": "BLUE_GREEN", "deploymentOption": "WITH_TRAFFIC_CONTROL"}
    },
    "lambda.get-function.pre-traffic-validator": {"exists": true, "tested": "OK"},
    "lambda.get-function.post-traffic-smoke-test": {"exists": true, "tested": "OK"},
    "iam.get-role.lambda-deploy": {
      "managedPolicies": ["arn:aws:iam::aws:policy/service-role/AWSCodeDeployRoleForLambda"]
    },
    "codebuild.list-curated-environment-images.standard:8.0": {
      "supports": ["TypeScript"]
    }
  }
}
```
