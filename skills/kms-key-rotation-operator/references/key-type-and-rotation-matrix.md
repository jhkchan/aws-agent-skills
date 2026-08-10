# KMS Key Type and Rotation Support Matrix Reference

Load this reference when planning a KMS key rotation. The matrix below
shows which key types support automatic rotation, which require manual
rotation, and the correct procedure for each.

## Key type rotation matrix

| KeySpec | KeyUsage | Origin | Auto rotation? | Manual rotation? | Notes |
|---|---|---|---|---|---|
| `SYMMETRIC_DEFAULT` | `ENCRYPT_DECRYPT` | `AWS_KMS` | Yes (365-day default, configurable 7-365) | Optional | Most common CMK. Transparent to applications. |
| `SYMMETRIC_DEFAULT` | `ENCRYPT_DECRYPT` | `AWS_CLOUDHSM` | Yes (cluster must be ACTIVE) | Optional | Custom key store. KMS rotates backing key in CloudHSM. |
| `SYMMETRIC_DEFAULT` | `ENCRYPT_DECRYPT` | `EXTERNAL` | NO | Re-import new material | BYOK. You must manage rotation externally. |
| `RSA_2048`, `RSA_3072`, `RSA_4096` | `ENCRYPT_DECRYPT` | `AWS_KMS` | NO | Yes (create new + update aliases) | Asymmetric encryption. |
| `RSA_2048`, `RSA_3072`, `RSA_4096` | `SIGN_VERIFY` | `AWS_KMS` | NO | Yes (create new + update aliases + re-sign) | Asymmetric signing. |
| `ECC_NIST_P256`, `P384`, `P521` | `SIGN_VERIFY` | `AWS_KMS` | NO | Yes (create new + update aliases + re-sign) | ECDSA signing. |
| `ECC_NIST_K256`, `ECC_SECG_P256K1` | `SIGN_VERIFY` | `AWS_KMS` | NO | Yes | Less common curves. |
| `SM2` | `ENCRYPT_DECRYPT` or `SIGN_VERIFY` | `AWS_KMS` | NO | Yes | China regions only. |
| `HMAC_256`, `HMAC_384`, `HMAC_512` | `GENERATE_VERIFY_MAC` | `AWS_KMS` | NO | Yes (create new + update aliases) | HMAC keys. |
| Multi-Region PRIMARY (symmetric) | `ENCRYPT_DECRYPT` | `AWS_KMS` | Yes | Optional | Rotation propagates to all replicas. |
| Multi-Region REPLICA (symmetric) | `ENCRYPT_DECRYPT` | `AWS_KMS` | Inherits from PRIMARY | N/A | `EnableKeyRotation` returns InvalidOperationException. Manage on primary. |
| AWS-managed (`aws/s3`, `aws/rds`, etc.) | `ENCRYPT_DECRYPT` | `AWS_KMS` | Automatic (~3 years, AWS-managed) | Not configurable | You CANNOT enable/disable/configure. |

## Procedure: enable automatic rotation (symmetric CMK)

```bash
# 1. Verify the key supports automatic rotation
aws kms describe-key --key-id <id> \
  --query 'KeyMetadata.[KeyState, KeyUsage, KeySpec, Origin,
            MultiRegionConfiguration.MultiRegionKeyType]'

# Expected: ["Enabled", "ENCRYPT_DECRYPT", "SYMMETRIC_DEFAULT",
#            "AWS_KMS", null or "PRIMARY"]

# 2. Enable rotation (default 365 days)
aws kms enable-key-rotation --key-id <id>

# Or with a custom period (7-365 days)
aws kms enable-key-rotation \
  --key-id <id> \
  --rotation-period-in-days 180

# 3. Verify
aws kms get-key-rotation-status --key-id <id>
# Expected: {"Enabled": true, "RotationPeriodInSeconds": 15552000,
#            "NextRotationDate": "2027-02-01T00:00:00Z"}
```

## Procedure: on-demand rotation (immediate, 2024+)

For incident response (suspected compromise) or pre-scheduled
compliance rotations. Does NOT affect the scheduled `NextRotationDate`.

```bash
aws kms rotate-key-on-demand --key-id <id>
# Returns immediately; the material swap happens within seconds.
# Verify via CloudTrail (RotateKey event) and observe NextRotationDate
# for the scheduled rotation is unchanged.
```

## Procedure: manual rotation (asymmetric / HMAC / external)

```bash
# 1. Create the new key with the same KeySpec / KeyUsage
NEW_KEY_ID=$(aws kms create-key \
  --description "manual rotation $(date +%Y-%m-%d)" \
  --key-usage SIGN_VERIFY \
  --key-spec RSA_2048 \
  --policy file://key-policy.json \
  --query 'KeyMetadata.KeyId' --output text)

# 2. Create an alias (if the old key has one, point it to the new key)
aws kms create-alias \
  --alias-name alias/prod-signing-key \
  --target-key-id $NEW_KEY_ID

# Or UPDATE an existing alias (atomic cutover for alias-using callers)
aws kms update-alias \
  --alias-name alias/prod-signing-key \
  --target-key-id $NEW_KEY_ID

# 3. Update hard-coded ARN callers (find them via CloudTrail)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=<old-key-arn> \
  --attribute-key EventSource --attribute-value kms.amazonaws.com \
  --max-results 50

# 4. (Optional) Re-sign / re-encrypt critical artifacts
#    Old signatures remain valid as long as the old key is Enabled.

# 5. Keep the old key Enabled until all artifacts are re-signed / no
#    longer needed (typically 90+ days). Then schedule deletion:
aws kms schedule-key-deletion --key-id <old-key-id> --pending-window-in-days 30
```

