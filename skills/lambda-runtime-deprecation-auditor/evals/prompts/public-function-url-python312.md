# Eval prompt: public-function-url-python312

Audit the following Lambda function configuration for security and
operational posture. Emit the standard VERDICT block (FUNCTION, VERDICT,
REASON, FINDINGS, REMEDIATION).

Function name: public-function-url-python312
Function configuration:
  Runtime: python3.12
  Handler: app.lambda_handler
  CodeSize: 4096
  PackageType: Zip
  Architectures: [x86_64]
  LastModified: 2025-11-01T09:15:00.000+0000
  TracingConfig:
    Mode: Active
  Timeout: 60
  MemorySize: 512

Execution role: arn:aws:iam::111111111111:role/lambda-api-role
Execution role policies (attached managed + inline):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["dynamodb:Query", "dynamodb:GetItem"],
      "Resource": "arn:aws:dynamodb:us-east-1:111111111111:table/app-table"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:111111111111:log-group:/aws/lambda/public-function-url-python312:*"
    }
  ]
}
```

Function URL config:
  FunctionUrl: https://abc123def456.lambda-url.us-east-1.on.aws
  AuthType: NONE
  Cors:
    AllowOrigins: ["*"]
    AllowMethods: ["GET", "POST"]
    AllowHeaders: ["content-type"]
