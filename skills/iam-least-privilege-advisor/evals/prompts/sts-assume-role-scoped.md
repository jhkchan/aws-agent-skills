# Eval prompt: sts-assume-role-scoped

Classify the following IAM policy document against least-privilege principles.
Note: AssumeRole is a privilege-escalation action, but here it is scoped to a
specific role ARN. Emit the standard VERDICT block (POLICY, VERDICT, REASON,
RISK, REMEDIATION).

Policy name: sts-assume-role-scoped
Policy document:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::123456789012:role/cross-audit-role"
    }
  ]
}
```
