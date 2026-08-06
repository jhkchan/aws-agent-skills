# Eval prompt: overpermissive-build-role

Audit the following AWS CodeBuild project configuration and its service
role identity-based policy for security exposure. Emit the standard
VERDICT block (PROJECT, VERDICT, REASON, FINDINGS, REMEDIATION).

Project name: arn:aws:codebuild:us-east-1:111111111111:project/overpermissive-build-role

Project config (batch-get-projects output, abridged):

```json
{
  "name": "overpermissive-build-role",
  "source": {
    "type": "CODECOMMIT",
    "buildspec": "version: 0.2\nphases:\n  build:\n    commands:\n      - ./build.sh"
  },
  "environment": {
    "type": "LINUX_CONTAINER",
    "image": "aws/codebuild/standard:7.0",
    "computeType": "BUILD_GENERAL1_SMALL",
    "privilegedMode": false,
    "environmentVariables": [
      {"name": "APP_ENV", "value": "ci", "type": "PLAINTEXT"}
    ]
  },
  "serviceRole": "arn:aws:iam::111111111111:role/service-role/CodeBuild-overpermissive-build-role",
  "badgeEnabled": false,
  "logsConfig": {
    "cloudWatchLogs": {"status": "ENABLED"},
    "s3Logs": {
      "status": "ENABLED",
      "location": "arn:aws:s3:::codebuild-logs-bucket/overpermissive-build-role",
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

Service role identity-based policy (CodeBuild-overpermissive-build-role):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "*",
      "Resource": "*"
    }
  ]
}
```
