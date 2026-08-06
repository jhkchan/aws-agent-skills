# Eval prompt: s3-logs-no-kms-encryption

Audit the following AWS CodeBuild project configuration for security
exposure. Emit the standard VERDICT block (PROJECT, VERDICT, REASON,
FINDINGS, REMEDIATION).

Project name: arn:aws:codebuild:us-east-1:111111111111:project/s3-logs-no-kms-encryption

Project config (batch-get-projects output, abridged):

```json
{
  "name": "s3-logs-no-kms-encryption",
  "source": {
    "type": "CODECOMMIT",
    "buildspec": "version: 0.2\nphases:\n  build:\n    commands:\n      - ./gradlew build"
  },
  "environment": {
    "type": "LINUX_CONTAINER",
    "image": "aws/codebuild/standard:7.0",
    "computeType": "BUILD_GENERAL1_SMALL",
    "privilegedMode": false
  },
  "serviceRole": "arn:aws:iam::111111111111:role/service-role/CodeBuild-s3-logs-no-kms-encryption",
  "badgeEnabled": false,
  "logsConfig": {
    "cloudWatchLogs": {"status": "DISABLED"},
    "s3Logs": {
      "status": "ENABLED",
      "location": "arn:aws:s3:::codebuild-logs-bucket/s3-logs-no-kms-encryption",
      "encryptionDisabled": true
    }
  },
  "artifacts": {"encryptionDisabled": true},
  "vpcConfig": {
    "vpcId": "vpc-aaa",
    "subnets": ["subnet-private-1", "subnet-private-2"],
    "securityGroupIds": ["sg-build-egress-only"]
  }
}
```
