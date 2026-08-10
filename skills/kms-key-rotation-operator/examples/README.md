# End-to-end usage scenario: kms-key-rotation-operator

A walkthrough showing the skill planning an enable-rotation operation
on a symmetric customer-managed KMS key, with all pre-checks passing
and the operator confirming at the CONFIRM gate. Contrasted with the
BLOCKED case where an asymmetric RSA key cannot use automatic
rotation.

## Input (user prompt)

> Enable automatic rotation on `alias/prod-app-encryption-key`
> (arn:aws:kms:us-east-1:111111111111:key/abcd1234-...). Annual is
> fine. The key is symmetric, customer-managed, single-region.

```json
{
  "Operation": "enable-rotation",
  "KeyId": "arn:aws:kms:us-east-1:111111111111:key/abcd1234-5678-90ef-...",
  "Alias": "alias/prod-app-encryption-key",
  "RotationPeriodInDays": 365,
  "KeyMetadata": {
    "KeyState": "Enabled",
    "KeyUsage": "ENCRYPT_DECRYPT",
    "KeySpec": "SYMMETRIC_DEFAULT",
    "Origin": "AWS_KMS",
    "MultiRegionConfiguration": null,
    "DeletionDate": null
  },
  "CurrentRotationStatus": {
    "Enabled": false
  }
}
```

## Skill output

```text
OPERATION: enable-rotation
VERDICT: READY
TARGET: arn:aws:kms:us-east-1:111111111111:key/abcd1234-... (alias:
        alias/prod-app-encryption-key, account 111111111111, region
        us-east-1)
PRE_CHECKS:
  - [PASS] Key exists, KeyState: Enabled
  - [PASS] Not PendingDeletion (DeletionDate absent)
  - [PASS] KeySpec: SYMMETRIC_DEFAULT, KeyUsage: ENCRYPT_DECRYPT
  - [PASS] Origin: AWS_KMS (supports automatic rotation)
  - [PASS] Single-region key (not a Multi-Region replica)
  - [PASS] Calling role has kms:EnableKeyRotation via key policy
  - [PASS] RotationPeriodInSeconds: 365 (default — annual)
STEPS:
  1. CONFIRM: About to enable automatic backing-key rotation on KMS
     key alias/prod-app-encryption-key in account 111111111111 region
     us-east-1. Rotation period: 365 days. The key ID, ARN, policy,
     grants, and aliases are unchanged. Existing ciphertext remains
     decryptable. Proceed? (yes/no)
  2. aws kms enable-key-rotation \
       --key-id arn:aws:kms:us-east-1:111111111111:key/abcd1234-...
  3. Verify immediately:
     aws kms get-key-rotation-status \
       --key-id arn:aws:kms:us-east-1:111111111111:key/abcd1234-...
POST_VERIFY:
  - (pending execution)
NOTES:
  - The first rotation occurs within 24 hours of NextRotationDate
    (~365 days from enablement). KMS performs the material swap; no
    application action needed.
  - Old backing material is retained indefinitely (until key deletion).
    Existing ciphertext encrypted with old material remains
    decryptable — no re-encryption required.
  - CloudTrail logs the EnableKeyRotation event immediately. The
    actual material rotation does NOT produce a separate event.
```

## Contrast — BLOCKED case (asymmetric RSA key)

If the operator tried to enable automatic rotation on an RSA signing
key, the pre-check gate would fire and no CLI would execute:

```text
OPERATION: diagnose-rotation
VERDICT: BLOCKED
TARGET: arn:aws:kms:us-east-1:111111111111:key/rsa12345-... (alias:
        alias/prod-signing-key)
PRE_CHECKS:
  - [PASS] Key exists, KeyState: Enabled
  - [PASS] Not PendingDeletion
  - [FAIL] KeySpec: RSA_2048, KeyUsage: SIGN_VERIFY — automatic
    rotation NOT supported (hard KMS limitation). Plan manual
    rotation: create new RSA_2048 key + update alias + optionally
    re-sign.
STEPS: (none — automatic rotation not supported)
POST_VERIFY: (none)
NOTES:
  - Root cause: asymmetric keys (RSA, ECDSA) and HMAC keys do NOT
    support automatic backing-key rotation. This is a KMS limitation.
  - Fix: plan a manual rotation:
    1. aws kms create-key --key-usage SIGN_VERIFY --key-spec RSA_2048
    2. aws kms update-alias --alias-name alias/prod-signing-key
       --target-key-id <new-key-id>
    3. Update hard-coded ARN callers.
    4. Keep the old key Enabled for signature verification.
```

