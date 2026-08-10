---
name: kms-key-deployer
description: 'Provisions AWS KMS keys correctly: key type selection (symmetric AES-256, asymmetric RSA/ECDSA, HMAC), key spec, key policy with separated key administrators vs key users, grants vs key policy, aliases, automatic rotation (symmetric only, annually), multi-Region keys (primary + replicas), custom key store (CloudHSM), deletion window (7-30 days, irreversible), tagging, cross-account access (key policy + caller IAM), and envelope encryption pattern. Emits a READY_TO_DEPLOY checklist with every configuration item verified. Use when creating a new KMS key, deploying a customer-managed CMK, validating a key policy, enabling rotation, or configuring multi-Region keys. Triggers: create KMS key, customer managed key, CMK, key policy, key administrators, key users, KMS grants, automatic rotation, multi-Region keys, CloudHSM custom key store, envelope encryption, cross-account KMS.'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with kms, iam, cloudhsm, ram, and sts access. Works with Terraform aws_kms_key / aws_kms_alias / aws_kms_grant resources, CloudFormation AWS::KMS::Key / AWS::KMS::Alias, and SAM templates.'
keywords:
- aws
- kms
- security
- cloudops
- deploy
- provisioning
- encryption
- key-policy
- cmk
- envelope-encryption
- multi-region
- cloudhsm
- key-rotation
- asymmetric
- grants
tags:
- aws
- kms
- security
- cloudops
- deploy
- encryption
- key-policy
- multi-region
dependencies:
- aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Security
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags:
  - aws
  - kms
  - security
  - cloudops
  - deploy
  - encryption
  - key-policy
  - multi-region
  dependencies:
  - aws-orchestrator
  keywords:
  - create kms key
  - customer managed key
  - kms key policy
  - kms key administrators
  - kms key users
  - kms grants
  - automatic key rotation
  - multi-region kms key
  - cloudhsm custom key store
  - envelope encryption
  - cross-account kms
  - kms asymmetric
  - kms hmac
  when_to_use: Invoke when the user wants to create a new KMS customer-managed key (CMK), provision a multi-Region key, configure a CloudHSM custom key store key, validate a key policy for least-privilege, enable automatic rotation, set up cross-account access, or generate deployment CLI / IaC templates. Do NOT invoke for AWS-managed default keys (S3, EBS, DynamoDB defaults — these are not customer-controllable), or for TLS certificate key material (use ACM).
---

# KMS Key Deployer

An AWS CloudOps agent skill that provisions AWS KMS customer-managed keys
(CMKs) with correct production defaults. The skill walks the operator
through a 10-step provisioning procedure, explains why each default
matters, and emits a READY_TO_DEPLOY checklist verifying every
configuration item.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the provisioning order matters | "Reasoning framework" |
| What to verify before provisioning | "Prerequisites" |
| The ordered provisioning steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Choosing key spec / administrators / users | "Expert heuristic" |
| Workload-specific defaults | "Workload matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/deployment-cli-commands.md` |
| Key policy, grants, multi-Region, CloudHSM | `references/key-policy-and-multiregion-guide.md` |

## Activation keywords

create KMS key, customer managed key, CMK, KMS key policy, key
administrators, key users, KMS grants vs key policy, KMS automatic
rotation, KMS multi-Region key, primary and replica, CloudHSM custom
key store, KMS deletion window, KMS aliases, cross-account KMS,
envelope encryption, KMS symmetric AES-256, KMS asymmetric RSA,
KMS ECDSA, KMS HMAC, KMS key spec, GenerateDataKey,
Encrypt / Decrypt.

## STRICT output contract

When this skill is invoked with a KMS key provisioning request (key
alias, usage, key type, or a partial existing configuration), the agent
MUST respond with the READY_TO_DEPLOY checklist defined in "Output
format" using the literal all-caps labels `KEY:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as the
first lines of the response.

### Required output structure

1. `KEY: <alias-or-key-id>` — the KMS key being provisioned.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING` —
   nothing else.
3. `CHECKLIST:` followed by indented lines, each prefixed with a status
   marker (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented `aws kms ...` /
   `aws iam ...` commands the operator can run.

### 6 FORBIDDEN output patterns (each silently breaks automation)

1. **FORBIDDEN — prose preamble before `KEY:`.** Do not write "Here is
   your provisioning checklist…" or "Sure, let me help…". The first
   non-empty line MUST be `KEY:`.
2. **FORBIDDEN — markdown variants of the labels.** Write `VERDICT:`,
   not `**VERDICT:**`, `### Verdict`, `Verdict =`, or `\`VERDICT\``.
   The labels are case-sensitive all-caps keywords.
3. **FORBIDDEN — swapping verdict tokens.** The verdict is exactly
   `READY_TO_DEPLOY` or `PREREQUISITES_MISSING` — not "ready",
   "missing", "BLOCKED", "OK", or "needs review".
4. **FORBIDDEN — omitting `VERIFICATION_COMMANDS:`.** Even when the
   verdict is `PREREQUISITES_MISSING`, include the commands the operator
   needs to verify the gaps.
5. **FORBIDDEN — extra sections after `VERIFICATION_COMMANDS:`.** The
   checklist block is the entire response. Put deeper explanation in
   `references/` files, not after the block.
