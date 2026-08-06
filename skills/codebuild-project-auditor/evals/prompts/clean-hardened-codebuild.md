# Eval prompt: clean-hardened-codebuild

Audit the following AWS CodeBuild project configuration and its
service-role identity-based + trust policies for security exposure. Emit
the standard VERDICT block (PROJECT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Project name: arn:aws:codebuild:us-east-1:111111111111:project/clean-hardened-codebuild

Project config (batch-get-projects output, abridged):

```json
{
  "name": "clean-hardened-codebuild",
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
      {"name": "DB_PASSWORD", "value": "arn:aws:secretsmanager:us-east-1:111111111111:secret:db-password-abc", "type": "SECRETS_MANAGER"}
    ],
    "secretsManager": [
      {"secretsManagerArn": "arn:aws:secretsmanager:us-east-1:111111111111:secret:db-password-abc", "name": "DB_PASSWORD", "type": "SECRETS_MANAGER"}
    ]
  },
  "serviceRole": "arn:aws:iam::111111111111:role/service-role/CodeBuild-clean-hardened-codebuild",
  "badgeEnabled": false,
  "logsConfig": {
    "cloudWatchLogs": {"status": "ENABLED"},
    "s3Logs": {
      "status": "ENABLED",
      "location": "arn:aws:s3:::codebuild-logs-bucket/clean-hardened-codebuild",
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

Service role identity-based policy (scoped, named actions):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["codebuild:CreateReport", "codebuild:UpdateReport", "codebuild:BatchPut*"],
      "Resource": "arn:aws:codebuild:us-east-1:111111111111:project/clean-hardened-codebuild"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::codebuild-logs-bucket/clean-hardened-codebuild/*"
    },
    {
      "Effect": "Allow",
      "Action": ["kms:GenerateDataKey*", "kms:Decrypt"],
      "Resource": "arn:aws:kms:us-east-1:111111111111:key/abc-123"
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:us-east-1:111111111111:secret:db-password-abc"
    }
  ]
}
```

Service role trust policy (scoped to project):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "codebuild.amazonaws.com"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceArn": "arn:aws:codebuild:us-east-1:111111111111:project/clean-hardened-codebuild"
        }
      }
    }
  ]
}
```
