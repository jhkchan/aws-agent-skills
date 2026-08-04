# Eval prompt: admin-wildcard-role-nodejs20

Audit the following Lambda function configuration for security and
operational posture. Emit the standard VERDICT block (FUNCTION, VERDICT,
REASON, FINDINGS, REMEDIATION).

Function name: admin-wildcard-role-nodejs20
Function configuration:
  Runtime: nodejs20.x
  Handler: index.handler
  CodeSize: 2048
  PackageType: Zip
  Architectures: [x86_64]
  LastModified: 2025-06-20T14:00:00.000+0000
  TracingConfig:
    Mode: Active
  Timeout: 15
  MemorySize: 256

Execution role: arn:aws:iam::111111111111:role/lambda-admin-role
Execution role policies (attached managed + inline):

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

Function URL config: (none — not configured)
