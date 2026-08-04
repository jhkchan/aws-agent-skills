# Eval prompt: missing-tracing-nodejs20

Audit the following Lambda function configuration for security and
operational posture. Emit the standard VERDICT block (FUNCTION, VERDICT,
REASON, FINDINGS, REMEDIATION).

Function name: missing-tracing-nodejs20
Function configuration:
  Runtime: nodejs20.x
  Handler: index.handler
  CodeSize: 1536
  PackageType: Zip
  Architectures: [arm64]
  LastModified: 2025-09-10T12:00:00.000+0000
  TracingConfig:
    Mode: PassThrough
  Timeout: 30
  MemorySize: 512

Execution role: arn:aws:iam::111111111111:role/lambda-processor-role
Execution role policies (attached managed + inline):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
      "Resource": "arn:aws:sqs:us-east-1:111111111111:task-queue"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:111111111111:log-group:/aws/lambda/missing-tracing-nodejs20:*"
    }
  ]
}
```

Function URL config: (none — not configured)
