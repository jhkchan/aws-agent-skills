# Eval prompt: confused-deputy-no-source

Audit the following IAM role trust policy for cross-account/external trust
exposure, confused-deputy risk, and condition-strength weaknesses. The
Principal is a service principal (lambda.amazonaws.com) with no source-guard
condition. Emit the standard VERDICT block (ROLE, VERDICT, REASON, RISK,
REMEDIATION).

Role name: confused-deputy-no-source
Role ARN: arn:aws:iam::123456789012:role/confused-deputy-no-source
Trust policy (AssumeRolePolicyDocument):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```
