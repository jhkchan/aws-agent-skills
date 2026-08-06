---
description: Audit an AWS CloudHSM cluster for HA posture (cross-AZ HSM distribution), backup readiness (retention, recency, restorability), PKCS#11 user management (CO password, quorum), cluster initialization (certificate signing), and network exposure.
nl_triggers:
  - "audit this CloudHSM cluster"
  - "check CloudHSM HA posture"
  - "CloudHSM backup readiness"
  - "CloudHSM single AZ risk"
  - "CloudHSM cluster initialized"
  - "CloudHSM PKCS#11 audit"
  - "harden CloudHSM cluster"
  - "CloudHSM CO password"
  - "CloudHSM backup retention"
  - "CloudHSM security group"
  - "is my HSM highly available"
  - "CloudHSM cluster posture"
  - "CloudHSM certificate signing"
routes_to: cloudhsm-cluster-posture-auditor
---

# /aws:audit-cloudhsm-cluster

Activate the `cloudhsm-cluster-posture-auditor` skill and audit one or more
AWS CloudHSM cluster configurations for security and operational posture.

## What it does

Reads a CloudHSM cluster configuration (from `describe-clusters` output plus
PKCS#11 management metadata) and applies the ordered classification logic:

1. Pre-flight cluster metadata gate — short-circuit clusters in
   CREATE_IN_PROGRESS or DELETE_IN_PROGRESS.
2. Cluster HA / AZ distribution — all HSMs in one AZ is SINGLE_AZ regardless
   of HSM count (HSM count is NOT a proxy for HA).
3. Backup posture — retention DAYS=0 disables backups; zero backups or stale
   backups (>7 days) are NO_BACKUP.
4. Configuration posture — UNINITIALIZED cluster state, default CO password
   unchanged, open security group on ports 2223-2225, missing quorum.
5. Aggregation — worst finding wins (SINGLE_AZ > NO_BACKUP > CONFIG_GAP > OK).

Emits a deterministic VERDICT per cluster:

```text
CLUSTER: <cluster-id>
VERDICT: SINGLE_AZ | NO_BACKUP | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [SINGLE_AZ] <finding description (Step 1)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a CloudHSM cluster configuration and ask any of:

- "audit this CloudHSM cluster"
- "is my HSM cluster highly available?"
- "check CloudHSM backup readiness"
- "CloudHSM single AZ risk"
- "is the cluster initialized?"
- "CloudHSM PKCS#11 user audit"

A bare cluster ID + any audit verb ("audit this cluster", "check posture")
also routes here via the orchestrator.

## Inputs

- A CloudHSM cluster configuration (YAML or JSON), pasted inline or
  referenced by file path. Include: State, HsmType, BackupRetentionPolicy,
  SubnetMapping, SecurityGroup, HSMs (with AvailabilityZone + State), and
  PKCS#11 management metadata (co_password_changed, quorum_enabled).
- For live-account audits: the auditor calls `aws cloudhsm describe-clusters`
  and `aws cloudhsm describe-backups` automatically.

## Outputs

- One VERDICT block per cluster (multiple findings aggregate to the worst
  severity).
- Enumerated FINDINGS list with per-finding verdict and step citation.
- Specific remediation: add cross-AZ HSMs, set backup retention, initialize
  cluster, change CO password, scope security group.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for CloudHSM security).
- `/aws:audit-kms-key-policy` for KMS key policy analysis — relevant when
  the CloudHSM cluster is a KMS Custom Key Store.
