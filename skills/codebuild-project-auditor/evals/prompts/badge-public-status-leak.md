# Eval prompt: badge-public-status-leak

Audit the following AWS CodeBuild project configuration and its service
role identity-based policy for security exposure. Emit the standard
VERDICT block (PROJECT, VERDICT, REASON, FINDINGS, REMEDIATION).

Project name: arn:aws:codebuild:us-east-1:111111111111:project/badge-public-status-leak

Project config (batch-get-projects output, abridged):

```json
{
  "name": "badge-public-status-leak",
  "source": {
    "type": "GITHUB",
    "buildspec": "version: 0.2\nphases:\n  build:\n    commands:\n      - npm ci && npm test"
  },
  "environment": {
    "type": "LINUX_CONTAINER",
    "image": "aws/codebuild/standard:7.0",
    "computeType": "BUILD_GENERAL1_SMALL",
    "privilegedMode": false,
    "environmentVariables": [
      {"name": "NODE_ENV", "value": "test", "type": "PLAINTEXT"}
    ]
  },
  "serviceRole": "arn:aws:iam::111111111111:role/service-role/CodeBuild-badge-public-status-leak",
  "badgeEnabled": true,
  "logsConfig": {
    "cloudWatchLogs": {"status": "ENABLED"},
    "s3Logs": {
      "status": "ENABLED",
      "location": "arn:aws:s3:::codebuild-logs-bucket/badge-public-status-leak",
      "encryptionDisabled": false,
      "kmsKeyArn": "arn:aws:kms:us-east-1:111111111111:key/abc-123"
    }
  },
  "artifacts": {"encryptionDisabled": false},
  "vpcConfig": {
    "vpcId": "vpc-aaa",
    "subnets": ["subnet-private-1", "subnet-private-2"],
    "securityGroupIds": ["sg-build-egress-only"]
  }
}
```

Service role identity-based policy (scoped):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["codebuild:CreateReport", "codebuild:UpdateReport", "codebuild:BatchPut*"],
      "Resource": "arn:aws:codebuild:us-east-1:111111111111:project/badge-public-status-leak"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::codebuild-logs-bucket/badge-public-status-leak/*"
    }
  ]
}
```
