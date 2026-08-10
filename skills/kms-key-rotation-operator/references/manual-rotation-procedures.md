# KMS Manual Rotation Procedures Reference

Load this reference when planning a manual KMS key rotation for
asymmetric, HMAC, or external-material keys. The procedures below
cover the cutover sequence, caller identification, and rollback.

## When manual rotation is required

- Asymmetric keys (`RSA_*`, `ECC_*`) — automatic rotation NOT
  supported by KMS.
- HMAC keys (`HMAC_*`) — automatic rotation NOT supported.
- External-material keys (`Origin: EXTERNAL`) — you manage the key
  material; KMS cannot rotate.
- Compliance-driven rotations on a schedule shorter than the minimum
  7-day automatic period (rare).

For symmetric `SYMMETRIC_DEFAULT` keys with `Origin: AWS_KMS`, use
automatic rotation instead. Manual rotation of symmetric keys is
unnecessary.

## Procedure: caller identification

Before a manual rotation, identify every caller of the key. Use
CloudTrail data events (if logged) or management events.

```bash
# 1. List recent callers (management events: Sign, Verify, Encrypt,
#    Decrypt, GenerateDataKey, GenerateMac, VerifyMac)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=<key-arn> \
  --start-time $(date -u -v-30d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --max-results 1000 \
  --query 'Events[*].[EventTime, Username, EventName, CloudTrailEvent]' \
  --output text > callers.tsv

# 2. Extract unique caller identities (assumed-role ARNs, IAM users)
awk -F'\t' '{print $2}' callers.tsv | sort -u

# 3. For each caller, find how they reference the key:
#    - Alias (alias/my-app-key) — transparent cutover via update-alias
#    - Key ID (abcd1234-...) — transparent cutover via alias update IF
#      the caller resolves the alias to a key ID at call time
#    - Key ARN (arn:aws:kms:...) — requires updating the caller's
#      configuration (env var, config file, IAM policy)
```

## Procedure: cutover via alias (preferred)

If all callers reference the key by alias, the cutover is a single
`update-alias` call. Callers resolve the alias at each call, so the
cutover is immediate.

```bash
# 1. Create the new key
NEW_KEY_ID=$(aws kms create-key \
  --description "rotation $(date +%Y-%m-%d) of <old-key-id>" \
  --key-usage SIGN_VERIFY \
  --key-spec RSA_2048 \
  --policy file://new-key-policy.json \
  --query 'KeyMetadata.KeyId' --output text)

# 2. Apply the same tags as the old key (for cost allocation, ABAC)
aws kms list-resource-tags --key-id <old-key-id> \
  --query 'Tags' --output json > tags.json
aws kms tag-resource --key-id $NEW_KEY_ID --tags file://tags.json

# 3. Cutover: point the alias to the new key
aws kms update-alias \
  --alias-name alias/prod-signing-key \
  --target-key-id $NEW_KEY_ID

# 4. Verify callers now use the new key
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=<new-key-arn> \
  --start-time $(date -u -v-5m +%Y-%m-%dT%H:%M:%SZ) \
  --max-results 10

# 5. Keep the old key Enabled (do NOT disable or delete yet)
aws kms describe-key --key-id <old-key-id> --query 'KeyMetadata.KeyState'
```

## Procedure: cutover via key ARN (hard-coded callers)

For callers that hard-code the key ARN, the cutover requires updating
each caller's configuration.

```bash
# 1. Create the new key (same as alias procedure)
NEW_KEY_ID=$(aws kms create-key ...)

# 2. For each caller identified in the caller-identification step:
#    a. Update the application's environment variable / config file:
#       KMS_KEY_ARN=arn:aws:kms:us-east-1:111111111111:key/$NEW_KEY_ID
#    b. Update the caller's IAM policy to grant kms:Sign/Verify on
#       the new key ARN (if the policy is key-specific).
#    c. Deploy the updated configuration.
#    d. Verify the caller can use the new key (test Sign + Verify).

# 3. IAM policy update example (if key-specific):
aws iam put-role-policy \
  --role-name prod-orders-service-role \
  --policy-name kms-signing \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["kms:Sign", "kms:Verify"],
      "Resource": "arn:aws:kms:us-east-1:111111111111:key/'"$NEW_KEY_ID"'"
    }]
  }'

# 4. After all callers are updated, verify via CloudTrail that no
#    caller still uses the old key ARN.
```

## Procedure: re-signing artifacts (optional)

For compliance, you may need to re-sign existing artifacts with the
new key. Old signatures remain valid (verifiable against the old key)
as long as the old key is `Enabled`.

```bash
# Example: re-signing a set of documents (Python with boto3)
python3 << 'EOF'
import boto3
kms = boto3.client('kms')

# List of document hashes to re-sign
# (fetch from your application's database)
documents = [...]

for doc in documents:
    # Sign with the new key
    response = kms.sign(
        KeyId='arn:aws:kms:us-east-1:111111111111:key/<new-key-id>',
        Message=doc['hash'].encode(),
        MessageType='DIGEST',
        SigningAlgorithm='RSASSA_PSS_SHA_256'
    )
    # Store the new signature alongside the document
    # doc['signature_v2'] = response['Signature']
    # doc['signing_key_arn_v2'] = response['SigningAlgorithm']
EOF
```

## Rollback procedure

If the new key is broken (wrong KeySpec, bad policy, callers can't
use it), roll back:

```bash
# 1. Re-point the alias back to the old key (immediate rollback for
#    alias-using callers)
aws kms update-alias \
  --alias-name alias/prod-signing-key \
  --target-key-id <old-key-id>

# 2. For ARN-hard-coded callers: revert the configuration change and
#    redeploy.

# 3. Schedule the new (broken) key for deletion after confirming
#    rollback is stable:
aws kms schedule-key-deletion \
  --key-id <new-key-id> \
  --pending-window-in-days 7
```

## Old-key retirement

After a successful manual rotation, retire the old key:

```bash
# 1. Wait 90 days (or your compliance window). During this time,
#    verify via CloudTrail that NO caller uses the old key ARN.

# 2. Confirm all old signatures / ciphertexts have been re-signed /
#    re-encrypted, OR are no longer needed.

# 3. Schedule deletion (7-30 day waiting period, configurable):
aws kms schedule-key-deletion \
  --key-id <old-key-id> \
  --pending-window-in-days 30

# 4. The key enters PendingDeletion state. Rotation is implicitly
#    cancelled. Existing ciphertext/signatures remain usable until
#    the deletion window expires.

# 5. After deletion: existing ciphertext signed by the old key is
#    PERMANENTLY unrecoverable. Ensure all artifacts are re-encrypted
#    / re-signed BEFORE the deletion window expires.
```

## Compliance evidence for manual rotations

Document each manual rotation with:

```bash
# Capture the CreateKey event for the new key
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateKey \
  --start-time <rotation-date> \
  --end-time <rotation-date + 1 day> \
  --query 'Events[?contains(CloudTrailEvent, `"<new-key-id>"`)]'

# Capture the UpdateAlias event (cutover)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=UpdateAlias \
  --start-time <rotation-date> \
  --end-time <rotation-date + 1 day> \
  --query 'Events[?contains(CloudTrailEvent, `"alias/prod-signing-key"`)]'

# Store the evidence in your compliance system with a ticket reference.
```
