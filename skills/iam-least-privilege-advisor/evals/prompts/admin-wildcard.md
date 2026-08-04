# Eval prompt: admin-wildcard

Classify the following IAM policy document against least-privilege principles.
Emit the standard VERDICT block (POLICY, VERDICT, REASON, RISK, REMEDIATION).

Policy name: admin-wildcard
Policy document:

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
