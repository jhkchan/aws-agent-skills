# Eval prompt: multi-az-no-backup

Audit the following AWS CloudHSM cluster configuration for posture exposure.
Emit the standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster id: cluster-multi-az-no-backup
Cluster metadata:
  State: INITIALIZED
  HsmType: hsm1m.medium
  VpcId: vpc-0ghi789
  CreateDate: 2026-06-10T10:00:00Z
  BackupRetentionPolicy:
    Type: DAYS
    Value: "0"
  SubnetMapping:
    us-east-1a: subnet-aaa333
    us-east-1b: subnet-bbb333
    us-east-1c: subnet-ccc333
  SecurityGroup:
    - sg-hsm003
HSMs:
  - HsmId: hsm-020
    AvailabilityZone: us-east-1a
    SubnetId: subnet-aaa333
    EniId: eni-020
    State: ACTIVE
  - HsmId: hsm-021
    AvailabilityZone: us-east-1b
    SubnetId: subnet-bbb333
    EniId: eni-021
    State: ACTIVE
  - HsmId: hsm-022
    AvailabilityZone: us-east-1c
    SubnetId: subnet-ccc333
    EniId: eni-022
    State: ACTIVE
Backups: []
PKCS#11 management:
  co_password_changed: true
Security group rules (sg-hsm003):
  inbound:
    - source: 10.0.3.0/24
      ports: 2223-2225
