# Diagnostic and Pre-flight Commands — Redshift Cluster Auditor


## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any destructive or
  state-changing operation (`modify-cluster`, `reboot-cluster`,
  `enable-logging`, `disable-logging`, `delete-cluster`,
  `modify-cluster-snapshot-schedule`), the auditor MUST emit:
  `CONFIRM: About to <action> on cluster <id> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. This
  gate prevents automated pipelines from silently modifying data
  warehouses.
- **Reboot warnings.** `modify-cluster` changes to
  `ClusterParameterGroupName`, `EnhancedVPCRouting`, `PubliclyAccessible`,
  or `Encrypted` (not supported — see Step 2) require a cluster reboot.
  Reboots terminate in-flight queries, fail over leader-node connections,
  and may take 10-30 minutes on large clusters. Surface this BEFORE the
  operator approves.
- **Encryption migration is irreversible and multi-day.** A NO_ENCRYPTION
  remediation involves provisioning a new cluster, UNLOAD/COPY migration,
  application cutover, and decommissioning. Do NOT represent this as a
  one-step CLI command. Provide the full migration workflow and warn
  that downstream BI tools must be repointed.
- **Snapshot before parameter-group or routing changes.** Capture the
  current state with a manual snapshot before modifying the parameter
  group or enhanced VPC routing:
  `aws redshift create-snapshot-cluster-schedule` or
  `aws redshift create-cluster-snapshot --cluster-identifier <id>
  --snapshot-identifier pre-audit-<id>-$(date +%s)`.
  This is the rollback path if the new PG breaks query patterns.
- **Confirm audit-log bucket ownership.** Before
  `aws redshift enable-logging`, verify the S3 bucket exists, is in the
  expected account, has object-lock or appropriate retention, and the
  Redshift service principal can write to it. Misconfigured buckets
  silently fail logging with no error surfaced in `describe-logging-status`
  beyond `LoggingEnabled: false` and `LogFileLastWritten` stalling.
- **Cross-region snapshot copy has cost implications.** Enabling
  `modify-snapshot-copy-destination` incurs cross-region data transfer
  + snapshot storage in the DR region. Surface the cost estimate before
  recommending.
- **Pre-flight for SG changes.** Before
  `aws ec2 revoke-security-group-ingress`, verify no other cluster or
  service shares the SG. Shared SGs are common in legacy Redshift
  deployments — revoking a rule may break adjacent workloads. Use
  `aws ec2 describe-network-interfaces --groups <sg-id>` to check
  associations first.
