# Diagnostic Commands — Secrets Manager Rotation Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Pre-flight safety checks (run before any remediation CLI)

- **Read-only discovery first.** Before modifying anything, list all
  secrets and their rotation status:
  ```bash
  aws secretsmanager list-secrets --query 'SecretList[].[Name,RotationEnabled,LastRotatedDate]' --output table
  ```
  This gives the full inventory without side effects. For accounts with
  more than 100 secrets, paginate with `--starting-token` (the
  `list-secrets` API returns at most 100 results per call). Use the
  `--filter` flag to scope by tag or owning service to reduce noise:
  ```bash
  aws secretsmanager list-secrets --filters Key=tag-key,Values=rotated --max-results 100
  ```

- **Check for multi-Region replica secrets.** Before auditing, determine
  whether each secret is a primary or replica:
  ```bash
  aws secretsmanager describe-secret --secret-id <name> --query '[Name,PrimaryRegion]'
  ```
  If `PrimaryRegion` is set and the secret is in a different region, it is
  a replica — audit rotation only on the primary.

- **Capture the secret's current state for rollback:**
  ```bash
  aws secretsmanager describe-secret --secret-id <name> > /tmp/<name>-describe-$(date +%s).json
  aws secretsmanager list-secret-version-ids --secret-id <name> > /tmp/<name>-versions-$(date +%s).json
  ```
  These captures are critical for incident response — if a manual
  rotation fails and creates a credential mismatch, you need the
  pre-change version IDs to restore `AWSCURRENT`.

- **Verify Lambda state before enabling rotation:**
  ```bash
  aws lambda get-function --function-name <rotation-lambda>
  aws lambda get-policy --function-name <rotation-lambda>
  ```
  Confirm `State: Active` and the resource-based policy allows
  `secretsmanager.amazonaws.com` to invoke.

- **Prefer additive changes over destructive ones.** Enabling rotation,
  fixing the execution role, and increasing the Lambda timeout are
  reversible. Deleting a stuck `AWSPENDING` version is irreversible — do
  it only after confirming the credential is not live on the target.

- **For ROTATION_BROKEN with target deleted:** if the RDS/Redshift
  instance was deleted but the secret remains, the secret is orphaned.
  Do NOT force a rotation — there is no target to rotate against.
  Either delete the secret (if it is truly orphaned) or update it to
  point to the replacement resource first.

