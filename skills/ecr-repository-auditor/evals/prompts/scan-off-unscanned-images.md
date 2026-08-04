# Eval prompt: scan-off-unscanned-images

Audit the following ECR repository configuration for security exposure. Emit
the standard VERDICT block (REPO, VERDICT, REASON, FINDINGS, REMEDIATION).

Repository: 111111111111.dkr.ecr.us-east-1.amazonaws.com/scan-off-unscanned-images
Registry ID: 111111111111
imageScanningConfiguration:
  scanOnPush: false
imageTagMutability: IMMUTABLE
lifecyclePolicyText: present
Images:
  - imageDigest: sha256:aaa, imageTags: ["v1.0"], imageScanStatus: null
  - imageDigest: sha256:bbb, imageTags: ["v1.1"], imageScanStatus: {"status": "PENDING"}

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
