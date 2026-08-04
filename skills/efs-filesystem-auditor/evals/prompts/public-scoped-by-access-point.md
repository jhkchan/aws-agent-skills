# Eval prompt: public-scoped-by-access-point

Audit the following EFS filesystem configuration for security exposure.
Emit the standard VERDICT block (FILESYSTEM, VERDICT, REASON, FINDINGS,
REMEDIATION).

Filesystem id: fs-5def67890123 (public-scoped-by-access-point)
Filesystem ARN: arn:aws:elasticfilesystem:us-east-1:111111111111:file-system/fs-5def67890123
Filesystem metadata:
  Encrypted: true
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/mno-678-901
  PerformanceMode: generalPurpose
  LifecyclePolicies:
    - TransitionToIA: AFTER_14_DAYS
  Access points: 1 (fsap-fff — root directory /shared/multi-tenant, PosixUser Uid=1000 Gid=1000)

Filesystem policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AccessPointOnly",
      "Effect": "Allow",
      "Principal": "*",
      "Action": [
        "elasticfilesystem:ClientMount",
        "elasticfilesystem:ClientWrite"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "elasticfilesystem:AccessPointArn": "arn:aws:elasticfilesystem:us-east-1:111111111111:access-point/fsap-fff"
        },
        "Bool": {"aws:SecureTransport": "true"}
      }
    }
  ]
}
```
