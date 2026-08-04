# Eval prompt: cross-account-with-externalid

Audit the following IAM role trust policy for cross-account/external trust
exposure, confused-deputy risk, and condition-strength weaknesses. The role
is in account 123456789012, the Principal references account 999999999999
(a different account), and the statement includes an sts:ExternalId condition.
Emit the standard VERDICT block (ROLE, VERDICT, REASON, RISK, REMEDIATION).

Role name: cross-account-with-externalid
Role ARN: arn:aws:iam::123456789012:role/cross-account-with-externalid
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
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "a1b2c3d4e5f6g7h8i9j0kLmNoPqRsTuV"
        }
      }
    }
  ]
}
```
