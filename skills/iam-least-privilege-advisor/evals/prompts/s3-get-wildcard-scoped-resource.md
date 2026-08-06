# Eval prompt: s3-get-wildcard-scoped-resource

Classify the following IAM policy document against least-privilege principles.
This case exercises the wildcard-action-on-scoped-resource edge: the resource
is a concrete bucket ARN, but the actions use read-level wildcards. Emit the
standard VERDICT block (POLICY, VERDICT, REASON, RISK, REMEDIATION).

Policy name: s3-get-wildcard-scoped-resource
Policy document:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:Get*",
        "s3:List*"
      ],
      "Resource": [
        "arn:aws:s3:::app-data-prod",
        "arn:aws:s3:::app-data-prod/*"
      ]
    }
  ]
}
```
