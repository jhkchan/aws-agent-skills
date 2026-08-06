# End-to-end usage scenario: cloudhsm-cluster-posture-auditor

A walkthrough showing the skill auditing a CloudHSM cluster that has three
HSMs all co-located in a single AZ (SINGLE_AZ), demonstrating the key
knowledge delta that HSM count alone is not HA, and the assume-failure
remediation workflow.

## Input (user prompt)

> Review this CloudHSM cluster before we attach it to the production payment
> processing system. It hosts the master keys for PCI-DSS card vault
> encryption.

```yaml
Cluster id: cluster-prod-payment-hsm
Cluster metadata:
  State: INITIALIZED
  HsmType: hsm1m.medium
  VpcId: vpc-0pay001
  CreateDate: 2026-01-15T10:00:00Z
  BackupRetentionPolicy:
    Type: DAYS
    Value: "90"
  SubnetMapping:
    us-east-1a: subnet-pay-a
    us-east-1b: subnet-pay-b
    us-east-1c: subnet-pay-c
  SecurityGroup:
    - sg-hsm-pay
HSMs:
  - HsmId: hsm-pay-01
    AvailabilityZone: us-east-1a
    SubnetId: subnet-pay-a
    EniId: eni-pay-01
    State: ACTIVE
  - HsmId: hsm-pay-02
    AvailabilityZone: us-east-1a
    SubnetId: subnet-pay-a
    EniId: eni-pay-02
    State: ACTIVE
  - HsmId: hsm-pay-03
    AvailabilityZone: us-east-1a
    SubnetId: subnet-pay-a
    EniId: eni-pay-03
    State: ACTIVE
Backups:
  - BackupId: backup-pay-101
    CreateDate: 2026-08-04T12:00:00Z
    State: READY
  - BackupId: backup-pay-102
    CreateDate: 2026-08-03T12:00:00Z
    State: READY
PKCS#11 management:
  co_password_changed: true
  quorum_enabled: true
Security group rules (sg-hsm-pay):
  inbound:
    - source: 10.10.1.0/24
      ports: 2223-2225
```

## Skill output

```text
CLUSTER: cluster-prod-payment-hsm
VERDICT: SINGLE_AZ
REASON: All 3 HSMs reside in a single AZ (us-east-1a) — an AZ-level event
(power, network, cooling) takes the entire cluster offline with no cross-AZ
failover, despite the HSM-level redundancy. For a PCI-DSS payment system,
this is an unacceptable single point of failure.
FINDINGS:
  - [SINGLE_AZ] 3 HSMs in us-east-1a only — HSM count does NOT substitute
    for AZ distribution (Step 1). The SubnetMapping includes 3 AZs but all
    HSMs were created in us-east-1a only.
  - [OK] Backup posture: 2 recent READY backups, retention DAYS=90 (Step 2)
  - [OK] Cluster State=INITIALIZED, CO password changed, quorum enabled,
    security group scoped to 10.10.1.0/24 (Step 3)
REMEDIATION:
  1. Create HSMs in the other two AZs immediately — the subnets already
     exist:
     aws cloudhsm create-hsm --cluster-id cluster-prod-payment-hsm
       --availability-zone us-east-1b --subnet-id subnet-pay-b
     aws cloudhsm create-hsm --cluster-id cluster-prod-payment-hsm
       --availability-zone us-east-1c --subnet-id subnet-pay-c
  2. Verify new HSMs reach ACTIVE state and synchronise keys before
     considering HA achieved (check via describe-clusters).
  3. After cross-AZ distribution, re-audit to confirm SINGLE_AZ is resolved.
  4. If this cluster is a KMS Custom Key Store, KMS Encrypt/Decrypt calls
     are already failing intermittently during AZ events — treat as
     incident-response priority.
```

## Key insight demonstrated

The most dangerous misjudgment in CloudHSM auditing is treating HSM count
as a proxy for HA. An operator seeing "3 HSMs" might conclude the cluster
is highly available. The skill's Step 0 expert knowledge and Step 1
classification catch this: the `AvailabilityZone` field across all HSMs is
`us-east-1a`, making this SINGLE_AZ regardless of the 3-HSM count. The
`SubnetMapping` even includes 3 AZs — but no HSMs were actually placed in
subnets-pay-b or subnet-pay-c, a deployment gap that looks configured but
isn't exercised.
