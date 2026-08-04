# Eval prompt: s3-poweruser-wildcard-resource

Classify the following IAM policy document against least-privilege principles.
Emit the standard VERDICT block (POLICY, VERDICT, REASON, RISK, REMEDIATION).

Policy name: s3-poweruser-wildcard-resource
Policy document:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": "*"
    }
  ]
}
```
