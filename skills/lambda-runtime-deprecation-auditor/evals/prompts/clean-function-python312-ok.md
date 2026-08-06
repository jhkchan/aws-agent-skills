# Eval prompt: clean-function-python312-ok

Audit the following Lambda function configuration for security and
operational posture. Emit the standard VERDICT block (FUNCTION, VERDICT,
REASON, FINDINGS, REMEDIATION).

Function name: clean-function-python312-ok
Function configuration:
  Runtime: python3.12
  Handler: app.handler
  CodeSize: 3072
  PackageType: Zip
  Architectures: [arm64]
  LastModified: 2025-12-01T08:00:00.000+0000
  TracingConfig:
    Mode: Active
  Timeout: 60
  MemorySize: 512
  DeadLetterConfig:
    TargetArn: arn:aws:sqs:us-east-1:111111111111:lambda-dlq

Execution role: arn:aws:iam::111111111111:role/lambda-clean-role
Execution role policies (attached managed + inline):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::app-data-prod/*"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:111111111111:log-group:/aws/lambda/clean-function-python312-ok:*"
    }
  ]
}
```

Function URL config: (none — not configured)
