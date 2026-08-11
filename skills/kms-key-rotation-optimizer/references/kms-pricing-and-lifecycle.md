# KMS Pricing and Lifecycle Reference

Supplementary reference for the KMS Key Rotation Optimizer skill. Loaded
on-demand when detailed pricing math, rotation configuration, grant
lifecycle details, or multi-region key setup steps are needed.

## KMS pricing (us-east-1, 2026, USD)

### Key pricing

| Key type | Monthly cost | Notes |
|---|---|---|
| AWS managed key | $0.00/month | Created by AWS services; cannot be deleted |
| Customer managed key | $1.00/month | Standard symmetric or asymmetric key |
| Multi-region primary key | $1.00/month | Same as standard customer-managed key |
| Multi-region replica key | $1.00/month per region | Each replica billed independently |
| Custom key store (CloudHSM) | $1.00/month | Additional CloudHSM cluster costs apply |

### Request pricing (customer-managed keys)

| Request tier | $/request | Notes |
|---|---|---|
| First 150K/month | $0.03 per 10,000 ($0.000003/req) | Standard tier |
| Over 150K/month | $0.02 per 10,000 ($0.000002/req) | Volume tier |

### Request pricing (AWS managed keys)

| Request tier | $/request | Notes |
|---|---|---|
| Free tier | 2,000,000 requests/month free | Per AWS managed key |
| Over free tier | $0.03 per 10,000 | Same rate as customer-managed |

### Free tier

- AWS managed keys: $0/month key cost + 2M free requests
- Customer managed keys: NO free tier on key cost ($1/month starts at creation)
- Customer managed keys: NO free request tier ($0.03/10K from first request)

## Key types and rotation support

| Key type | Rotation support | Default | Notes |
|---|---|---|---|
| AWS managed (symmetric) | Annual automatic | Enabled (cannot disable) | Free |
| Customer managed (symmetric) | Annual automatic | Disabled | Enable via CLI; same key ARN |
| Customer managed (asymmetric) | Annual automatic | Disabled | Supported since 2024 |
| Customer managed (HMAC) | Annual automatic | Disabled | Supported since 2024 |
| Custom key store | Not supported | N/A | Key material in CloudHSM |

### Rotation transparency

When automatic rotation fires on a customer-managed key:
- The **key ARN stays the same** — all aliases, policies, grants remain valid
- The **backing key material changes** under the same ARN
- Applications referencing the key by ARN or alias are **unaffected**
- The old backing key is retained for decryption of previously encrypted data
- Rotation is **free** — no additional billing

This is fundamentally different from **manual rotation** which creates a
new key with a new ARN.

## Key lifecycle states

```
Creating → Enabled → Disabled → PendingDeletion → Deleted
              │                      │
              └── PendingImport ─────┘
                   (for imported keys)
```

| State | Billing | API calls accepted | Notes |
|---|---|---|---|
| Enabled | $1/month | Yes (Decrypt, Encrypt, GenerateDataKey) | Normal operation |
| Disabled | $1/month | No | Still bills; evaluate deletion |
| PendingDeletion | $1/month (until window expires) | No | Billing stops at permanent deletion |
| PendingImport | $0/month | No | Waiting for key material import |

### Deletion window details

- Minimum: **7 days**
- Maximum: **30 days** (standard); **120 days** (via support case)
- Billing continues through the entire window
- Cancellation: `aws kms cancel-key-deletion --key-id <id>`
- After permanent deletion: **IRREVERSIBLE**. Data encrypted under the
  key is permanently unrecoverable.

```bash
# Schedule deletion (7-day minimum)
aws kms schedule-key-deletion --key-id <id> --pending-window-in-days 7

# Cancel deletion (before window expires)
aws kms cancel-key-deletion --key-id <id>
```

## Grant lifecycle

### Grant creation

```bash
aws kms create-grant \
  --key-id <key-id> \
  --grantee-principal arn:aws:iam::123456789012:role/MyAppRole \
  --operations Decrypt Encrypt \
  --retiring-principal arn:aws:iam::123456789012:role/MyGrantAdmin
```

### Grant expiration

- Grants do NOT auto-expire unless `ExpiryDate` is set at creation
- `ExpiryDate` uses Unix epoch seconds
- After expiry, the grant must be retired manually

