# Diagnostic Commands (load on demand) — EKS Cluster Auditor

Pre-flight, diagnostic, and verification command listings moved verbatim from SKILL.md. Loaded on demand.

---

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (update-cluster-config, kubectl edit configmap, security group
  modification), the auditor MUST emit:
  `CONFIRM: About to <action> on cluster <name> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **aws-auth ConfigMap backup.** Before any `mapRoles` edit:
  `kubectl get configmap aws-auth -n kube-system -o yaml > /tmp/aws-auth-backup-$(date +%s).yaml`
  A malformed ConfigMap is the most common cause of total cluster lockout.

- **Endpoint access change blast radius.** Disabling public endpoint
  access breaks all `kubectl` sessions originating outside the VPC.
  Verify VPN/bastion connectivity BEFORE the change, not after.

- **Logging enablement cost.** Enabling control-plane logs creates
  CloudWatch Log Groups with ingestion + storage charges. Estimate
  volume first: a busy production cluster can generate 50-200 GB/day of
  audit logs.

- **Version upgrade prerequisites.** Before recommending a version
  upgrade: (1) check add-on compatibility (`aws eks describe-addon-
  versions`), (2) check pod security standards / admission controller
  changes, (3) check deprecated API usage (`kubectl convert` / `kubent`),
  (4) verify the target version is available in the cluster's region.
