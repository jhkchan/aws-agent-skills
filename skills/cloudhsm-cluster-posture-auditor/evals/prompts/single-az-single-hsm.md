# Eval prompt: single-az-single-hsm

Audit the following AWS CloudHSM cluster configuration for posture exposure.
Emit the standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster id: cluster-single-az-single-hsm
Cluster metadata:
  State: INITIALIZED
  HsmType: hsm1m.medium
  VpcId: vpc-0abc123
  CreateDate: 2026-06-01T10:00:00Z
  BackupRetentionPolicy:
    Type: DAYS
    Value: "0"
  SubnetMapping:
    us-east-1a: subnet-aaa111
  SecurityGroup:
    - sg-hsm001
HSMs:
  - HsmId: hsm-001
    AvailabilityZone: us-east-1a
    SubnetId: subnet-aaa111
    EniId: eni-001
    State: ACTIVE
Backups: []
PKCS#11 management:
  co_password_changed: true
Security group rules (sg-hsm001):
  inbound:
    - source: 10.0.1.0/24
      ports: 2223-2225
