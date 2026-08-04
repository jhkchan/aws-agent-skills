# Eval prompt: public-policy-wildcard

Audit the following EFS filesystem configuration for security exposure.
Emit the standard VERDICT block (FILESYSTEM, VERDICT, REASON, FINDINGS,
REMEDIATION).

Filesystem id: fs-1def789012345 (public-policy-wildcard)
Filesystem ARN: arn:aws:elasticfilesystem:us-east-1:111111111111:file-system/fs-1def789012345
Filesystem metadata:
  Encrypted: true
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/abc-def-123
  PerformanceMode: generalPurpose
  LifecyclePolicies:
    - TransitionToIA: AFTER_30_DAYS
  Access points: 0

Filesystem policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "OpenMount",
      "Effect": "Allow",
      "Principal": "*",
      "Action": [
        "elasticfilesystem:ClientMount",
        "elasticfilesystem:ClientWrite",
        "elasticfilesystem:ClientRootAccess"
      ],
      "Resource": "*"
    }
  ]
}
```
