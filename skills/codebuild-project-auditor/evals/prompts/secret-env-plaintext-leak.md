# Eval prompt: secret-env-plaintext-leak

Audit the following AWS CodeBuild project configuration for security
exposure. Emit the standard VERDICT block (PROJECT, VERDICT, REASON,
FINDINGS, REMEDIATION).

Project name: arn:aws:codebuild:us-east-1:111111111111:project/secret-env-plaintext-leak

Project config (batch-get-projects output, abridged):

```json
{
  "name": "secret-env-plaintext-leak",
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
      {"name": "NODE_ENV", "value": "test", "type": "PLAINTEXT"},
      {"name": "DB_PASSWORD", "value": "Sup3r$ecret#2026-abc123XYZ", "type": "PLAINTEXT"},
      {"name": "GITHUB_TOKEN", "value": "ghp_abcDEF1234567890XYZ", "type": "PLAINTEXT"}
    ]
  },
  "serviceRole": "arn:aws:iam::111111111111:role/service-role/CodeBuild-secret-env-leak",
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
