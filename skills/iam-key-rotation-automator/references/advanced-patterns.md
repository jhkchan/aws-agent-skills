# Advanced Patterns — IAM Key Rotation Automator

Step 0 expert-knowledge deep dive, the overlap-window principle, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

## Step 0: Expert knowledge — non-obvious IAM key behaviors

- **IAM allows exactly 2 access keys per user.** The rotation flow uses
  the second slot. If both are Active, the pipeline must first
  determine which can be deactivated — this is the most common blocker.

- **`get-access-key-last-used` is eventually consistent.** `LastUsedDate`
  may lag by up to 4 hours. A key that appears "unused" may have been
  used minutes ago. Always add a 24-hour buffer before deactivation.

- **Deactivating a key does NOT immediately revoke active sessions.**
  An application using the key may continue calling for minutes to
  hours after deactivation. The overlap window accounts for this.

- **Deleting a key is irreversible.** Any app still using it fails
  immediately with `InvalidClientTokenId`. Always verify the new key
  works AND the old key has not been used for N hours before deleting.

- **Credential reports are generated on demand and may be 4 hours
  stale.** For real-time data, use `list-access-keys` +
  `get-access-key-last-used`.

- **STS temporary credentials do NOT need rotation.** When an app
  assumes a role via STS, credentials are temporary (15min-12hr). No
  access key to rotate — this is the target architecture.

- **`create-access-key` returns the secret ONCE.** If lost, the key
  must be deactivated and recreated. Store immediately in Secrets
  Manager. NEVER log the secret.

- **Keys aged > 90 days trigger Security Hub findings.** Check IAM.7
  (key aged > 90 days) and IAM.6 (key never used). Use these as
  secondary detection signals.

## Recent AWS features (2024-2026)

- **Access Analyzer key findings (2024):** Flags external access to IAM
  keys, including third-party service usage. Integrates with rotation
  pipeline to identify exposed keys.
- **Security Hub IAM.7 enhanced (2024-2025):** The "key > 90 days" check
  now includes `LastUsedDate`, distinguishing active-aged from stale.
- **STS session tagging (2024):** Assumed-role sessions carry session
  tags for better attribution when migrating from permanent keys.
- **Credential report format (2025):** Now includes `last_rotated` and
  `last_used_region` columns for richer lifecycle analysis.

## Expert heuristic: the overlap-window principle

The single most important principle: **NEVER remove the old key until
you have verified the new key works in production.**

**The rule:** the pipeline MUST include an overlap window of at least
24 hours (7 days for production) where both keys are active. During
this window: (1) new key deployed, (2) app verified, (3) old key usage
monitored — if still used, app has NOT transitioned, (4) only after 24h
of old-key non-use is it deactivated, (5) only after 72h of successful
operation is it deleted.

**Why:** applications cache credentials. An app that reads the key at
startup won't pick up the new key until restarted. Without overlap,
deletion precedes restart — immediate `InvalidClientTokenId`.

**STS migration is the permanent fix.** The overlap window is correct
for rotation. But eliminating keys entirely via STS is the real fix.
