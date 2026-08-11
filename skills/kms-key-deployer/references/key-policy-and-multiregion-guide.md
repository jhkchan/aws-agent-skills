# Key Policy, Multi-Region, and Envelope Encryption Guide

Deep reference on KMS key policy structure (administrators vs. users,
grants, encryption context), multi-Region primary/replica internals,
CloudHSM custom key store lifecycle, envelope encryption patterns,
and cross-account access semantics.

## 1. Key policy structure

The key policy is a JSON resource policy attached to the CMK. It is
the PRIMARY access control mechanism — IAM grants are layered on top
but cannot grant access the key policy denies.

### 1.1 The four canonical statements

A production key policy should contain exactly four statements:

1. **Break-glass (root)** — gives the account root full access.
   Mandatory. Without this, an accidental lockout is unrecoverable.
2. **Key administrators** — lifecycle actions (`Create*`, `Put*`,
   `Disable*`, `ScheduleKeyDeletion`, `RotateKeyOnDemand`). NO
   cryptographic operations.
3. **Key users** — cryptographic operations (`Encrypt`, `Decrypt`,
   `GenerateDataKey*`, `ReEncrypt*`, `DescribeKey`). The application's
   identity.
4. **Grant creation** — allows the application role to create grants
   for AWS service integrations (when `kms:GrantIsForAWSResource=true`).

### 1.2 Statement ordering

KMS evaluates policy statements independently — order does not matter
for Allow/Deny resolution. However, the convention is:

1. Break-glass (root)
2. Key administrators
3. Key users
4. Grant creation
5. Cross-account (if applicable)

Deny statements (if any) usually come last for readability.

### 1.3 Condition keys

KMS supports condition keys for fine-grained access:

- `kms:EncryptionContext:<key>` — require a specific encryption
  context value (e.g., `kms:EncryptionContext:department=finance`).
- `kms:ViaService` — restrict to calls from a specific AWS service
  (e.g., `kms:ViaService: s3.us-east-1.amazonaws.com`).
- `kms:CallerAccount` — restrict to a specific account.
- `kms:GrantIsForAWSResource` — only for AWS service-created grants.
- `kms:KeySpec` — restrict by key spec.
- `kms:SigningAlgorithm` — restrict signing algorithms (asymmetric).

Example: limit a Lambda role to Decrypt only when called via S3:

```json
{
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::<account-id>:role/<lambda-role>" },
  "Action": "kms:Decrypt",
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "kms:ViaService": "s3.us-east-1.amazonaws.com"
    }
  }
}
```

### 1.4 Policy size limit

The key policy JSON has a 32 KB limit (after whitespace removal).
For complex policies with many principals, use grants instead.

## 2. Key administrators vs. key users — the separation principle

| Action | Administrator | User | Why separate? |
|---|---|---|---|
| `kms:CreateAlias`, `kms:DeleteAlias` | YES | NO | Aliases are operational; users should not rename them. |
| `kms:PutKeyPolicy`, `kms:GetKeyPolicy` | YES | NO | Users should not change their own access. |
| `kms:EnableKeyRotation`, `kms:DisableKeyRotation` | YES | NO | Rotation is a security policy decision. |
| `kms:ScheduleKeyDeletion`, `kms:CancelKeyDeletion` | YES | NO | Deletion is irreversible — gate it tightly. |
| `kms:RotateKeyOnDemand` | YES | NO | On-demand rotation is an admin action. |
| `kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey*` | NO | YES | Admins should not read production ciphertext. |
| `kms:ReEncrypt*` | NO | YES | Re-encryption moves ciphertext between keys. |
| `kms:Describe*`, `kms:List*` | YES | YES | Read-only metadata access is safe for both. |
| `kms:CreateGrant`, `kms:RevokeGrant` | Conditionally | YES (with condition) | Users can create service-integration grants; admins revoke. |

### 2.1 Why this matters

- **Compliance:** SOC 2 / PCI-DSS / HIPAA require separation of duties
  between key management and data access. An admin who can disable the
  key should not be able to read the encrypted data; an analyst who
  reads encrypted data should not be able to disable the key.
- **Blast radius:** if the admin role is compromised, the attacker can
  disable the key (denial of service) but cannot exfiltrate data. If
  the user role is compromised, the attacker can read data but cannot
  destroy the key.
