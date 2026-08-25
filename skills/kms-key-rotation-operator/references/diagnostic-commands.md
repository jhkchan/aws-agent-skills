# Diagnostic Commands — kms-key-rotation-operator

Pre-flight and diagnostic command listings moved verbatim from SKILL.md.

## Pre-flight: pagination + live-account pre-flight

**Pagination:** `list-keys` paginates at 100/page — drain
`--marker`/`--next-marker` to completion. `list-grants` paginates at
50/page. `list-aliases` paginates at 100/page.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws kms describe-key --key-id <id>` — capture `KeyState`,
   `Enabled`, `KeyUsage`, `KeySpec`, `Origin`,
   `MultiRegionConfiguration`, `CreationDate`, `Description`,
   `DeletionDate` (if pending).
2. `aws kms get-key-rotation-status --key-id <id>` — capture
   `Enabled` (rotation status), `RotationPeriodInSeconds`,
   `NextRotationDate` (if enabled).
3. `aws kms get-key-policy --key-id <id> --policy-name default` —
   capture the policy; verify the caller's role has
   `kms:EnableKeyRotation` or that the caller is the root admin.
4. `aws kms list-grants --key-id <id>` — capture all grants.
   Rotation does not invalidate grants, but verify there are no
   ` retiring` grants that could affect behavior.
5. `aws kms list-aliases --key-id <id>` — capture aliases pointing
   to this key. Aliases are the application-facing name; rotation
   does not affect aliases.
6. `aws cloudtrail lookup-events --lookup-attributes
   AttributeKey=ResourceName,AttributeValue=<key-arn>
   --attribute-key EventSource --attribute-value kms.amazonaws.com
   --max-results 20` — capture recent `EnableKeyRotation`,
   `DisableKeyRotation`, `RotateKey` (manual) events.
7. For custom key stores: `aws kms describe-custom-key-stores` —
   verify the CloudHSM cluster state is `ACTIVE` and the key store
   `ConnectionState: CONNECTED`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`enable-key-rotation`, `disable-key-rotation`, `enable-key`,
  `disable-key`, `schedule-key-deletion`, `cancel-key-deletion`,
  `create-key`, `update-alias`, `rotate-key-on-demand`), emit:
  `CONFIRM: About to <operation> on KMS key <key-id> in account
  <account> region <region>. This will <consequence>. Proceed?
  (yes/no)`. Do NOT execute until the operator confirms.

- **Capture pre-state for audit.** Before any rotation operation:
  `aws kms describe-key --key-id <id> --output json > /tmp/<id>-
  describe-pre-$(date +%s).json` AND `aws kms get-key-rotation-status
  --key-id <id> --output json > /tmp/<id>-rotation-pre-$(date
  +%s).json`. These captures are critical for compliance evidence and
  for diagnosing any post-change anomaly.

- **Verify the key policy is unchanged after rotation.** `get-key-
  policy --key-id <id> --policy-name default` — diff against pre-state.
  Rotation must not modify the policy. A policy change indicates a
  concurrent modification by another process.

- **Verify grants are unchanged.** `list-grants --key-id <id>` — diff
  against pre-state. Rotation does not affect grants.

- **Verify CloudTrail is logging the event.** If the account's
  CloudTrail trail is paused or misconfigured, the `EnableKeyRotation`
  event will not be captured. Compliance evidence depends on the
  trail being active.

- **Prefer additive changes over destructive ones.** Enabling
  rotation is safe and reversible. Disabling rotation, disabling a
  key, or scheduling deletion is consequential — confirm intent
  explicitly.