6. **FORBIDDEN — status marker drift.** Use only `[✓]`, `[✗]`,
   `[OPTIONAL]`, `[INPUT NEEDED]`. Do not invent `[?]`, `[!]`,
   `[WARN]`, or emoji markers.

### Perfect example (copy the shape exactly)

```text
KEY: alias/payments-cmk
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Key spec — SYMMETRIC_DEFAULT (AES-256-GCM)
  [✓]      Key usage — ENCRYPT_DECRYPT
  [✓]      Origin — AWS_KMS
  [✓]      Key administrators — arn:aws:iam::123456789012:role/kms-admin (kms:Create*, kms:Put*, kms:Enable*, ScheduleKeyDeletion)
  [✓]      Key users — arn:aws:iam::123456789012:role/payments-svc (kms:Encrypt, kms:Decrypt, kms:GenerateDataKey, kms:DescribeKey)
  [✓]      Root account break-glass — arn:aws:iam::123456789012:root (kms:*)
  [✓]      Automatic rotation — enabled (annual, symmetric only)
  [✓]      Alias — alias/payments-cmk
  [✓]      Deletion window — 30 days
  [✓]      Tags — Environment=production, Application=payments
  [OPTIONAL] Multi-Region — single-Region (us-east-1) primary only
  [OPTIONAL] Grants — none (key policy covers all callers)
VERIFICATION_COMMANDS:
  aws kms describe-key --key-id alias/payments-cmk
  aws kms get-key-rotation-status --key-id alias/payments-cmk
  aws kms list-aliases --key-id <key-id>
  aws kms list-resource-tags --key-id <key-id>
  aws kms list-grants --key-id <key-id>
  aws iam get-role-policy --role-name kms-admin --policy-name kms-admin-policy
```

## Reasoning framework (why the provisioning order matters)

KMS key provisioning has **dependency and ordering constraints** that
make the procedure non-trivial. Applying configurations in the wrong
order causes locked-out keys, un-decryptable data, or compliance
violations:

1. **Key spec + key usage FIRST** — the `KeySpec` and `KeyUsage`
   determine what cryptographic operations the key supports. A
   `SYMMETRIC_DEFAULT` key cannot sign; an `RSA_4096` `SIGN_VERIFY`
   key cannot encrypt. Changing the spec after creation requires a new
   key and re-encrypting all data.

2. **Key policy — who can administer vs. who can use (separate!)** —
   the key policy is the ONLY way to grant access to a CMK (IAM alone
   is not enough — IAM grants are subject to the key policy). Separate
   `kms:Create*`/`kms:Disable*`/`ScheduleKeyDeletion` (administrators)
   from `kms:Encrypt`/`kms:Decrypt`/`kms:GenerateDataKey` (users).
   Conflating them produces either lockouts (users can disable the
   key) or over-permission (admins can decrypt production data).

3. **Root account break-glass** — every CMK key policy MUST include the
   account root as a final break-glass principal with `kms:*`. Without
   this, an accidental policy lockout becomes unrecoverable — AWS
   support cannot restore access to a CMK whose policy excludes the
   root.

4. **Aliases** — human-readable names (`alias/<name>`) that point to a
   key ID. Create the alias AFTER the key exists. Aliases can be
   updated to point at a new key (for rotation cutover), decoupling
   the application's reference from the underlying key material.

5. **Automatic rotation** — symmetric CMKs support annual automatic
   rotation (key material rotation, not key ID change). Asymmetric,
   HMAC, and multi-Region primary keys do NOT support automatic
   rotation. Rotation is invisible to callers — the key ARN and ID do
   not change.

6. **Multi-Region keys** — a multi-Region primary key has replicas in
   other Regions. Replicas share the key material with the primary
   but have independent key policies. Create the primary first, then
   replicate. Multi-Region keys cannot auto-rotate.

7. **Deletion window** — when a CMK is scheduled for deletion, AWS
   enforces a mandatory 7-30 day waiting period before irreversible
   deletion. Set to 30 days for production to allow recovery from
   accidental deletion. Deletion is FINAL — encrypted data becomes
   permanently unrecoverable.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **AWS account root access or break-glass** | Every CMK policy MUST include the account root as break-glass. Omitting it makes an accidental lockout unrecoverable. | `aws sts get-caller-identity` (confirm account ID) |
| **Key administrator principal** | An IAM role/user/Group that can administer the key (`kms:Create*`, `kms:Disable*`, `ScheduleKeyDeletion`). | `aws iam get-role --role-name <admin-role>` |
| **Key user principals** | The application roles that need to call `kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey`. | `aws iam get-role --role-name <app-role>` |
| **CloudHSM cluster** (if custom key store) | The CloudHSM cluster must be ACTIVE with at least 2 HSMs across AZs, and the `kmsuser` CU logged out. | `aws cloudhsmv2 describe-clusters` |
| **Cross-account caller IAM** (if cross-account) | The caller account's IAM policy must ALSO grant `kms:Decrypt` etc. — both the key policy AND the caller IAM must allow. | `aws iam get-role --role-name <caller-role>` in caller account |
| **Alias name uniqueness** | Alias names must be unique within an account/Region. `alias/aws/*` is reserved for AWS-managed keys. | `aws kms list-aliases --query 'Aliases[?AliasName==`alias/<name>`]'` |
| **Region** (multi-Region replica) | The replica Region must support KMS (all commercial Regions do). Primary and replica share key material. | `aws kms describe-regions` (via `aws kms list-keys --region <region>`) |
| **IAM permissions** | Caller needs `kms:CreateKey`, `iam:CreatePolicy`/`PutRolePolicy` if attaching to a role, `kms:CreateAlias`, `kms:PutKeyPolicy`. | `aws sts get-caller-identity` |

