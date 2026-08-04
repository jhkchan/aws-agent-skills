# Eval prompt: config-gap-no-tls

Audit the following EFS filesystem configuration for security exposure.
Emit the standard VERDICT block (FILESYSTEM, VERDICT, REASON, FINDINGS,
REMEDIATION).

Filesystem id: fs-3def45678901 (config-gap-no-tls)
Filesystem ARN: arn:aws:elasticfilesystem:us-east-1:111111111111:file-system/fs-3def45678901
Filesystem metadata:
  Encrypted: true
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/ghi-012-345
  PerformanceMode: generalPurpose
  LifecyclePolicies:
    - TransitionToIA: AFTER_30_DAYS
  Access points: 1 (fsap-ccc — root directory /logs/archive)

Filesystem policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AppAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/app-efs-role"},
      "Action": [
        "elasticfilesystem:ClientMount",
        "elasticfilesystem:ClientWrite"
      ],
      "Resource": "*"
    }
  ]
}
```
