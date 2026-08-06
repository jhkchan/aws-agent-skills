# Eval prompt: multi-az-uninitialized

Audit the following AWS CloudHSM cluster configuration for posture exposure.
Emit the standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster id: cluster-multi-az-uninitialized
Cluster metadata:
  State: UNINITIALIZED
  HsmType: hsm1m.medium
  VpcId: vpc-0jkl012
  CreateDate: 2026-08-01T10:00:00Z
  BackupRetentionPolicy:
    Type: DAYS
    Value: "90"
  SubnetMapping:
    us-east-1a: subnet-aaa444
    us-east-1b: subnet-bbb444
    us-east-1c: subnet-ccc444
  SecurityGroup:
    - sg-hsm004
HSMs:
  - HsmId: hsm-030
    AvailabilityZone: us-east-1a
    SubnetId: subnet-aaa444
    EniId: eni-030
    State: ACTIVE
  - HsmId: hsm-031
    AvailabilityZone: us-east-1b
    SubnetId: subnet-bbb444
    EniId: eni-031
    State: ACTIVE
  - HsmId: hsm-032
    AvailabilityZone: us-east-1c
    SubnetId: subnet-ccc444
    EniId: eni-032
    State: ACTIVE
Backups:
  - BackupId: backup-301
    CreateDate: 2026-08-04T14:00:00Z
    State: READY
PKCS#11 management:
  co_password_changed: false
Security group rules (sg-hsm004):
  inbound:
    - source: 10.0.4.0/24
      ports: 2223-2225