## Deployment procedure (apply in order)

### Step 1: Key spec + key usage selection

The `KeySpec` and `KeyUsage` together determine the cryptographic
behavior. Choose based on the workload.

**Symmetric encryption key (the common case):**

| KeySpec | KeyUsage | What it does |
|---|---|---|
| `SYMMETRIC_DEFAULT` | `ENCRYPT_DECRYPT` | AES-256-GCM. Default for 95% of workloads (EBS, S3, RDS, Lambda env vars, Secrets Manager). |

**Asymmetric keys:**

| KeySpec | KeyUsage | What it does |
|---|---|---|
| `RSA_2048` / `RSA_3072` / `RSA_4096` | `ENCRYPT_DECRYPT` | RSA encryption (outside AWS — public key downloadable) |
| `RSA_2048` / `RSA_3072` / `RSA_4096` | `SIGN_VERIFY` | RSA signing (code signing, document signing) |
| `ECC_NIST_P256` / `P384` / `P521` | `SIGN_VERIFY` | ECDSA signing (lower latency than RSA) |
| `ECC_NIST_P256` / `P384` | `KEY_AGREEMENT` | ECDH key agreement (mTLS, hybrid encryption) |
| `SM2` (China Regions) | `ENCRYPT_DECRYPT` / `SIGN_VERIFY` | China-only cryptographic standard |

**HMAC keys:**

| KeySpec | KeyUsage | What it does |
|---|---|---|
| `HMAC_256` | `GENERATE_VERIFY_MAC` | HMAC-SHA-256 for message authentication (JWT signing, API tokens) |

**Defaults for common workloads:**

| Workload | KeySpec | KeyUsage |
|---|---|---|
| EBS / S3 / RDS / Lambda / Secrets Manager | `SYMMETRIC_DEFAULT` | `ENCRYPT_DECRYPT` |
| DynamoDB / Aurora / SQS / SNS | `SYMMETRIC_DEFAULT` | `ENCRYPT_DECRYPT` |
| Code signing (Signer) | `RSA_4096` | `SIGN_VERIFY` |
| JWT / API token signing | `HMAC_256` | `GENERATE_VERIFY_MAC` |
| Public-key encryption (downloadable public key) | `RSA_4096` | `ENCRYPT_DECRYPT` |
| ACVP / FIPS 140-3 compliance | `ECC_NIST_P384` | `SIGN_VERIFY` |

**Choose `SYMMETRIC_DEFAULT` unless you have a specific reason not to.**
It is the only spec that supports automatic rotation, the only spec
that integrates with AWS services (S3, EBS, etc.), and the cheapest.

### Step 2: Key policy (separate administrators from users)

The key policy is a JSON resource policy attached directly to the CMK.
**The key policy is the ONLY way to grant access to a CMK** — IAM
policies are evaluated on top of the key policy, but cannot grant
access the key policy denies.

**Canonical least-privilege key policy:**

```json
{
  "Version": "2012-10-17",
  "Id": "key-policy-payments-cmk",
  "Statement": [
    {
      "Sid": "Enable IAM User Permissions (break-glass)",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::123456789012:root" },
      "Action": "kms:*",
      "Resource": "*"
    },
    {
      "Sid": "Allow access for Key Administrators",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::123456789012:role/kms-admin" },
      "Action": [
        "kms:Create*",
        "kms:Describe*",
        "kms:Enable*",
        "kms:List*",
        "kms:Put*",
        "kms:Update*",
        "kms:Revoke*",
        "kms:Disable*",
        "kms:Get*",
        "kms:Delete*",
        "kms:ScheduleKeyDeletion",
        "kms:CancelKeyDeletion",
        "kms:RotateKeyOnDemand"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Allow use of the key (Cryptographic operations)",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::123456789012:role/payments-svc" },
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Allow attachment of persistent resources (grant creation)",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::123456789012:role/payments-svc" },
      "Action": [
        "kms:CreateGrant",
        "kms:ListGrants",
        "kms:RevokeGrant"
      ],
      "Resource": "*",
      "Condition": {
        "Bool": {
          "kms:GrantIsForAWSResource": "true"
        }
      }
    }
  ]
  }
}
```

**What each statement does:**

1. **Break-glass (root)** — gives the account root full access. This
   statement is mandatory — without it, a mistake in subsequent
   statements permanently locks everyone out.
2. **Key administrators** — can manage the key lifecycle (rotate,
   disable, schedule deletion) but CANNOT call Encrypt/Decrypt. This
   separation prevents administrators from reading production data.
3. **Key users** — can call Encrypt/Decrypt/GenerateDataKey. This is
   the application's identity.
4. **Grant creation** — allows AWS services that integrate with KMS
   (e.g., a Lambda function that the service needs to use) to create
   grants on the key when `kms:GrantIsForAWSResource=true`.

**NEVER grant `kms:*` to anyone but the account root.** Even key
administrators should only get lifecycle actions, not cryptographic
operations.