- **Auditability:** CloudTrail shows which role took which action.
  Mixed permissions obscure accountability.

## 3. Grants vs. key policy

| Property | Key policy | Grant |
|---|---|---|
| Persistence | Permanent (until policy update) | Temporary (revocable, can expire) |
| Scope | All principals listed | Specific grantee principal |
| Constraints | Limited | Rich (encryption context subset, grant constraints) |
| Use case | Long-term human/role access | Service integrations, temporary access |
| Limit | 32 KB policy | 50 grants per CMK initially (quota increase available) |

### 3.1 When to use grants

- **AWS service integration:** when an encrypted EBS volume is attached
  to an EC2 instance, EC2 creates a grant on the CMK allowing the
  instance role to Decrypt. The grant is retired when the volume is
  detached.
- **Temporary cross-account access:** grant a migration tool Decrypt
  access for 24 hours with a retiring principal.
- **Tighter scoping:** a grant can constrain Decrypt to a specific
  encryption context (e.g., `department=finance`) even if the key
  policy allows Decrypt broadly.

### 3.2 Grant lifecycle

```bash
# Create (eventually consistent — wait ~5 seconds)
aws kms create-grant \
  --key-id <key-id> \
  --grantee-principal <role-arn> \
  --operations Decrypt GenerateDataKey \
  --constraints '{"EncryptionContextSubset": {"department": "finance"}}'

# List
aws kms list-grants --key-id <key-id>

# Revoke (immediate)
aws kms revoke-grant --key-id <key-id> --grant-id <grant-id>

# Retire (automatic when the retiring principal deletes it)
# Use --retiring-principal at create time
```

### 3.3 Grant constraints

- `EncryptionContextSubset` — requires the specified context keys to
  be present (subset match).
- `EncryptionContextEquals` — requires exact context match.

```json
"Constraints": {
  "EncryptionContextSubset": {
    "department": "finance",
    "env": "prod"
  }
}
```

## 4. Multi-Region keys

### 4.1 Primary and replicas

A multi-Region CMK has a primary in one Region and replicas in other
Regions. All share the same key material — encrypted data under the
primary can be decrypted by any replica (in its own Region).

- **Primary** — created with `--multi-region`. The "source of truth"
  for key material.
- **Replica** — created with `replicate-key` from the primary's ARN.
  Has an independent key policy.

### 4.2 Independent policies

The primary's policy does NOT propagate to replicas. Each replica
starts with a copy of the primary's policy at replication time, but
diverges afterward. Automate replica policy sync via CloudFormation
StackSets or Terraform `for_each`.

### 4.3 No automatic rotation

Multi-Region keys CANNOT auto-rotate — rotation would desync the
primary and replicas. For multi-Region rotation:

1. Create a new multi-Region primary (with replicas).
2. Update the alias to point at the new primary.
3. Re-encrypt data on next access (or in a batch migration).
4. Schedule the old primary for deletion (30-day window).

This manual rotation is what the "Expert heuristic" section refers to
as "documented manual rotation procedure."

### 4.4 Use cases

- **Cross-Region disaster recovery:** encrypt in us-east-1, decrypt in
  us-west-2 during failover.
- **Cross-Region encrypted EBS snapshot restore:** snapshot encrypted
  with multi-Region CMK can be copied and decrypted in another Region.
- **Global DynamoDB tables:** a single multi-Region CMK protects all
  replica tables.

For single-Region workloads, multi-Region adds complexity for no
benefit. Stick with a single-Region CMK with auto-rotation enabled.

## 5. CloudHSM custom key store

### 5.1 Architecture

A custom key store links KMS to a CloudHSM cluster. The key material
lives in the HSM (FIPS 140-2 Level 3); KMS proxies cryptographic
operations to the HSM via the `kmsuser` crypto user (CU).

### 5.2 Prerequisites

- **CloudHSM cluster:** ACTIVE state, with >= 2 HSMs in different AZs
  for HA.
- **`kmsuser` CU:** created on the HSM, logged out before KMS connects.
- **Trust anchor:** the cluster's certificate, used by KMS to verify
  the HSM.
- **Cluster state:** ACTIVE, not in deletion.

### 5.3 Lifecycle

