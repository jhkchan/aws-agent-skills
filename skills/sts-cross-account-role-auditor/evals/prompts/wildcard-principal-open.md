# Eval prompt: wildcard-principal-open

Audit the following IAM role trust policy for cross-account/external trust
exposure, confused-deputy risk, and condition-strength weaknesses. Emit the
standard VERDICT block (ROLE, VERDICT, REASON, RISK, REMEDIATION).

Role name: wildcard-principal-open
Role ARN: arn:aws:iam::123456789012:role/wildcard-principal-open
Trust policy (AssumeRolePolicyDocument):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sts:AssumeRole"
    }
  ]
}
```
