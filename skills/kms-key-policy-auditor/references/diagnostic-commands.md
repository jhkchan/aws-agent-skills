# Diagnostic Commands — kms-key-policy-auditor

Pre-flight and diagnostic command listings moved verbatim from SKILL.md.

## Pre-flight: account-wide sweep pagination + live-account checks

**Multi-key / account-wide sweep note (pagination):** when auditing every
key in an account, `aws kms list-keys` returns at most 100 per page. Use
`--starting-token` from the prior `NextMarker` to page through all keys;
iterating only the first page silently skips the long tail of keys (the
ones most likely to be stale, exposed, or unrotated). For each key id,
also page `aws kms list-aliases --key-id <id>` and
`aws kms list-grants --key-id <id>` — both cap at 50/100 per page and
silently truncate. Always drain `NextMarker` to completion.

**Live-account pre-flight checks (skip if doing offline policy-doc audit):**
1. Verify the caller's identity can run `kms:PutKeyPolicy` if remediation
   is intended — most read-only auditor roles CANNOT, and remediation
   commands will fail with `AccessDenied`. Surface this BEFORE the operator
   approves the change.
2. Verify CloudTrail is logging KMS **data events** for `kms:Decrypt` /
   `kms:GenerateDataKey*` — KMS management events are on by default, but
   Decrypt/GenerateDataKey are data events that must be explicitly enabled.
   Without them, breach forensics (Step "Assume breach") have no signal.
3. Snapshot `aws kms list-grants --key-id <id>` (paged) BEFORE any policy
   edit — grants are not versioned and a PutKeyPolicy does not retire
   existing grants. Compare pre/post to detect new grants created during
   the remediation window.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any destructive or state-changing
  operation (PutKeyPolicy, ScheduleKeyDeletion, CancelKeyDeletion,
  DisableKey, EnableKeyRotation), the auditor MUST emit:
  `CONFIRM: About to <action> on key <id> in account <account>. This
  affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. This gate
  prevents automated pipelines from silently modifying encryption keys.
- **PutKeyPolicy allowed-principal constraints.** When emitting a
  remediation `PutKeyPolicy` command, the new policy MUST satisfy ALL of:
  (1) include the root-of-trust statement
  (`Principal: {AWS: "arn:aws:iam::ACCOUNT:root"}`) unless
  `BypassPolicyLockoutSafetyCheck: true` is explicitly justified —
  omitting it locks the owning account out of IAM-based access; (2) never
  introduce `Principal: "*"` on DATA_ACCESS or KEY_CONTROL actions in the
  replacement (a remediation that creates a new wildcard Decrypt is worse
  than the original finding); (3) prefer listing explicit 12-digit
  account/role ARNs over `Principal: {"AWS": "*"}` or
  `Principal: {"Service": "*"}`; (4) if the operator's role is not in
  the proposed policy, REFUSE to emit the command and abort — a
  PutKeyPolicy that removes the caller's own access is an instant
  self-lockout with no rollback path (key policies are unversioned).
- Confirm the key exists and is accessible:
  `aws kms describe-key --key-id <id> --profile <p>` — fail closed
  (skip remediation) if it returns an error.
- Capture the current key policy for rollback:
  `aws kms get-key-policy --key-id <id> --policy-name default --output json > /tmp/<id>-policy-backup-$(date +%s).json`
  BEFORE any modification. Key policy changes are not versioned — there is
  no undo without a backup.
- Before enabling rotation, verify the key supports it (symmetric,
  `Origin: AWS_KMS`, `KeyManager: CUSTOMER`). Enabling rotation on an
  unsupported key type returns a `ValidationException`.
- Before cancelling a key deletion, confirm the cancellation is intended
  (not a stale test artifact). `aws kms cancel-key-deletion` is
  irreversible — once cancelled, you must re-schedule if deletion is
  still desired.
- **Multi-region replica sync procedure.** For multi-region keys, policy
  fixes must be applied to EACH replica independently. The procedure is:
  (1) `aws kms describe-key --key-id <primary-id>` to list all replicas
  via the `MultiRegionConfiguration` block. (2) For each replica ARN,
  retrieve its key policy (`aws kms get-key-policy --key-id <replica-arn>`).
  (3) Apply the same remediation to each replica's policy. (4) Verify each
  replica independently by re-auditing. A policy fix on the primary does
  NOT propagate — KMS does not sync key policies across replicas.
- Prefer additive changes (add a Deny statement, add a condition) over
  destructive changes (remove a statement) — additive changes are
  reversible and do not risk breaking existing access patterns.
- For CRITICAL findings (wildcard decrypt, cross-account decrypt, short
  deletion window), treat as incident-response — remediate immediately
  before capturing full forensic state. Rotate any data that was encrypted
  under the exposed key, because the ciphertext may have been exfiltrated.
