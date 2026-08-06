# Eval prompt: same-account-scoped-ok

Audit the following IAM role trust policy for cross-account/external trust
exposure, confused-deputy risk, and condition-strength weaknesses. The role
is in account 123456789012 and the Principal references a role ARN in the
same account. Emit the standard VERDICT block (ROLE, VERDICT, REASON, RISK,
REMEDIATION).

Role name: same-account-scoped-ok
Role ARN: arn:aws:iam::123456789012:role/same-account-scoped-ok
Trust policy (AssumeRolePolicyDocument):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/app-ci-runner"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```
