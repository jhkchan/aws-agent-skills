# Error Handling — kms-key-policy-auditor

Remediation runbooks moved verbatim from SKILL.md.

## Remediation guidance — by severity

### For CRITICAL — cross-account or wildcard decrypt (Rules 5a, 5c)

1. **Immediately** remove the cross-account/wildcard principal from the
   key policy, or add a strong condition (`kms:ViaService`,
   `aws:SourceAccount`, `aws:SourceArn`) to scope the grant. Back up the
   policy first (see Pre-flight).
2. **Assume breach.** Audit CloudTrail for `kms:Decrypt` events from the
   external principal during the exposure window. Any ciphertext they
   could have decrypted should be considered compromised.
3. **Re-encrypt affected data** under a new key with a clean policy.
   Identify data dependencies via CloudTrail `kms:Encrypt` and
   `kms:GenerateDataKey` events.
4. If cross-account decrypt is **intentional** (e.g., a shared services
   account), replace `Principal: "*"` with the specific external role ARN
   and add `aws:SourceAccount` / `aws:SourceArn` conditions.

### For CRITICAL — wildcard/cross-account key control (Rules 5b, 5d)

1. Remove `kms:PutKeyPolicy`, `kms:ScheduleKeyDeletion`, `kms:DisableKey`,
   `kms:Delete*` from any cross-account or wildcard statement.
2. These actions should ONLY be available to the account root and
   explicitly named administrator roles within the owning account.
3. Verify the key policy still includes the root-of-trust statement
   (`Principal: {AWS: "arn:aws:iam::ACCOUNT:root"}`) — without it, the
   key cannot be managed via IAM.

### For CRITICAL — key in PendingDeletion with window <= 7 days

1. **Immediately** cancel deletion if the key has live dependencies:
   `aws kms cancel-key-deletion --key-id <id>`.
2. Identify all data encrypted under the key (CloudTrail
   `kms:Encrypt`/`GenerateDataKey` events, resource tags).
3. If deletion is intentional, first re-encrypt all dependent data to a
   replacement key, THEN schedule deletion with the maximum 30-day window.

### For CRITICAL — wildcard CreateGrant (Rule 5e)

1. Remove `kms:CreateGrant` from the wildcard statement.
2. Enumerate existing grants: `aws kms list-grants --key-id <id>`.
   Review each grant for unexpected delegates.
3. Retire any grants that were created by the exposed principal:
   `aws kms retire-grant --key-id <id> --grant-id <gid>`.

### For HIGH — rotation disabled on customer-managed symmetric key

1. Enable rotation:
   `aws kms enable-key-rotation --key-id <id> --profile <p>`.
2. Rotation takes effect at the next rotation window (up to 365 days for
   existing keys; new keys rotate within the first year).
3. Verify with:
   `aws kms get-key-rotation-status --key-id <id>`.

### For HIGH — cross-account encrypt/delegation (Rules 5g, 5h)

1. Scope the cross-account grant to specific actions and add conditions.
2. If cross-account encrypt is intentional (e.g., a log-shipping account),
   restrict to `kms:Encrypt` + `kms:GenerateDataKey*` only — never grant
   `kms:Decrypt` to the external principal.
3. For `kms:CreateGrant`, replace broad grants with constrained grants
   that include `EncryptionContextEquals` constraints.

### For MEDIUM — condition-restricted cross-account (Rule 5k)

1. Validate the condition is still correct and the named service/account
   still exists.
2. Convert the Allow-based restriction to an explicit Deny (deny all
   except the trusted service/account) — Deny statements cannot be
   accidentally widened by adding a new Allow.
3. For `kms:ViaService`, verify the service integration is still in use.

### For OK

1. No remediation required for the current posture.
2. Recommend enabling key rotation if not already enabled (defense-in-depth
   for symmetric customer-managed keys).
3. Recommend adding a Deny statement for `aws:SecureTransport: false` to
   enforce TLS for all KMS API calls (defense-in-depth).
4. For multi-region keys, verify replicas are also audited.
