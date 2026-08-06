# Eval prompt: multi-az-default-co-password

Audit the following AWS CloudHSM cluster configuration for posture exposure.
Emit the standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster id: cluster-multi-az-default-co-password
Cluster metadata:
  State: INITIALIZED
  HsmType: hsm1m.medium
  VpcId: vpc-0mno345
  CreateDate: 2026-07-01T10:00:00Z
  BackupRetentionPolicy:
    Type: DAYS
    Value: "90"
  SubnetMapping:
    us-east-1a: subnet-aaa555
    us-east-1b: subnet-bbb555
    us-east-1c: subnet-ccc555
  SecurityGroup:
    - sg-hsm005
HSMs:
  - HsmId: hsm-040
    AvailabilityZone: us-east-1a
    SubnetId: subnet-aaa555
    EniId: eni-040
    State: ACTIVE
  - HsmId: hsm-041
    AvailabilityZone: us-east-1b
    SubnetId: subnet-bbb555
    EniId: eni-041
    State: ACTIVE
  - HsmId: hsm-042
    AvailabilityZone: us-east-1c
    SubnetId: subnet-ccc555
    EniId: eni-042
    State: ACTIVE
Backups:
  - BackupId: backup-401
    CreateDate: 2026-08-04T16:00:00Z
    State: READY
  - BackupId: backup-402
    CreateDate: 2026-08-03T16:00:00Z
    State: READY
PKCS#11 management:
  co_password_changed: false
Security group rules (sg-hsm005):
  inbound:
    - source: 10.0.5.0/24
      ports: 2223-2225