```bash
# Create a grant with expiry
aws kms create-grant \
  --key-id <key-id> \
  --grantee-principal arn:aws:iam::...:role/TempRole \
  --operations Decrypt \
  --constraints '{"EncryptionContextSubset":{"Department":"Finance"}}' \
  --expiry-date $(date -d '+7 days' +%s)
```

### Grant retirement

```bash
# Retire a single grant
aws kms retire-grant --key-id <key-id> --grant-id <grant-id>

# List grants to find expired ones
aws kms list-grants --key-id <key-id>
```

Grant retirement is **idempotent** — safe to retry. Grant revocation
(`revoke-grant`) is different and immediate; use `retire-grant` for
planned lifecycle management.

### Grant limits

| Limit | Value | Notes |
|---|---|---|
| Grants per key | ~2,500 (soft) | Request increase via support |
| Tokens per creation | 1 | Grant token returned at creation |
| Nesting | None | Grants cannot delegate grant creation |

## Multi-region key configuration

### Create a multi-region primary key

```bash
aws kms create-key --origin AWS_KMS --multi-region
# Note the KeyId — this is the primary key
```

### Create a replica in another region

```bash
aws kms replicate-key \
  --key-id arn:aws:kms:us-east-1:...:key/primary-id \
  --replica-region eu-west-1
```

### Delete a replica (does NOT affect primary)

```bash
# In the replica's region
aws kms schedule-key-deletion \
  --key-id arn:aws:kms:eu-west-1:...:key/replica-id \
  --pending-window-in-days 7
```

Each replica is independently billed at $1/month per region. Deleting a
replica does not affect the primary or other replicas.

## Cross-account key usage

### Cross-account grant pattern

```bash
# In account A (key owner)
aws kms create-grant \
  --key-id <key-id> \
  --grantee-principal arn:aws:iam::<account-B>:role/CrossAccountRole \
  --operations Decrypt Encrypt GenerateDataKey \
  --constraints '{"EncryptionContextSubset":{"Application":"SharedData"}}'
```

The grant token must be passed with each API call from account B. Best
practice: set an `ExpiryDate` and implement a refresh mechanism.

### Key policy for cross-account

The key policy must allow the grantee principal:

```json
{
  "Sid": "AllowCrossAccountUse",
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::<account-B>:root"
  },
  "Action": [
    "kms:Decrypt",
    "kms:Encrypt",
    "kms:GenerateDataKey"
  ],
  "Resource": "*"
}
```

## Alias management

```bash
# Create an alias
aws kms create-alias --alias-name alias/my-app --target-key-id <key-id>

# List aliases
aws kms list-aliases

# Update alias to point at a new key (manual rotation)
aws kms update-alias --alias-name alias/my-app --target-key-id <new-key-id>

# Delete an alias (does NOT delete the key)
aws kms delete-alias --alias-name alias/my-app
```

Aliases are **free** — no cost benefit to reducing them. The value is
operational: alias-based references survive key changes.

## Extended anti-pattern catalog

1. **NEVER delete a key that encrypts active data.** KMS key deletion is
   irreversible. Data encrypted under the key is permanently lost.

2. **NEVER assume a key with low API call volume is unused.** Keys may
   encrypt rarely-accessed archived data.

3. **NEVER consolidate keys serving different compliance domains.**

4. **NEVER disable rotation for cost reasons.** Rotation is free.

5. **NEVER retire a grant that an active workload depends on.** Check
   CloudTrail for recent usage.

6. **NEVER create a new key for manual rotation without planning the old
   key's retirement.** Overlap costs $2/month until the old key is deleted.

7. **NEVER schedule key deletion with a 30-day window when 7 days
   suffices.** The $1/month billing continues through the window.

8. **NEVER ignore PendingDeletion keys in cost reports.** They still bill
   until permanently deleted.

## CloudTrail KMS event filtering

```bash
# Count Decrypt events for a key in the last 30 days
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=<key-id> \
  --start-time $(date -d '-30 days' +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --attribute-key eventCategory \
  --attribute-value Management \
  --query 'Events[?EventName==`Decrypt`]' \
  --output text | wc -l
```

Note: CloudTrail lookup-events has a 90-day retention window. For
longer analysis, use Athena on CloudTrail S3 logs.