### Step 3: Key administrators vs. key users (the separation principle)

| Capability | Key administrators | Key users |
|---|---|---|
| `kms:Create*`, `kms:Put*`, `kms:Update*` | YES | NO |
| `kms:Enable*`, `kms:Disable*` | YES | NO |
| `kms:ScheduleKeyDeletion`, `kms:CancelKeyDeletion` | YES | NO |
| `kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey*` | NO | YES |
| `kms:Describe*`, `kms:List*` | YES | YES (read-only) |
| `kms:ReEncrypt*` | NO | YES |
| `kms:CreateGrant` | NO | YES (with condition) |

The separation enforces **separation of duties** — the team that
manages the key lifecycle cannot decrypt production data, and the
application that decrypts data cannot disable or delete the key.

### Step 4: Grants vs. key policy

**Key policy** — the persistent JSON document attached to the key.
Use for stable, long-term access (the application's role, the
break-glass root, key admin role).

**Grants** — temporary, programmatic permissions with constraints.
Use for:
- AWS service integrations (Lambda, CodeBuild, EBS attaching to an
  instance): the service creates a grant on the key when an encrypted
  resource is attached.
- Temporary access for a specific operation (e.g., cross-account
  `kms:Decrypt` for a migration).
- Tighter scoping than the key policy allows (e.g., `kms:Encrypt` only
  on a specific encryption context).

```bash
aws kms create-grant \
  --key-id alias/payments-cmk \
  --grantee-principal arn:aws:iam::123456789012:role/migration-tool \
  --operations Decrypt \
  --constraints '{"EncryptionContextSubset": {"department": "finance"}}' \
  --retiring-principal arn:aws:iam::123456789012:role/kms-admin
```

Grants are subject to the key policy (the grantee must be allowed by
the policy AND the grant). Grants are eventually consistent — allow
~5 seconds for propagation.

**Rule of thumb:** prefer the key policy for human/long-term roles;
prefer grants for service integrations and temporary access.

### Step 5: Aliases

```bash
aws kms create-alias \
  --alias-name alias/payments-cmk \
  --target-key-id <key-id>
```

**Alias rules:**
- Prefix `alias/` is mandatory. `alias/aws/*` is reserved for
  AWS-managed keys.
- Unique within account/Region.
- Can be updated to point at a different key (`UpdateAlias`) —
  applications referencing the alias transparently use the new key.
  Useful for rotation cutover.
- Cannot be deleted if it is the only reference to a key — but you can
  delete the alias and the key independently.

**Convention:** name aliases after the workload
(`alias/payments-cmk`, `alias/audit-evidence`,
`alias/code-signing`). Avoid generic names like `alias/my-key`.

### Step 6: Automatic rotation

```bash
aws kms enable-key-rotation --key-id alias/payments-cmk
```

**Rotation rules:**
- **Symmetric CMKs (`SYMMETRIC_DEFAULT`)**: support annual automatic
  rotation. The key material rotates once per year. The key ARN, ID,
  and policy do not change. Existing ciphertext remains decryptable.
- **Asymmetric CMKs (RSA, ECC)**: do NOT support automatic rotation.
  Manual rotation requires creating a new key and re-encrypting.
- **HMAC CMKs**: do NOT support automatic rotation. Manual rotation
  required.
- **Multi-Region primary keys**: do NOT support automatic rotation
  (rotation would desync replicas). Use manual rotation or on-demand
  rotation where available.
- **Custom key store keys (CloudHSM)**: support automatic rotation
  since 2023 (rotates key material in the CloudHSM cluster).

**On-demand rotation (2024-2025):** `kms:RotateKeyOnDemand` triggers
immediate key material rotation for eligible symmetric keys, bypassing
the annual schedule. Useful for incident response (suspected key
material compromise).

Rotation is invisible to callers — `GenerateDataKey` always returns
the latest key material, and old ciphertext remains decryptable via
the key's retained history.

### Step 7: Multi-Region keys (primary + replicas)

```bash
# Primary (multi-Region)
aws kms create-key \
  --description "Payments CMK (primary)" \
  --origin AWS_KMS \
  --multi-region \
  --policy file://policy.json

# Replica in us-west-2
aws kms replicate-key \
  --key-id arn:aws:kms:us-east-1:123456789012:key/<primary-key-id> \
  --replica-region us-west-2 \
  --policy file://replica-policy.json
```

**Multi-Region rules:**
- The primary and replicas share key material — any replica can
  decrypt data encrypted by the primary or another replica.
- Each Region's replica has an INDEPENDENT key policy. Set the replica
  policy to grant the application roles in that Region.
- Multi-Region keys CANNOT auto-rotate (rotation would desync
  replicas). Plan manual rotation across all replicas.
- Use cases: disaster recovery across Regions, cross-Region encrypted
  EBS snapshot restore, global DynamoDB tables with a single
  encryption key.

### Step 8: Custom key store (CloudHSM)

For workloads requiring key material in a customer-owned HSM (FIPS
140-2 Level 3 compliance, regulatory key custody):