## What the skill caught that a generic assistant misses

1. **Key-type pre-check before enabling rotation.** A generic
   assistant emits `enable-key-rotation` directly, which fails on
   asymmetric/HMAC keys. The skill checks `KeySpec` and `KeyUsage`
   first and routes asymmetric keys to the manual-rotation plan.

2. **Multi-Region replica detection.** A generic assistant calls
   `enable-key-rotation` on the replica and gets
   `InvalidOperationException`. The skill detects the replica
   (`MultiRegionConfiguration.MultiRegionKeyType: REPLICA`) and
   directs the operator to the primary.

3. **Cryptographic-material lifecycle explanation.** A generic
   assistant says "rotation changes the key." The skill explains that
   the key ID/ARN/policy/grants are unchanged, old material is
   retained for decrypt, and new operations use the new material —
   no application changes needed.

4. **CloudTrail event awareness.** A generic assistant says "verify
   rotation ran in CloudTrail." The skill clarifies that CloudTrail
   logs `EnableKeyRotation` (the schedule) but NOT the actual material
   swap — the operator must verify via `NextRotationDate` advancing.

5. **AWS-managed vs customer-managed distinction.** A generic
   assistant says "enable rotation on `aws/s3`." The skill knows
   AWS-managed keys rotate automatically every ~3 years and are not
   configurable — the operator must use a CMK for annual rotation.

6. **Alias-based cutover recommendation.** For manual rotations, a
   generic assistant tells the operator to "update all callers." The
   skill recommends aliases (`update-alias`) so the cutover is a
   one-line atomic operation for callers that use the alias.

7. **Old-key retirement guidance.** A generic assistant omits when
   to delete the old key. The skill specifies: keep Enabled for at
   least 90 days; verify via CloudTrail that no caller uses the old
   key; then schedule deletion with a 30-day window.

## Slash-command invocation

```
/aws:operate-kms-key-rotation
```

Or via the orchestrator:

```
/aws:pipeline
You: "enable rotation on alias/prod-app-encryption-key"
```

The orchestrator emits
`[Phase: Operate | Skills routed: kms-key-rotation-operator]` and
hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "enable rotation on alias/prod-app-encryption-key"
# [Phase: Operate | Skills routed: kms-key-rotation-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After enabling rotation:

```bash
# Verify rotation status
aws kms get-key-rotation-status \
  --key-id arn:aws:kms:us-east-1:111111111111:key/abcd1234-... \
  --profile default

# Confirm CloudTrail logged the EnableKeyRotation event
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=arn:aws:kms:us-east-1:111111111111:key/abcd1234-... \
  --attribute-key EventSource --attribute-value kms.amazonaws.com \
  --start-time $(date -u -v-10m +%Y-%m-%dT%H:%M:%SZ) \
  --max-results 10 \
  --profile default

# Verify key policy unchanged
aws kms get-key-policy \
  --key-id arn:aws:kms:us-east-1:111111111111:key/abcd1234-... \
  --policy-name default \
  --profile default

# Spot-check: application can still Encrypt + Decrypt
aws kms encrypt \
  --key-id alias/prod-app-encryption-key \
  --plaintext fileb://<(echo "test") \
  --profile default | jq -r .CiphertextBlob | base64 -d > /tmp/ct.bin
aws kms decrypt \
  --ciphertext-blob fileb:///tmp/ct.bin \
  --profile default | jq -r .Plaintext | base64 -d
```