```bash
# 1. Verify cluster
aws cloudhsmv2 describe-clusters \
  --query 'Clusters[].{Id:ClusterId,State:State,Hsms:Hsms[].{Id:HsmId,State:State,AZ:AvailabilityZone}}'

# 2. Create custom key store
aws kms create-custom-key-store \
  --custom-key-store-name <name> \
  --cloud-hsm-cluster-id cluster-xxx \
  --trust-anchor fileb://trust-anchor.pem \
  --key-store-admin-credentials <kmsuser-password> \
  --hsm-credentials <partition-password>

# 3. Connect (kmsuser must be logged out)
aws kms connect-custom-key-store --custom-key-store-id cks-xxx

# 4. Create key in the custom key store
aws kms create-key \
  --custom-key-store-id cks-xxx \
  --description "<description>" \
  --policy file:///tmp/policy.json
```

### 5.4 Failure modes

- **Cluster unhealthy:** if any HSM goes unhealthy, the custom key
  store may disconnect. All Encrypt/Decrypt on its keys fails
  immediately.
- **`kmsuser` locked:** if `kmsuser` exceeds PIN retries, KMS cannot
  log in. Requires resetting the CU password on the HSM, then
  reconnecting the key store.
- **Network partition:** if KMS cannot reach the HSM (e.g., security
  group change), the key store disconnects.

Monitor `ConnectCustomKeyStore` CloudWatch metrics and alert on
`DISCONNECTED` state.

### 5.5 Rotation in custom key store

Custom key store keys now support automatic rotation in most Regions
(since 2024-2025). Verify Region support before relying on it.
Otherwise, manual rotation as for multi-Region.

## 6. Envelope encryption

### 6.1 The pattern

```
1. App calls KMS GenerateDataKey(keyId,KeySpec=AES_256)
   KMS returns: plaintext_data_key + encrypted_data_key
2. App encrypts payload with plaintext_data_key (AES-GCM client-side)
3. App discards plaintext_data_key
4. App stores: ciphertext + encrypted_data_key
5. To decrypt: App calls KMS Decrypt(encrypted_data_key)
   KMS returns plaintext_data_key
6. App decrypts ciphertext with plaintext_data_key
```

### 6.2 Why envelope encryption

- **Size limit:** KMS Encrypt has a 4 KB payload limit. Envelope
  encryption handles arbitrary sizes.
- **Throughput:** KMS has a per-key RPS quota (50k for
  GenerateDataKey). Envelope encryption caches the data key client-side.
- **Latency:** each KMS call is ~100-200 ms. Caching the data key
  avoids per-record KMS calls.
- **Auditability:** KMS CloudTrail logs GenerateDataKey and Decrypt
  calls — these are the "interesting" events. Per-record Encrypt would
  flood CloudTrail.

### 6.3 The AWS Encryption SDK

Use the AWS Encryption SDK (`@aws-crypto/client-node`,
`aws-crypto-python-encryption-sdk`, `aws-encryption-sdk-java`) — it
implements envelope encryption with key caching, key commitment, and
algorithm suites. NEVER roll your own.

```python
import aws_encryption_sdk

client = aws_encryption_sdk.EncryptionSDKClient()

kms_key_provider = aws_encryption_sdk.StrictAwsKmsMasterKeyProvider(
    key_ids=['arn:aws:kms:us-east-1:123456789012:key/<key-id>']
)

# Encrypt
with client.stream(
    source=plaintext_io,
    mode='encrypt',
    key_provider=kms_key_provider,
    encryption_context={'department': 'finance', 'app': 'payments'}
) as encryptor:
    ciphertext = encryptor.read()

# Decrypt
with client.stream(
    source=io.BytesIO(ciphertext),
    mode='decrypt',
    key_provider=kms_key_provider
) as decryptor:
    plaintext = decryptor.read()
```

### 6.4 Encryption context

The encryption context is a non-secret map of key/value pairs that is:

- **Authenticated AAD** — bound to the ciphertext. Must match on
  Decrypt.
- **Logged in CloudTrail** — provides audit trail (which context was
  used).
- **Usable in policy conditions** — grants and policies can require
  specific context.

