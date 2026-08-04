# Eval prompt: config-gap-no-lifecycle

Audit the following EFS filesystem configuration for security exposure.
Emit the standard VERDICT block (FILESYSTEM, VERDICT, REASON, FINDINGS,
REMEDIATION).

Filesystem id: fs-2abc34567890 (config-gap-no-lifecycle)
Filesystem ARN: arn:aws:elasticfilesystem:us-east-1:111111111111:file-system/fs-2abc34567890
Filesystem metadata:
  Encrypted: true
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/def-456-789
  PerformanceMode: generalPurpose
  LifecyclePolicies: (none)
  Access points: 1 (fsap-bbb — root directory /data/share)

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
      "Resource": "*",
      "Condition": {
        "Bool": {"aws:SecureTransport": "true"}
      }
    }
  ]
}
```
