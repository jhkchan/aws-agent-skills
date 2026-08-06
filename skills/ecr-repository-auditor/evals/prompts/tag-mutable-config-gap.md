# Eval prompt: tag-mutable-config-gap

Audit the following ECR repository configuration for security exposure. Emit
the standard VERDICT block (REPO, VERDICT, REASON, FINDINGS, REMEDIATION).

Repository: 111111111111.dkr.ecr.us-east-1.amazonaws.com/tag-mutable-config-gap
Registry ID: 111111111111
imageScanningConfiguration:
  scanOnPush: true
imageTagMutability: MUTABLE
lifecyclePolicyText: present
Images:
  - imageDigest: sha256:ddd, imageTags: ["v2.0"], imageScanStatus: {"status": "COMPLETE"}

Repository policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RootAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": "ecr:*",
      "Resource": "*"
    }
  ]
}
```
