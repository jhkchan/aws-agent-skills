# Advanced Patterns — Redshift Cluster Auditor


## Step 0: Expert knowledge — non-obvious Redshift behaviours that change classification

These behaviours are easy to misjudge without operational Redshift experience.
Each changes a verdict if ignored:

- **`PubliclyAccessible: false` does NOT mean "no internet exposure" if a
  NAT Gateway + routing path exists.** Redshift with
  `PubliclyAccessible: false` is unreachable from the public internet
  (no public IP assigned). However, `COPY` from / `UNLOAD` to public S3
  endpoints still traverses the internet unless `EnhancedVPCRouting:
  true` is set. The two flags are independent — privacy of the *cluster
  endpoint* and privacy of the *data-path for bulk transfers* are
  separate concerns.

- **`require_ssl` parameter applies to client connections, not intra-
  cluster traffic.** Setting `require_ssl: true` forces SQL clients to
  connect over TLS. It does NOT encrypt the wire between compute nodes
  (which is always TLS-protected internally on RA3 / Serverless) and
  does NOT encrypt `COPY`/`UNLOAD` traffic (which is HTTPS to S3
  regardless). The compliance question "is TLS enforced?" is answered
  by this parameter for client connections.

- **The default parameter group is read-only.** `default.redshift-1.0`
  cannot be modified. A cluster using the default PG with
  `require_ssl: false` and `Source: engine-default` is reporting the
  Redshift engine default — the operator may not have actively decided.
  Remediation requires creating a custom PG, setting `require_ssl: true`,
  associating it with the cluster, AND rebooting. Treat the
  `Source: engine-default` signal as "operator has not hardened this"
  rather than "operator chose plaintext".

- **`Encrypted: true` + `KmsKeyId: null` uses the AWS-managed key
  `aws/redshift`.** The AWS-managed key rotates annually on AWS's
  schedule, has a policy controlled by AWS, and cannot be cross-account
  shared. Compliance frameworks (PCI-DSS, HIPAA, SOC 2) generally accept
  AWS-managed keys, but high-assurance audits require customer-managed
  keys for rotation control. Note the distinction in FINDINGS; do NOT
  flag the AWS-managed key as a security gap.

- **Encryption is immutable per cluster.** Unlike RDS (snapshot + copy
  toggles encryption) or EBS (online modify), Redshift encryption is
  fixed at cluster creation. To "enable" encryption on an unencrypted
  cluster you must: (1) provision a new encrypted cluster, (2) `UNLOAD`
  data to S3 (prefer Parquet with columnar compression), (3) `COPY`
  into the new cluster, (4) redirect downstream BI / ETL tools, (5)
  decommission the old cluster once queries validated. This is a
  multi-day migration, not a CLI toggle. State this explicitly in
  remediation — operators asking "can I just flip encryption on?" must
  be corrected.

- **`AutomatedSnapshotRetentionPeriod: 0` deletes existing automated
  snapshots within hours.** Setting retention to zero does NOT just stop
  future snapshots — Redshift begins expiring existing automated
  snapshots immediately (typically within the next snapshot window,
  ~1 hour). Manual snapshots are NOT affected. If an operator sets
  retention to 0 to "save cost" without first converting critical
  automated snapshots to manual, they lose PITR irreversibly.

- **`AutomatedSnapshotRetentionPeriod` range is 0 to 35.** Values above
  35 are rejected by the API. The default is 1 day (effectively
  overnight-only recovery). Compliance postures typically require 7+;
  35 is the maximum. Manual snapshots have no retention cap and persist
  until explicitly deleted.

- **`enable_user_activity_logging` is a parameter-group setting distinct
  from `aws redshift enable-logging`.** The `enable-logging` API
  exports audit events (connections, DDL, DML authorisation checks) to
  S3 in near-real-time. The `enable_user_activity_logging` parameter
  logs every SQL statement to the STL_QUERY system table at high
  volume. Both are needed for full forensic coverage: enable-logging
  gives you a tamper-evident S3 trail; user_activity_logging gives you
  the full query text. Treat `enable-logging` off as NO_AUDIT_LOG; treat
  `enable_user_activity_logging` off as an additive CONFIG_GAP finding.