## Procedure: re-import material (EXTERNAL origin)

For keys with imported material, rotation = re-importing new material.

```bash
# 1. Get parameters for import (public key + import token)
aws kms get-parameters-for-import \
  --key-id <id> \
  --wrapping-algorithm RSAES_OAEP_SHA_256 \
  --wrapping-key-spec RSA_4096 \
  --query '[PublicKey, ImportToken]' --output text > params.txt

# 2. Generate new key material locally, encrypt with the wrapping key,
#    then import:
aws kms import-key-material \
  --key-id <id> \
  --import-token fileb://import-token.b64 \
  --encrypted-key-material fileb://encrypted-material.bin \
  --valid-to 2027-01-01T00:00:00Z
```

## Diagnostic command quick-reference

| Goal | Command |
|---|---|
| Key metadata | `aws kms describe-key --key-id <id>` |
| Rotation status | `aws kms get-key-rotation-status --key-id <id>` |
| Enable rotation | `aws kms enable-key-rotation --key-id <id> [--rotation-period-in-days N]` |
| Disable rotation | `aws kms disable-key-rotation --key-id <id>` |
| On-demand rotation | `aws kms rotate-key-on-demand --key-id <id>` |
| Key policy | `aws kms get-key-policy --key-id <id> --policy-name default` |
| Update key policy | `aws kms put-key-policy --key-id <id> --policy-name default --policy file://policy.json` |
| List grants | `aws kms list-grants --key-id <id>` |
| List aliases | `aws kms list-aliases --target-key-id <id>` |
| Update alias | `aws kms update-alias --alias-name alias/<name> --target-key-id <new-id>` |
| List keys | `aws kms list-keys` |
| CloudTrail events | `aws cloudtrail lookup-events --lookup-attributes AttributeKey=ResourceName,AttributeValue=<arn> --attribute-key EventSource --attribute-value kms.amazonaws.com` |
| Custom key stores | `aws kms describe-custom-key-stores` |
| Get import params | `aws kms get-parameters-for-import --key-id <id> --wrapping-algorithm RSAES_OAEP_SHA_256 --wrapping-key-spec RSA_4096` |
| Import material | `aws kms import-key-material --key-id <id> --import-token fileb://token.b64 --encrypted-key-material fileb://material.bin` |
| Schedule deletion | `aws kms schedule-key-deletion --key-id <id> --pending-window-in-days 7` |
| Cancel deletion | `aws kms cancel-key-deletion --key-id <id>` |

## Compliance evidence collection

For annual-rotation compliance audits, capture per-key evidence:

```bash
for KEY_ID in $(aws kms list-keys --query 'Keys[*].KeyId' --output text); do
  echo "=== $KEY_ID ==="
  aws kms describe-key --key-id $KEY_ID \
    --query 'KeyMetadata.[KeyId, KeyState, KeyUsage, KeySpec, Origin,
              Description, DeletionDate]'
  aws kms get-key-rotation-status --key-id $KEY_ID \
    --query '[Enabled, RotationPeriodInSeconds, NextRotationDate]'
  echo
done
```

**Compliance interpretation:**

| Key type | Rotation evidence |
|---|---|
| Symmetric CMK, auto-rotation enabled | `Enabled: true` + `NextRotationDate` set. Compliance: PASS. |
| Symmetric CMK, auto-rotation disabled | `Enabled: false`. Compliance: FAIL unless manually rotated within policy window. |
| AWS-managed key (`aws/*`) | Auto-rotates ~3 years. Compliance: PASS for 3-year policies; FAIL for annual policies. Use CMKs for annual. |
| Asymmetric / HMAC | No auto-rotation. Compliance: requires documented manual rotation (CreateKey + UpdateAlias events in CloudTrail). |
| Multi-Region replica | Inherits primary's status. Reference the primary's `get-key-rotation-status` as evidence. |
| External-material key | Requires documented re-import events as rotation evidence. |
| PendingDeletion | Out of scope — key is being deleted. |

## CloudTrail events for rotation auditing

| Event | Meaning |
|---|---|
| `EnableKeyRotation` | Automatic rotation scheduled (management event, always logged). |
| `DisableKeyRotation` | Automatic rotation cancelled (management event). |
| `RotateKey` (2024+) | On-demand rotation performed via `rotate-key-on-demand`. |
| `CreateKey` | New key created (manual rotation evidence). |
| `UpdateAlias` | Alias retargeted (manual rotation cutover evidence). |
| `ScheduleKeyDeletion` | Old key scheduled for deletion (manual rotation retirement). |
| `CancelKeyDeletion` | Deletion cancelled; key restored. |
| (internal material swap) | NOT logged as a separate CloudTrail event. Use `NextRotationDate` advancing as the observable signal. |
