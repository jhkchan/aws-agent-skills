# Eval prompt: multi-az-backup-ok

Audit the following AWS CloudHSM cluster configuration for posture exposure.
Emit the standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster id: cluster-multi-az-backup-ok
Cluster metadata:
  State: INITIALIZED
  HsmType: hsm2m.medium
  VpcId: vpc-0pqr678
  CreateDate: 2026-03-15T10:00:00Z
  BackupRetentionPolicy:
    Type: DAYS
    Value: "90"
  SubnetMapping:
    us-east-1a: subnet-aaa666
    us-east-1b: subnet-bbb666
    us-east-1c: subnet-ccc666
  SecurityGroup:
    - sg-hsm006
HSMs:
  - HsmId: hsm-050
    AvailabilityZone: us-east-1a
    SubnetId: subnet-aaa666
    EniId: eni-050
    State: ACTIVE
  - HsmId: hsm-051
    AvailabilityZone: us-east-1b
    SubnetId: subnet-bbb666
    EniId: eni-051
    State: ACTIVE
  - HsmId: hsm-052
    AvailabilityZone: us-east-1c
    SubnetId: subnet-ccc666
    EniId: eni-052
    State: ACTIVE
Backups:
  - BackupId: backup-501
    CreateDate: 2026-08-05T06:00:00Z
    State: READY
  - BackupId: backup-502
    CreateDate: 2026-08-04T06:00:00Z
    State: READY
  - BackupId: backup-503
    CreateDate: 2026-08-03T06:00:00Z
    State: READY
PKCS#11 management:
  co_password_changed: true
  quorum_enabled: true
Security group rules (sg-hsm006):
  inbound:
    - source: 10.0.6.0/24
      ports: 2223-2225