```bash
# Encrypt with context
aws kms encrypt \
  --key-id alias/<name> \
  --plaintext fileb://data.bin \
  --encryption-context '{"department":"finance","env":"prod"}' \
  --output text --query CiphertextBlob \
  | base64 --decode > data.encrypted

# Decrypt with SAME context
aws kms decrypt \
  --ciphertext-blob fileb://data.encrypted \
  --encryption-context '{"department":"finance","env":"prod"}' \
  --output text --query Plaintext | base64 --decode > data.bin
```

A wrong context fails Decrypt with `InvalidCiphertextException`. Use
this to scope access (a grant requiring `department=finance` cannot
decrypt `department=engineering` data, even if both are under the
same CMK).

## 7. Cross-account access

KMS is a **both-must-allow** service. For a principal in account B to
use a CMK in account A:

1. **Account A (key owner):** the key policy MUST grant account B's
   root (or specific role) the relevant KMS actions. Granting root
   allows account B's IAM to scope further.
2. **Account B (caller):** the caller's IAM policy MUST also grant the
   KMS actions on the cross-account CMK ARN.

Both must allow — IAM alone is not enough, key policy alone is not
enough.

### 7.1 Common pattern

```json
// Account A key policy
{
  "Sid": "Allow account B",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::<account-b-id>:root" },
  "Action": ["kms:Decrypt", "kms:DescribeKey", "kms:GenerateDataKey*"],
  "Resource": "*"
}
```

```json
// Account B caller IAM policy
{
  "Effect": "Allow",
  "Action": ["kms:Decrypt", "kms:GenerateDataKey*"],
  "Resource": "arn:aws:kms:us-east-1:<account-a-id>:key/<key-id>"
}
```

### 7.2 Encryption context in cross-account

Account A's key policy can constrain account B's access via the
encryption context:

```json
{
  "Condition": {
    "StringEquals": {
      "kms:EncryptionContext:partner": "account-b"
    }
  }
}
```

This ensures account B can only Decrypt ciphertext encrypted with
`partner=account-b` in the context.

### 7.3 Service-linked grants across accounts

When an AWS service in account B integrates with a CMK in account A
(e.g., an S3 bucket in account A encrypted with the cross-account
CMK, accessed by a role in account B), the service creates a grant
on the CMK. Account A's key policy must allow account B
`kms:CreateGrant` with `kms:GrantIsForAWSResource=true`.

## 8. Quotas and limits

| Resource | Default quota | Adjust |
|---|---|---|
| CMKs per account per Region | 100,000 | Yes (limit increase) |
| GenerateDataKey RPS per CMK | 50,000 (varies by Region) | Yes |
| Encrypt/Decrypt RPS per CMK | 10,000 (varies) | Yes |
| Grants per CMK | 50 (initial) | Yes |
| Key policy size | 32 KB | No |
| Aliases per CMK | 50 | Yes |
| Pending window (deletion) | 7-30 days | Within range |

For high-throughput workloads (millions of GenerateDataKey calls per
second), use envelope encryption with data key caching (the AWS
Encryption SDK does this automatically).

## Full NEVER list (anti-patterns)

- NEVER create a CMK without the account root as break-glass. Without root
  fallback, an accidental policy misconfiguration permanently locks everyone
  out — AWS support cannot recover.
- NEVER grant `kms:*` to any non-root principal. Use scoped statements for
  users vs administrators.
- NEVER combine key administrator and key user into one role. Separation of
  duties: admins manage lifecycle, users access data — never both.
- NEVER rely on IAM alone for CMK access. IAM grants cannot override a key
  policy denial. The key policy MUST explicitly list principals.
- NEVER skip automatic rotation on a `SYMMETRIC_DEFAULT` CMK. Annual rotation
  is free, invisible to callers, limits blast radius of compromise.
- NEVER use a CMK with no deletion window (API enforces 7-30 day). For
  production, set 30 days.
- NEVER assume cross-account access works because account B's IAM is correct.
  KMS requires BOTH key policy AND caller IAM to allow.
- NEVER delete a CMK without confirming no ciphertext is encrypted under it.
  Audit CloudTrail for recent Encrypt / GenerateDataKey usage.
- NEVER use AWS-managed keys when you need cross-account access, rotation
  control, or CloudTrail audit trail of key usage.
- NEVER rotate a multi-Region primary without rotating all replicas.
- NEVER use the CMK directly to encrypt data > 4 KB. Use envelope encryption.
- NEVER omit the encryption context on Encrypt/Decrypt. It is authenticated
  AAD and must match on both operations.