```bash
# 1. CloudHSM cluster must be ACTIVE with >= 2 HSMs
aws cloudhsmv2 describe-clusters

# 2. Create custom key store linked to the CloudHSM cluster
aws kms create-custom-key-store \
  --custom-key-store-name payments-hsm-keystore \
  --cloud-hsm-cluster-id cluster-xxx \
  --trust-anchor certificate.pem \
  --key-store-admin-credentials <kmsuser-password> \
  --hsm-credentials <hsm-password>

# 3. Connect the key store
aws kms connect-custom-key-store --custom-key-store-id cks-xxx

# 4. Create key in the custom key store
aws kms create-key \
  --custom-key-store-id cks-xxx \
  --description "Payments CMK (CloudHSM)" \
  --policy file://policy.json
```

**CloudHSM custom key store rules:**
- The `kmsuser` crypto user (CU) must be created on the HSM and LOGGED
  OUT before KMS connects. KMS logs in as `kmsuser`.
- The cluster must have >= 2 active HSMs across different AZs.
- Keys in a custom key store support `SYMMETRIC_DEFAULT`,
  `RSA_*`, `ECC_*`, and `HMAC_256`. They do NOT support automatic
  rotation in all configurations — verify per Region.
- A disconnected key store blocks all Encrypt/Decrypt on its keys.

### Step 9: Deletion window

```bash
aws kms schedule-key-deletion --key-id alias/payments-cmk --pending-window-in-days 30
```

**Deletion rules:**
- Window: 7-30 days. Default is 30 days.
- Deletion is IRREVERSIBLE — once the window expires, the key material
  is destroyed and all ciphertext encrypted under the key becomes
  permanently unrecoverable.
- The key is in `PendingDeletion` state during the window. It can be
  cancelled with `CancelKeyDeletion`.
- During `PendingDeletion`, the key CANNOT be used for Encrypt or
  GenerateDataKey, but CAN be used for Decrypt (so existing data can
  be migrated).
- For production, ALWAYS set the window to 30 days.

### Step 10: Tagging + verification

```bash
aws kms tag-resource \
  --key-id <key-id> \
  --tags '[{"TagKey":"Environment","TagValue":"production"},{"TagKey":"Application","TagValue":"payments"}]'

aws kms describe-key --key-id alias/payments-cmk
aws kms get-key-rotation-status --key-id alias/payments-cmk
aws kms list-aliases --key-id <key-id>
aws kms list-resource-tags --key-id <key-id>
aws kms list-grants --key-id <key-id>
aws kms get-key-policy --key-id <key-id> --policy-name default
```

## Envelope encryption pattern

KMS keys are not used to bulk-encrypt data. Instead, use **envelope
encryption** — KMS protects a data key, the data key protects the
payload:

1. **Encrypt:** the application calls `GenerateDataKey` on the CMK.
   KMS returns a plaintext data key (up to 1024 bits) AND the same key
   encrypted under the CMK.
