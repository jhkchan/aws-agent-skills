# Eval prompt: public-pull-wildcard-no-condition

Audit the following ECR repository configuration for security exposure. Emit
the standard VERDICT block (REPO, VERDICT, REASON, FINDINGS, REMEDIATION).

Repository: 111111111111.dkr.ecr.us-east-1.amazonaws.com/public-pull-wildcard-no-condition
Registry ID: 111111111111
imageScanningConfiguration:
  scanOnPush: true
imageTagMutability: IMMUTABLE
lifecyclePolicyText: present

Repository policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicPull",
      "Effect": "Allow",
      "Principal": "*",
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchCheckLayerAvailability"
      ],
      "Resource": "*"
    }
  ]
}
```
