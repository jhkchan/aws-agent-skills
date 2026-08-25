# Error Handling (load on demand) — EKS Add-On Deployer

Error-handling deep dives and API failure tables moved verbatim from SKILL.md. Loaded on demand.

---

## Error handling (moved from SKILL.md)

- **`InvalidParameterException` on create-addon:** Add-on version
  incompatible with cluster K8s version. Run `describe-addon-versions`
  to find a valid version. Also check the add-on name spelling.
- **Add-on status `DEGRADED` after creation:** Conflict with self-
  managed add-on. Check `describe-addon --query 'addon.healthIssues'`.
  Resolve by updating with `--resolve-conflicts OVERWRITE` or fixing
  the conflicting resource.
- **Pods get `AccessDenied` / `Unauthorized` on AWS API:** IRSA trust
  policy has wrong service account name or OIDC URL. Verify the trust
  policy matches the add-on's service account. For Pod Identity, verify
  the association exists and the agent is running.
- **`ConfigurationConflict` on update:** `--configuration-values`
  conflicts with existing self-managed config. Use `--resolve-conflicts
  PRESERVE` to merge, or `OVERWRITE` to replace.
- **Add-on reverts to default after manual config:** Cluster uses Auto
  Mode which reconciles managed add-ons. Do not manually configure Auto
  Mode-managed add-ons. Use cluster-level settings instead.
- **PVC provisioning fails after EBS CSI add-on:** Missing IAM role.
  Create an IRSA role for `ebs-csi-controller-sa` with the
  `AmazonEBSCSIDriverPolicy` (or appropriate custom policy) and
  re-create the add-on with `--service-account-role-arn`.
