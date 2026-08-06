# Eval prompt: privileged-dind-no-docker

Audit the following AWS CodeBuild project configuration for security
exposure. Emit the standard VERDICT block (PROJECT, VERDICT, REASON,
FINDINGS, REMEDIATION).

Project name: arn:aws:codebuild:us-east-1:111111111111:project/privileged-dind-no-docker

Project config (batch-get-projects output, abridged):

```json
{
  "name": "privileged-dind-no-docker",
  "source": {
    "type": "CODECOMMIT",
    "buildspec": "version: 0.2\nphases:\n  build:\n    commands:\n      - mvn clean install\n      - aws s3 cp target/app.jar s3://artifacts-bucket/"
  },
  "environment": {
    "type": "LINUX_CONTAINER",
    "image": "aws/codebuild/standard:7.0",
    "computeType": "BUILD_GENERAL1_SMALL",
    "privilegedMode": true
  },
  "serviceRole": "arn:aws:iam::111111111111:role/service-role/CodeBuild-privileged-dind-no-docker",
  "badgeEnabled": false,
  "logsConfig": {
    "cloudWatchLogs": {"status": "ENABLED"},
    "s3Logs": {"status": "DISABLED"}
  },
  "artifacts": {"encryptionDisabled": false},
  "vpcConfig": {
    "vpcId": "vpc-aaa",
    "subnets": ["subnet-private-1", "subnet-private-2"],
    "securityGroupIds": ["sg-build-egress-only"]
  }
}
```
