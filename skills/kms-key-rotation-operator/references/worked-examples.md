# Worked Examples — kms-key-rotation-operator

Secondary worked examples moved verbatim from SKILL.md. Load on demand.

## Worked example — plan-manual-rotation (asymmetric RSA key)

```text
OPERATION: plan-manual-rotation
VERDICT: READY
TARGET: arn:aws:kms:us-east-1:111111111111:key/rsa12345-... (alias:
        alias/prod-signing-key, account 111111111111, region
        us-east-1)
PRE_CHECKS:
  - [PASS] Key exists, KeyState: Enabled
  - [PASS] Not PendingDeletion
  - [INFO] KeySpec: RSA_2048, KeyUsage: SIGN_VERIFY — automatic
    rotation NOT supported (hard KMS limitation)
  - [PASS] Operator has kms:CreateKey permission
  - [PASS] Alias alias/prod-signing-key points to this key — callers
    using the alias will follow the update-alias cutover transparently
  - [INFO] 3 CloudTrail-observed callers in the last 30 days:
    prod-orders-service (uses alias), prod-payments-service (uses
    alias), prod-web-app (uses key ARN — MUST be updated manually)
STEPS:
  1. CONFIRM: About to perform a MANUAL rotation on RSA signing key
     alias/prod-signing-key. This involves: (a) creating a new RSA_2048
     key, (b) updating alias/prod-signing-key to point to the new key,
     (c) updating prod-web-app to use the new key ARN. Old signatures
     remain verifiable against the old key (which stays Enabled).
     Proceed? (yes/no)
  2. Create the new key:
     aws kms create-key \
       --description "prod-signing-key rotation 2026-08" \
       --key-usage SIGN_VERIFY \
       --key-spec RSA_2048 \
       --policy file://new-key-policy.json
     # Capture the new KeyId from the response.
  3. Update the alias (atomic cutover for alias-referencing callers):
     aws kms update-alias \
       --alias-name alias/prod-signing-key \
       --target-key-id <new-key-id>
  4. Update prod-web-app (hard-coded ARN caller):
     # Update the application configuration / environment variable to
     # the new key ARN. Deploy. Verify signatures validate with the
     # new key.
  5. (Optional) Re-sign critical artifacts with the new key. Old
     signatures remain valid as long as the old key is Enabled.
POST_VERIFY:
  - (pending execution)
NOTES:
  - The old key (rsa12345-...) MUST remain Enabled for as long as any
    signature produced with it needs to be verified. Disabling or
    deleting the old key breaks signature verification for all
    artifacts signed by it.
  - Schedule a review in 90 days: if all observed verifications use
    the new key, consider scheduling the old key for deletion (after
    compliance approval).
  - For compliance evidence, document the manual rotation with a
    ticket reference and the CloudTrail CreateKey + UpdateAlias
    events.
```

## Worked example — diagnose-rotation (BLOCKED with remediation)

```text
OPERATION: diagnose-rotation
VERDICT: BLOCKED
TARGET: arn:aws:kms:us-east-1:111111111111:key/multi-replica-... (alias:
        alias/prod-dr-key, account 111111111111, region us-east-1)
PRE_CHECKS:
  - [PASS] Key exists
  - [INFO] KeyState: Enabled
  - [FAIL] MultiRegionConfiguration.MultiRegionKeyType: REPLICA
    (primary: arn:aws:kms:eu-west-1:111111111111:key/multi-primary-...)
    — EnableKeyRotation cannot be called on a replica key. Rotation
    must be enabled on the primary in eu-west-1.
STEPS: (none — wrong key target)
POST_VERIFY: (none)
NOTES:
  - Root cause: the operator is trying to enable rotation on a Multi-
    Region REPLICA key. KMS returns InvalidOperationException for
    this case. Rotation is controlled by the primary key.
  - Fix: call enable-key-rotation on the PRIMARY key in eu-west-1:
    aws kms enable-key-rotation \
      --key-id arn:aws:kms:eu-west-1:111111111111:key/multi-primary-... \
      --region eu-west-1
    The primary's rotation status propagates to all replicas
    automatically. Verify on the replica after the primary's
    NextRotationDate:
    aws kms get-key-rotation-status \
      --key-id arn:aws:kms:us-east-1:111111111111:key/multi-replica-...
```
