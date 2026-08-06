# Eval prompt: same-az-three-hsm

Audit the following AWS CloudHSM cluster configuration for posture exposure.
Emit the standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster id: cluster-same-az-three-hsm
Cluster metadata:
  State: INITIALIZED
  HsmType: hsm1m.medium
  VpcId: vpc-0def456
  CreateDate: 2026-05-15T08:00:00Z
  BackupRetentionPolicy:
    Type: DAYS
    Value: "90"
  SubnetMapping:
    us-east-1a: subnet-aaa222
  SecurityGroup:
    - sg-hsm002
HSMs:
  - HsmId: hsm-010
    AvailabilityZone: us-east-1a
    SubnetId: subnet-aaa222
    EniId: eni-010
    State: ACTIVE
  - HsmId: hsm-011
    AvailabilityZone: us-east-1a
    SubnetId: subnet-aaa222
    EniId: eni-011
    State: ACTIVE
  - HsmId: hsm-012
    AvailabilityZone: us-east-1a
    SubnetId: subnet-aaa222
    EniId: eni-012
    State: ACTIVE
Backups:
  - BackupId: backup-101
    CreateDate: 2026-08-04T12:00:00Z
    State: READY
  - BackupId: backup-102
    CreateDate: 2026-08-03T12:00:00Z
    State: READY
PKCS#11 management:
  co_password_changed: true
Security group rules (sg-hsm002):
  inbound:
    - source: 10.0.2.0/24
      ports: 2223-2225
