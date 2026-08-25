# Diagnostic Commands (load on demand) — CodeBuild Project Auditor

Pre-flight and diagnostic command listings moved verbatim from SKILL.md. Load on demand.

---

## Pre-flight safety checks — snapshot and verify commands (moved from SKILL.md)

- **Snapshot the current project config for rollback:**
  `aws codebuild batch-get-projects --names <name> --output json > /tmp/<name>-backup-$(date +%s).json`
  BEFORE any modification. CodeBuild project configs are NOT versioned —
  there is no undo without a backup.
- **Snapshot the service-role policy for rollback:**
  `aws iam list-role-policies --role-name <role> --output json > /tmp/<role>-inline-$(date +%s).json`
  and
  `aws iam list-attached-role-policies --role-name <role> --output json > /tmp/<role>-attached-$(date +%s).json`.
  Inline and attached IAM policies are not versioned by default — a
  `put-role-policy` replaces inline content atomically with no rollback.
- **Verify the build is not currently running** before disabling
  `privilegedMode` on a Docker-build project. An in-flight Docker build
  will fail mid-flight when privilegedMode flips. Use
  `aws codebuild batch-get-builds --ids <build-id>` to check status.
- **Confirm the Secrets Manager secret exists and is resolvable** before
  moving a plaintext env var to `secretsManager`. A broken secret
  reference breaks the build. Use
  `aws secretsmanager describe-secret --secret-id <id>` first.
- **Prefer additive changes** (add a condition, scope a resource) over
  destructive changes (remove a statement, delete a variable) — additive
  changes are reversible and do not risk breaking existing builds.

