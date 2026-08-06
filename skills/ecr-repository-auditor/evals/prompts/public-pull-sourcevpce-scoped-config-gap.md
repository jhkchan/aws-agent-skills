# Eval prompt: public-pull-sourcevpce-scoped-config-gap

Audit the following ECR repository configuration for security exposure. Emit
the standard VERDICT block (REPO, VERDICT, REASON, FINDINGS, REMEDIATION).

Repository: 111111111111.dkr.ecr.us-east-1.amazonaws.com/public-pull-sourcevpce-scoped-config-gap
Registry ID: 111111111111
imageScanningConfiguration:
  scanOnPush: true
imageTagMutability: IMMUTABLE
lifecyclePolicyText: present
Images:
  - imageDigest: sha256:fff, imageTags: ["v4.0"], imageScanStatus: {"status": "COMPLETE"}

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
    },
    {
      "Sid": "VpceScopedPull",
      "Effect": "Allow",
      "Principal": "*",
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:SourceVpce": "vpce-abc123def456"
        }
      }
    }
  ]
}
```
