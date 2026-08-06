# Eval prompt: confused-deputy-with-source-arn

Audit the following IAM role trust policy for cross-account/external trust
exposure, confused-deputy risk, and condition-strength weaknesses. The
Principal is a service principal (lambda.amazonaws.com) WITH an
aws:SourceArn and aws:SourceAccount condition. Emit the standard VERDICT
block (ROLE, VERDICT, REASON, RISK, REMEDIATION).

Role name: confused-deputy-with-source-arn
Role ARN: arn:aws:iam::123456789012:role/confused-deputy-with-source-arn
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
      "Action": "sts:AssumeRole",
      "Condition": {
        "ArnLike": {
          "aws:SourceArn": "arn:aws:lambda:us-east-1:123456789012:function:*"
        },
        "StringEquals": {
          "aws:SourceAccount": "123456789012"
        }
      }
    }
  ]
}
```