2. **Encrypt the data:** use a client-side cipher (AES-GCM in the AWS
   SDK's `EncryptionSDK`) with the plaintext data key.
3. **Store:** discard the plaintext data key. Store the ciphertext and
   the encrypted data key alongside it.
4. **Decrypt:** the application calls `Decrypt` on the encrypted data
   key. KMS returns the plaintext data key. Use it to decrypt the
   ciphertext.

```bash
# Generate a data key (returns plaintext + encrypted data key)
aws kms generate-data-key \
  --key-id alias/payments-cmk \
  --key-spec AES_256 \
  --encryption-context '{"department":"finance","app":"payments"}'

# Decrypt the encrypted data key when needed
aws kms decrypt \
  --ciphertext-blob fileb://encrypted-data-key.bin \
  --encryption-context '{"department":"finance","app":"payments"}'
```

**Why envelope encryption:**
- KMS has a 4 KB limit on `Encrypt` / `Decrypt` — envelope encryption
  handles arbitrary payload sizes.
- KMS request quotas (5,500-50,000 RPS depending on Region) limit
  direct KMS encryption. Envelope encryption caches the data key.
- The Encryption SDK (`@aws-crypto/client-*` for JS/Python/Java)
  implements this automatically with key caching and key commitment.

**Encryption context** — the `--encryption-context` map is
authenticated AAD (additional authenticated data). It MUST be
identical on Encrypt and Decrypt. Use it to scope access (e.g., grant
can require `department=finance` context).

## Cross-account access

For a principal in account B to use a CMK in account A:

1. **Account A (key owner)** — key policy must grant account B's role
   the relevant KMS actions (`kms:Decrypt`, etc.) AND grant
   `kms:CreateGrant` with `kms:GrantIsForAWSResource=true` for service
   integrations.
2. **Account B (caller)** — IAM policy on the caller role must
   ALSO grant `kms:Decrypt` on the cross-account CMK ARN.

Both policies must allow — KMS is a "both-must-allow" service, not an
"either-or".

```json
// Account A key policy — grants account B root (so account B IAM can scope further)
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

## Workload matrix

| Workload | KeySpec | Rotation | Multi-Region | Origin | Notes |
|---|---|---|---|---|---|
| EBS / S3 / RDS / Lambda env vars | `SYMMETRIC_DEFAULT` | Annual | Optional | AWS_KMS | Default for AWS service integration |
| DynamoDB / Aurora / SQS / SNS | `SYMMETRIC_DEFAULT` | Annual | Optional | AWS_KMS | Use customer-managed CMK for full control |
| Secrets Manager | `SYMMETRIC_DEFAULT` | Annual | No | AWS_KMS | One CMK per secret-class |
| Code signing (Signer) | `RSA_4096` SIGN_VERIFY | Manual | Optional | AWS_KMS | Cannot auto-rotate |
| JWT / API tokens | `HMAC_256` | Manual | Optional | AWS_KMS | Cannot auto-rotate |
| Cross-Region DR | `SYMMETRIC_DEFAULT` | Manual | YES | AWS_KMS | Replica per Region; no auto-rotation |
| FIPS / regulatory | `SYMMETRIC_DEFAULT` | Annual | No | CloudHSM | Custom key store |
| Public-key encryption (downloadable public key) | `RSA_4096` ENCRYPT_DECRYPT | Manual | Optional | AWS_KMS | Asymmetric; cannot auto-rotate |
| Document signing | `ECC_NIST_P384` SIGN_VERIFY | Manual | Optional | AWS_KMS | Lower latency than RSA |

## Recent AWS features (2024-2026)

- **On-demand key rotation (2024-2025):** `kms:RotateKeyOnDemand`
  triggers immediate rotation for eligible symmetric CMKs, bypassing
  the annual schedule. Use for incident response (suspected key
  compromise). The key ARN and policy do not change.

- **Key spec HMAC_256 GA (2024):** HMAC keys for message authentication
  (JWT signing, API tokens). `KeyUsage=GENERATE_VERIFY_MAC`. Does NOT
  support automatic rotation.

- **CloudHSM custom key store rotation (2024-2025):** custom key store
  keys now support automatic rotation in more Regions. Previously
  manual-only. Verify Region support before relying on it.

- **ECDH key agreement (2024-2025):** `ECC_NIST_P256`/`P384` with
  `KeyUsage=KEY_AGREEMENT` for mTLS and hybrid post-quantum schemes.

- **Key policy hash check (2024):** `DescribeKey` now returns a hash of
  the key policy, enabling drift detection in CI.

- **XKS (External Key Store) GA (2024-2025):** for workloads needing
  key material outside AWS entirely (external HSM over a standard
  API). Replace CloudHSM custom key stores for some regulated
  workloads.

- **VPC endpoint policy support (2024):** KMS interface VPC endpoints
  now support endpoint policies — control which CMKs are reachable
  from a VPC.

- **MAC algorithms expanded (2025):** HMAC keys now support additional
  MAC algorithm options via KeySpec; verify Region support.

## NEVER (anti-patterns)

- NEVER create a CMK without the account root as break-glass
  (`{"AWS": "arn:aws:iam::<account>:root"}` with `kms:*`). Without
  root fallback, an accidental policy misconfiguration permanently
  locks everyone out — AWS support cannot recover a CMK whose policy
  excludes the root.

- NEVER grant `kms:*` to any non-root principal. Use scoped statements:
  `kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey*` for users;
  `kms:Create*` / `kms:Disable*` / `ScheduleKeyDeletion` for
  administrators. Granting full access conflates administration and
  data access.

- NEVER combine key administrator and key user into one role. The
  separation of duties is the entire point of having both: admins
  should not be able to read production data, and applications should
  not be able to disable or delete the key.

- NEVER rely on IAM alone for CMK access. IAM grants are evaluated on
  top of the key policy — they cannot grant access the key policy
  denies. The key policy MUST explicitly list the principals.

- NEVER skip automatic rotation on a `SYMMETRIC_DEFAULT` CMK. Annual
  rotation is free, invisible to callers, and limits the blast radius
  of a key material compromise. Asymmetric / HMAC / multi-Region keys
  cannot auto-rotate — document the manual rotation procedure.

- NEVER use a CMK with no deletion window (the API enforces a 7-30 day
  window). For production, set the window to 30 days. A 7-day window
  leaves too little time to recover from accidental deletion.

- NEVER assume cross-account access works because account B's IAM is
  correct. KMS requires BOTH the key policy (in account A) AND the
  caller IAM (in account B) to allow. A missing key policy statement
  fails silently with `AccessDeniedException`.

- NEVER delete a CMK without confirming there is no ciphertext
  encrypted under it. Once the deletion window expires, all data
  encrypted under the key is permanently unrecoverable. Audit
  CloudTrail for recent Encrypt / GenerateDataKey usage.

- NEVER use AWS-managed keys (`alias/aws/s3`, `alias/aws/ebs`) when you
  need cross-account access, rotation control, or a CloudTrail audit
  trail of key usage. AWS-managed keys cannot be shared across
  accounts and rotate on AWS's schedule (not yours).

- NEVER rotate a multi-Region primary without rotating all replicas.
  Rotation would desync the primary and replicas, breaking
  cross-Region decrypt. Multi-Region keys cannot auto-rotate for this
  reason.

- NEVER use the CMK directly to encrypt data > 4 KB. KMS has a 4 KB
  payload limit on Encrypt/Decrypt. Use envelope encryption
  (GenerateDataKey + client-side cipher) — the AWS Encryption SDK
  handles this automatically.

- NEVER omit the encryption context on Encrypt/Decrypt. The encryption
  context is authenticated AAD — it binds ciphertext to a context
  (department, app, file ID) and must match on Decrypt. A missing
  context on Encrypt silently weakens the binding.

- NEVER deviate from the checklist output format. Substituting
  `Verdict` / `**VERDICT**` / `### Verdict:` for the literal `VERDICT:`
  label silently breaks downstream deployment pipelines and
  assertion-based evals.

## Expert heuristic — choosing key spec, administrators, and users

**Key spec — default to `SYMMETRIC_DEFAULT`:** it is the only spec
that integrates with AWS services (S3, EBS, RDS, Lambda, Secrets
Manager), supports annual automatic rotation, and is the cheapest.
Choose asymmetric only when you need: (a) public-key encryption where
the public key is downloadable outside AWS, (b) digital signatures
verifiable outside AWS, or (c) HMAC for token signing.

**Administrators — one role per security team:** create a single
`kms-admin` role (or a dedicated IAM group) and grant it
`kms:Create*`/`kms:Put*`/`ScheduleKeyDeletion` on all CMKs. The
administrator role should NOT have `kms:Decrypt` — separation of
duties.

**Users — one role per application:** grant `kms:Encrypt`,
`kms:Decrypt`, `kms:GenerateDataKey*` to the specific application
role. Never grant to a broad group like "Developers" — that lets
engineers read production ciphertext.

**Break-glass — root always:** the account root MUST be in the key
policy with `kms:*`. This is not a violation of least privilege — it
is the recovery path when the human-configured statements fail.

**Rotation — symmetric: on, asymmetric/HMAC: plan manual:** enable
annual rotation on every symmetric CMK. For asymmetric / HMAC, document
the manual rotation procedure (create new key, update alias, re-encrypt
on next access). Test the rotation cutover annually.

**Multi-Region — only when you actually need it:** multi-Region keys
add complexity (no auto-rotation, per-Region policy sync). Use only
for cross-Region DR, global-table encryption, or cross-Region snapshot
restore. Single-Region is the right default.

**Encryption context — always include identifying fields:** use a
stable context like `{"app":"payments","env":"prod"}` or
`{"file_id":"<uuid>"}`. The context scopes grants (a grant can require
a specific context) and provides an audit trail in CloudTrail.

## Pre-flight safety checks (run before any provisioning CLI)

- **Confirm the AWS account ID (for root break-glass):**
  ```bash
  aws sts get-caller-identity --query Account --output text
  ```
  The key policy will reference `arn:aws:iam::<account-id>:root`.

- **Confirm the key administrator role exists:**
  ```bash
  aws iam get-role --role-name <admin-role>
  ```

- **Confirm the application (key user) role exists:**
  ```bash
  aws iam get-role --role-name <app-role>
  ```

- **Confirm the alias is available:**
  ```bash
  aws kms list-aliases --query 'Aliases[?AliasName==`alias/<name>`]'
  ```

- **For custom key store, confirm the CloudHSM cluster is ACTIVE:**
  ```bash
  aws cloudhsmv2 describe-clusters --query 'Clusters[].{Id:ClusterId,State:State,HsmCount:length(Hsms)}'
  ```
  Need `State=ACTIVE` and `HsmCount >= 2`.

- **For multi-Region, confirm the replica Region is enabled:**
  ```bash
  aws kms list-keys --region <replica-region>
  ```

- **For existing keys, capture current policy for rollback:**
  ```bash
  aws kms get-key-policy --key-id <key-id> --policy-name default --output text > /tmp/<key-id>-policy-backup.json
  ```

## Output format — MANDATORY literal labels

When invoked with a key provisioning request, your ENTIRE response
MUST be the checklist block below. The labels are **case-sensitive
all-caps keywords** — write them EXACTLY as shown. Do NOT substitute
`Verdict`, `**VERDICT**`, `### Verdict`, or any markdown variant. Do
NOT write a preamble ("Here is your provisioning checklist…"). Start
with `KEY:` and stop after the `VERIFICATION_COMMANDS:` block.

```text
KEY: <alias-or-key-id>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Key spec — <SYMMETRIC_DEFAULT | RSA_4096 | HMAC_256 | ...>
  [✓]      Key usage — <ENCRYPT_DECRYPT | SIGN_VERIFY | GENERATE_VERIFY_MAC | KEY_AGREEMENT>
  [✓]      Origin — <AWS_KMS | AWS_CLOUDHSM | EXTERNAL_KEY_STORE>
  [✓]      Key administrators — <admin-role-arn> (lifecycle actions only, no Encrypt/Decrypt)
  [✓]      Key users — <app-role-arns> (Encrypt, Decrypt, GenerateDataKey)
  [✓]      Root account break-glass — arn:aws:iam::<account>:root (kms:*)
  [✓]      Automatic rotation — <enabled annual | not supported for this spec>
  [✓]      Alias — alias/<name>
  [✓]      Deletion window — <7-30 days>
  [✓]      Tags — <key=value pairs>
  [OPTIONAL] Multi-Region — <primary only | primary + replicas in <regions>>
  [OPTIONAL] Grants — <none | service integrations>
VERIFICATION_COMMANDS:
  aws kms describe-key --key-id alias/<name>
  aws kms get-key-rotation-status --key-id alias/<name>
  aws kms get-key-policy --key-id <key-id> --policy-name default
  aws kms list-aliases --key-id <key-id>
  aws kms list-resource-tags --key-id <key-id>
  aws kms list-grants --key-id <key-id>
```

**Status marker semantics:**
- `[✓]` — configuration is applied and verified.
- `[✗]` — configuration is NOT applied or is misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required for the workload type.
- `[INPUT NEEDED]` — a prerequisite value is missing (admin role ARN,
  app role ARN, CloudHSM cluster ID) and the operator must provide it
  before provisioning can proceed.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is
missing (administrator role ARN, application role ARN, CloudHSM
cluster for a custom key store key), the verdict is
`PREREQUISITES_MISSING` with each gap listed. The checklist shows the
target configuration with `[INPUT NEEDED]` or `[✗]` for unmet
prerequisites.

## Edge-case handling

- **Accidental lockout.** If a key policy misconfiguration excludes
  the root, recovery is impossible — AWS support cannot restore
  access. Always include `{"AWS": "arn:aws:iam::<account>:root"}`
  with `kms:*` as the first statement. For defense, validate the
  policy with `aws kms put-key-policy --policy` and a dry-run IAM
  policy simulator before applying.

- **Cross-account service-linked role.** When an AWS service in
  account B needs to use a CMK in account A (e.g., a Lambda function),
  the service creates a grant on the CMK. The key policy must allow
  account B `kms:CreateGrant` with `kms:GrantIsForAWSResource=true`.
  The caller IAM in account B must also allow the KMS actions.

- **CMK in PendingDeletion.** A key in `PendingDeletion` cannot
  Encrypt or GenerateDataKey, but CAN Decrypt. This is intentional —
  it allows data migration off the doomed key. Cancel deletion with
  `CancelKeyDeletion` if the deletion window has not elapsed.

- **Asymmetric key rotation.** Asymmetric and HMAC CMKs cannot
  auto-rotate. Manual rotation = create a new key, update the alias
  to point at the new key, and re-encrypt data on next access. The
  old key must remain accessible for decrypt of historical ciphertext.

- **Multi-Region replica policy drift.** Each replica has an
  independent key policy. A common mistake is to update the primary
  policy and forget to update replica policies. Automate replica
  policy sync via CloudFormation StackSets or Terraform `for_each`.

- **Custom key store disconnect.** If the CloudHSM cluster goes
  unhealthy or the `kmsuser` password rotates, the custom key store
  disconnects and all Encrypt/Decrypt on its keys fails. Monitor
  `ConnectCustomKeyStore` health and set a CloudWatch alarm.

- **CloudTrail `Decrypt` calls.** KMS logs `Decrypt` events to
  CloudTrail with the encryption context. Use this for audit — it
  shows which principal decrypted what data. Note: high-volume
  GenerateDataKey calls are rate-limited in CloudTrail by default.

- **Quota limits.** Each CMK supports 50,000 RPS for
  `GenerateDataKey` (request quota, Region-wide). For higher
  throughput, use envelope encryption with data key caching (the
  AWS Encryption SDK does this automatically).

## Section taxonomy (CloudOps deployer pattern)

1. **Frontmatter** — name, description, version, when-to-use.
2. **Quick navigation** — what each section covers.
3. **Activation keywords** — discoverability terms.
4. **STRICT output contract** — mandatory output format + FORBIDDEN
   patterns + perfect example.
5. **Reasoning framework** — the *why* behind the provisioning order.
6. **Prerequisites** — what must be verified before provisioning.
7. **Deployment procedure** — the ordered 10-step provisioning
   sequence.
8. **Envelope encryption pattern** — the canonical KMS usage pattern.
9. **Cross-account access** — key policy + caller IAM.
10. **Workload matrix** — per-workload configuration.
11. **Recent AWS features** — 2024-2026 feature changes.
12. **NEVER** — anti-patterns with explicit *why* each is wrong.
13. **Expert heuristic** — key spec, admin, user selection rules of
    thumb.
14. **Pre-flight safety checks** — non-destructive provisioning guards.
15. **Output format** — the fixed checklist report shape.
16. **Edge-case handling** — lockout, cross-account, multi-Region,
    CloudHSM.
17. **References** — pointer to deeper references.

## Domain

AWS CloudOps / KMS Cryptographic Key Provisioning.

## AWS documentation

- **AWS KMS Developer Guide** — https://docs.aws.amazon.com/kms/latest/developerguide/overview.html
- **KMS Key Policies** — https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html
- **KMS Key Spec** — https://docs.aws.amazon.com/kms/latest/developerguide/kms-developer-guide.html#concepts
- **KMS Rotating Keys** — https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html
- **KMS Multi-Region Keys** — https://docs.aws.amazon.com/kms/latest/developerguide/multi-region-keys-overview.html
- **KMS Custom Key Store** — https://docs.aws.amazon.com/kms/latest/developerguide/custom-key-store-overview.html
- **KMS Grants** — https://docs.aws.amazon.com/kms/latest/developerguide/grants.html
- **Envelope Encryption** — https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html#enveloping
- **KMS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/kms/

## References

- `references/deployment-cli-commands.md` — full copy-pasteable CLI
  command sequence for all 10 provisioning steps, including key
  creation, key policy, alias, rotation, multi-Region replicas,
  CloudHSM custom key store, deletion, and Terraform
  `aws_kms_key` / `aws_kms_alias` / `aws_kms_grant` resource
  equivalents.

- `references/key-policy-and-multiregion-guide.md` — deep reference on
  key policy structure (administrators vs. users, grants, encryption
  context), multi-Region primary/replica internals, CloudHSM custom
  key store lifecycle, envelope encryption patterns, and cross-account
  access (both-must-allow semantics).
