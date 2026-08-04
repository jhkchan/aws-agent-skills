# Eval prompt: unencrypted-fs

Audit the following EFS filesystem configuration for security exposure.
Emit the standard VERDICT block (FILESYSTEM, VERDICT, REASON, FINDINGS,
REMEDIATION).

Filesystem id: fs-0abc123456789 (unencrypted-fs)
Filesystem ARN: arn:aws:elasticfilesystem:us-east-1:111111111111:file-system/fs-0abc123456789
Filesystem metadata:
  Encrypted: false
  PerformanceMode: generalPurpose
  ThroughputMode: bursting
  LifecyclePolicies:
    - TransitionToIA: AFTER_30_DAYS
  Access points: 1 (fsap-aaa — root directory /prod/app)
Filesystem policy: none (IAM-governed)