- NEVER deviate from the checklist output format. Substituting `Verdict` for
  literal `VERDICT:` breaks downstream automation.

## Edge-case handling (full detail)

- **Accidental lockout.** If a key policy excludes the root, recovery is
  impossible — AWS support cannot restore access. Always include
  `{"AWS": "arn:aws:iam::<account>:root"}` with `kms:*` as the first
  statement. Validate with IAM policy simulator before applying.

- **Cross-account service-linked role.** When an AWS service in account B
  needs a CMK in account A, the service creates a grant on the CMK. The key
  policy must allow account B `kms:CreateGrant` with
  `kms:GrantIsForAWSResource=true`. Caller IAM in account B must also allow.

- **CMK in PendingDeletion.** Cannot Encrypt or GenerateDataKey, but CAN
  Decrypt (intentional — allows data migration off the doomed key). Cancel
  with `CancelKeyDeletion` if the window has not elapsed.

- **Asymmetric key rotation.** Asymmetric and HMAC CMKs cannot auto-rotate.
  Manual rotation = create new key, update alias, re-encrypt on next access.
  Old key must remain accessible for decrypt of historical ciphertext.

- **Multi-Region replica policy drift.** Each replica has an independent key
  policy. Automate replica policy sync via CloudFormation StackSets or
  Terraform `for_each`.

- **Custom key store disconnect.** If the CloudHSM cluster goes unhealthy or
  `kmsuser` password rotates, the custom key store disconnects and all
  Encrypt/Decrypt on its keys fails. Monitor health, set CloudWatch alarm.

- **CloudTrail `Decrypt` calls.** KMS logs `Decrypt` events with encryption
  context. Use for audit. High-volume `GenerateDataKey` calls are
  rate-limited in CloudTrail by default.

- **Quota limits.** Each CMK supports 50,000 RPS for `GenerateDataKey`
  (Region-wide). For higher throughput, use envelope encryption with data
  key caching (AWS Encryption SDK does this automatically).

## Envelope encryption pattern (full reference)

KMS keys are not used to bulk-encrypt data. Use envelope encryption:

1. **GenerateDataKey** — KMS returns a plaintext data key AND the same key
   encrypted under the CMK.
2. **Encrypt the data** — use a client-side cipher (AES-GCM via AWS
   Encryption SDK) with the plaintext data key.
3. **Store** — discard the plaintext data key. Store ciphertext + encrypted
   data key.
4. **Decrypt** — call `Decrypt` on the encrypted data key. KMS returns
   plaintext data key. Use it to decrypt.

```bash
aws kms generate-data-key \
  --key-id alias/payments-cmk \
  --key-spec AES_256 \
  --encryption-context '{"department":"finance","app":"payments"}'

aws kms decrypt \
  --ciphertext-blob fileb://encrypted-data-key.bin \
  --encryption-context '{"department":"finance","app":"payments"}'
```

Why envelope encryption:
- KMS has a 4 KB limit on `Encrypt` / `Decrypt`.
- KMS request quotas (5,500-50,000 RPS) limit direct encryption. Envelope
  encryption caches the data key.
- The Encryption SDK implements this automatically with key caching and key
  commitment.

Encryption context is authenticated AAD — MUST be identical on Encrypt and
Decrypt. Use it to scope access (grants can require specific context).

## Cross-account access (full reference)

For a principal in account B to use a CMK in account A:

1. **Account A (key owner)** — key policy grants account B's role the KMS
   actions AND `kms:CreateGrant` with `kms:GrantIsForAWSResource=true`.
2. **Account B (caller)** — IAM policy on the caller role must ALSO grant
   KMS actions on the cross-account CMK ARN.

Both policies must allow — KMS is a "both-must-allow" service.

```json
// Account A key policy
{
  "Sid": "Allow cross-account use",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::<account-b-id>:root" },
  "Action": ["kms:Decrypt", "kms:DescribeKey", "kms:GenerateDataKey*"],
  "Resource": "*"
}
```

```json
// Account B caller IAM policy
{
  "Effect": "Allow",
  "Action": ["kms:Decrypt", "kms:GenerateDataKey*"],
  "Resource": "arn:aws:kms:us-east-1:<account-a-id>:key/<key-id>"
}
```
