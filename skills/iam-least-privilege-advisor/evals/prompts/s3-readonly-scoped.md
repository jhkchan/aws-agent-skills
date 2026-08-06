# Eval prompt: s3-readonly-scoped

Classify the following IAM policy document against least-privilege principles.
Emit the standard VERDICT block (POLICY, VERDICT, REASON, RISK, REMEDIATION).

Policy name: s3-readonly-scoped
Policy document:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::app-data-prod",
        "arn:aws:s3:::app-data-prod/*"
      ]
    }
  ]
}
```
