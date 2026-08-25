# Diagnostic and Pre-flight Commands — MSK Cluster Auditor

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (update-cluster-configuration, broker storage update, cluster
  deletion), the auditor MUST emit:
  `CONFIRM: About to <action> on cluster <name> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **Encryption immutability awareness.** Before recommending encryption
  remediation, verify the operator understands that MSK encryption
  settings CANNOT be changed in-place. The remediation path is: create
  new cluster with TLS → mirror topics → validate → cut over consumers
  → decommission old cluster. This is a multi-day operation, not a
  one-line CLI fix.

- **Public access toggle blast radius.** Disabling public access
  (`PublicAccess.Type: DISABLED`) immediately breaks all clients
  connecting via the Elastic IPs. Verify VPN/Direct Connect/bastion
  connectivity BEFORE the change.

- **Logging enablement cost.** Enabling broker log delivery to
  CloudWatch creates log groups with ingestion charges. A busy MSK
  cluster with many partitions generates significant broker log volume.
  Estimate volume first and set a retention policy:
  `aws logs put-retention-policy --log-group-name <name>
  --retention-in-days 90`.

- **Configuration change propagation.** MSK configuration changes
  (update-cluster-configuration) trigger a rolling broker restart. The
  cluster remains available (other brokers serve traffic), but
  partition leadership shifts during the rollout. Schedule during a
  maintenance window.

