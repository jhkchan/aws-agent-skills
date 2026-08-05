---
description: Audit an Amazon Redshift provisioned cluster for public accessibility, KMS encryption-at-rest, require_ssl parameter-group enforcement, S3 audit logging, automated-snapshot retention, enhanced VPC routing, and VPC security-group ingress on the cluster port — emits VERDICT per cluster.
nl_triggers:
  - "audit this Redshift cluster"
  - "is my Redshift cluster public"
  - "is encryption enabled on Redshift"
  - "is require_ssl on"
  - "Redshift audit logging"
  - "are automated snapshots on"
  - "Redshift enhanced VPC routing"
  - "Redshift security group audit"
  - "harden this data warehouse"
  - "PubliclyAccessible true"
  - "Encrypted false"
  - "require_ssl false"
  - "LoggingEnabled false"
  - "AutomatedSnapshotRetentionPeriod zero"
  - "EnhancedVPCRouting false"
  - "Redshift config gap"
  - "data warehouse security audit"
routes_to: redshift-cluster-auditor
---

# /aws:audit-redshift-cluster

Activate the `redshift-cluster-auditor` skill and audit one or more Amazon
Redshift provisioned clusters for security exposure and configuration gaps.

## What it does

Reads a Redshift cluster configuration (describe-clusters metadata,
optionally paired with describe-logging-status, describe-cluster-parameters
for the attached parameter group, and describe-security-groups for the
attached SGs) and applies the ordered classification logic:

1. Public accessibility — `PubliclyAccessible: true` is PUBLIC (an
   internet-exposed petabyte-scale data warehouse on TCP 5439/5440; the
   highest-impact Redshift misconfiguration).
2. Encryption-at-rest — `Encrypted: false` is NO_ENCRYPTION (immutable
   post-creation; remediation is a new-cluster + UNLOAD/COPY migration,
   not a toggle).
3. Parameter group `require_ssl` — value `false` (engine default) is
   NO_SSL (clients may connect over plaintext; default PG is read-only
   and cannot be modified in place).
4. Audit logging — `LoggingEnabled: false` is NO_AUDIT_LOG (no S3 audit
   trail; CloudTrail covers only control-plane events, not SQL queries).
5. Configuration gaps — additive CONFIG_GAP findings for snapshot
   retention 0 (PITR disabled), EnhancedVPCRouting false (COPY/UNLOAD
   bypasses VPC controls), SG `0.0.0.0/0` on cluster port, user-activity
   logging off.
6. Aggregation — worst finding wins
   (PUBLIC > NO_ENCRYPTION > NO_SSL > NO_AUDIT_LOG > CONFIG_GAP > OK).

Redshift Serverless workgroups have a different API surface (no
`PubliclyAccessible`, no `ClusterParameterGroupName`) — the skill defers
with an ERROR routing note rather than misclassifying.

Emits a deterministic VERDICT per cluster:

```text
CLUSTER: <cluster-identifier>
VERDICT: PUBLIC | NO_ENCRYPTION | NO_SSL | NO_AUDIT_LOG | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [PUBLIC] <finding description (Step 1)>
  - [CONFIG_GAP] <finding description (Step 5)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Redshift cluster configuration and ask any of:

- "audit this Redshift cluster"
- "is my Redshift cluster public?"
- "is encryption enabled on this cluster?"
- "is require_ssl on?"
- "is Redshift audit logging configured?"
- "are automated snapshots enabled?"
- "is enhanced VPC routing on?"
- "is the cluster security group exposed?"

A bare cluster identifier + any audit verb ("audit this data warehouse",
"check Redshift config") also routes here via the orchestrator.

## Inputs

- Cluster metadata: ClusterIdentifier, ClusterStatus, NodeType,
  NumberOfNodes, PubliclyAccessible, Encrypted, KmsKeyId,
  EnhancedVPCRouting, ClusterParameterGroupName,
  ClusterParameterGroupStatus, AutomatedSnapshotRetentionPeriod,
  VpcSecurityGroups, ElasticIpStatus, Endpoint.Port,
  ClusterSnapshotCopyStatus, HsmClientCertificateIdentifier.
- Parameter group parameters: ParameterName, ParameterValue, Source for
  `require_ssl` and `enable_user_activity_logging`.
- Logging status: LoggingEnabled, BucketName, S3KeyPrefix.
- Security group ingress: IpProtocol, FromPort, ToPort, IpRanges for
  each attached SG.
- For live-account audits: the skill references `describe-clusters`,
  `describe-logging-status`, `describe-cluster-parameters`,
  `describe-security-groups`, and (when CMK is in use) `kms describe-key`.

## Outputs

- One VERDICT block per cluster (multiple findings aggregate to the
  worst-severity verdict in priority order).
- Enumerated FINDINGS list with per-finding verdict tag and step
  citation.
- Specific remediation: flip PubliclyAccessible (with reboot caveat),
  plan an encryption migration (UNLOAD/COPY workflow), create a custom
  PG with require_ssl, enable S3 audit logging, raise snapshot
  retention, enable EnhancedVPCRouting, restrict the SG.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Redshift / analytics security).
- `/aws:audit-kms-key-policy` for auditing the KMS key policy when the
  cluster uses a customer-managed KMS key for encryption-at-rest.
- `/aws:audit-ec2-security-groups` for deeper SG analysis (prefix lists,
  cross-VPC exposure).
- `/aws:audit-s3-public-access` for auditing the S3 bucket receiving
  UNLOAD exports or audit logs — a private cluster with a public UNLOAD
  bucket silently exfiltrates data.
