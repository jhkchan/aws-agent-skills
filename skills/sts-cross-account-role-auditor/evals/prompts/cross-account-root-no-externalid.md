# Eval prompt: cross-account-root-no-externalid

Audit the following IAM role trust policy for cross-account/external trust
exposure, confused-deputy risk, and condition-strength weaknesses. The role
is in account 123456789012 and the Principal references account
999999999999 (a different account). Emit the standard VERDICT block (ROLE,
VERDICT, REASON, RISK, REMEDIATION).

Role name: cross-account-root-no-externalid
Role ARN: arn:aws:iam::123456789012:role/cross-account-root-no-externalid
Trust policy (AssumeRolePolicyDocument):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::999999999999:root"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```