- **`EnhancedVPCRouting: false` is the engine default.** With it off,
  `COPY` and `UNLOAD` traffic leaves the cluster over the public AWS
  network path to S3 (HTTPS, still encrypted, but not subject to your
  VPC's security groups, network ACLs, or VPC endpoints). With it on,
  that traffic flows through your VPC, enabling S3 Gateway VPC endpoint
  enforcement. Many compliance frameworks require EnhancedVPCRouting on
  because it closes the "data-path bypasses network controls" gap.

- **The Redshift cluster port defaults to 5439, not 5432.** A common
  misconfiguration copies RDS-style SG rules permitting TCP 5432 from
  app CIDRs, which silently fail to permit any traffic. Conversely,
  `0.0.0.0/0` on TCP 5439 is the canonical "cluster open to the world"
  SG rule. The port is configurable at cluster creation
  (`ClusterPort`, range 1150-65535); JK SecureListen deployments use
  5440. Always read the actual port from `Endpoint.Port`, not assume.

- **Snapshot copy grants cross-region DR but is configured separately.**
  `ClusterSnapshotCopyStatus` (present on the cluster) reports whether
  automated snapshots are copied to a DR region. Absent
  `DestinationRegion` is a DR gap (not a security verdict driver, but
  noted in FINDINGS as resilience).

- **A paused cluster still incurs storage charges and still has its
  encryption + SG posture.** Pause is a cost-optimisation action, not a
  security control. Do not treat paused clusters as safer; their
  configuration dimensions audit identically to available clusters.

- **`PubliclyAccessible: true` on a single-node cluster is the worst-
  case Redshift exposure.** Single-node clusters have no replication
  and no HA — an attacker with the credentials (or a CVE) has access to
  the entire dataset with no redundancy to recover from destructive
  queries. Treat as PUBLIC with an additional operational risk note.

- **CloudTrail logs Redshift *control-plane* events (CreateCluster,
  ModifyCluster, DeleteCluster) by default.** It does NOT log data-
  plane SQL queries — that is what `enable-logging` (S3 audit logs) is
  for. "We have CloudTrail, so we have audit coverage" is a false
  belief for Redshift data-plane activity.

## Edge-case handling

- **Cluster in `modifying` / `rebooting` state.** Audit normally. Note
  in FINDINGS that parameter-group changes may be pending; the verdict
  reflects the *current effective* state, not the pending one.

- **Cluster using `default.redshift-1.0` parameter group.** Default PGs
  are read-only — `require_ssl` and `enable_user_activity_logging`
  cannot be modified in place. Remediation requires creating a custom
  PG, associating, and rebooting. Surface this explicitly so operators
  do not attempt `modify-cluster-parameter-group` on the default PG
  (which fails).

- **Multi-AZ deployment.** `MultiAZ: true` (on supported node types) is
  an availability dimension, not a security dimension. Note its presence
  or absence as an operational finding; do not let it drive the verdict.

- **RA3 vs DC2 / DS2 node types.** DS2 (dense storage) is end-of-life
  and being forcibly retired. DC2 (dense compute) is current for
  compute-bound workloads. RA3 (managed storage) is the recommended
  current generation with separated compute + storage. Flag DS2 in
  FINDINGS as a deprecation risk (operational, not a verdict driver).

- **HSM-encrypted legacy cluster.** `HsmClientCertificateIdentifier` set
  + `Encrypted: true` indicates pre-2017 HSM-managed encryption. Treat
  as Encrypted OK for Step 2; flag in FINDINGS that HSM integration is
  deprecated and the cluster should be migrated to KMS-managed
  encryption.

- **ClusterSnapshotCopyStatus present.** Cross-region snapshot copy is
  configured. Note in FINDINGS as a positive resilience signal. Absent
  on a production cluster is a CONFIG_GAP (resilience, not security).

- **Redshift Serverless input.** Serverless workgroups do not have
  `PubliclyAccessible` or `ClusterParameterGroupName`. They have a
  `config-parameters` list including `require_ssl` and the base network
  is always VPC-only. Do NOT attempt to apply this skill to Serverless —
  emit ERROR with a routing note.

- **Cluster with `KmsKeyId: null` AND `Encrypted: true`.** AWS-managed
  key in use. Treat as Encrypted OK; note the AWS-managed vs
  customer-managed distinction in FINDINGS. Recommend CMK for
  high-assurance compliance postures.

- **`Endpoint.Port` is non-default.** Always read the cluster port from
  `Endpoint.Port` (range 1150-65535). SG rules matching TCP 5439 are
  the canonical check, but if the cluster uses 5440 (JK SecureListen)
  or any custom port, evaluate SG ingress on the actual port.

## Recent AWS features (2024-2026)

- **Redshift Serverless GA and enhanced (2024-2025):** Redshift Serverless auto-scales compute based on workload. Auditors should note that Serverless workgroups have a different audit surface than provisioned clusters — verify encryption, VPC security groups, and `maxRPU` (base capacity) settings at the workgroup level.
- **Zero-ETL integration with Aurora (2024-2025):** Redshift now supports Zero-ETL integration that replicates Aurora data to Redshift automatically. Auditors should verify that the Zero-ETL integration IAM role is scoped appropriately and that data replication does not bypass encryption requirements.
- **Data sharing enhancements (2024):** Improved cross-namespace and cross-account data sharing. Auditors should verify that data share consumers have appropriate Lake Formation or Redshift-scoped permissions and that consumer namespaces are documented.
- **Redshift ML improvements (2024):** Enhanced SageMaker integration for ML model creation from Redshift. Auditors should verify that the Redshift-SageMaker IAM role does not have wildcard permissions.
