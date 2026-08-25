---
name: kms-key-deployer
description: 'Provisions AWS KMS keys correctly: key type selection (symmetric AES-256, asymmetric RSA/ECDSA, HMAC), key spec, key policy with separated key administrators vs key users, grants vs key policy, aliases, automatic rotation (symmetric only, annually), multi-Region keys (primary + replicas), custom key store (CloudHSM), deletion window (7-30 days, irreversible), tagging, cross-account access (key policy + caller IAM), and envelope encryption pattern. Emits a READY_TO_DEPLOY checklist with every configuration item verified. Use when creating a new KMS key, deploying a customer-managed CMK, validating a key policy, enabling rotation, or configuring multi-Region keys. Triggers: create KMS key, customer managed key, CMK, key policy, key administrators, key users, KMS grants, automatic rotation, multi-Region keys, CloudHSM custom key store, envelope encryption, cross-account KMS.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with kms, iam, cloudhsm, ram, and sts access. Works with Terraform aws_kms_key / aws_kms_alias / aws_kms_grant resources, CloudFormation AWS::KMS::Key / AWS::KMS::Alias, and SAM templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, kms, security, cloudops, deploy, encryption, key-policy, multi-region
  dependencies: aws-orchestrator
  keywords: aws, kms, security, cloudops, deploy, provisioning, encryption, key-policy, cmk, envelope-encryption, multi-region, cloudhsm, key-rotation, asymmetric, grants
  when_to_use: Invoke when the user wants to create a new KMS customer-managed key (CMK), provision a multi-Region key, configure a CloudHSM custom key store key, validate a key policy for least-privilege, enable automatic rotation, set up cross-account access, or generate deployment CLI / IaC templates. Do NOT invoke for AWS-managed default keys (S3, EBS, DynamoDB defaults — these are not customer-controllable), or for TLS certificate key material (use ACM).
---

# KMS Key Deployer

An AWS CloudOps agent skill that provisions AWS KMS customer-managed keys
(CMKs) with correct production defaults. Emits a READY_TO_DEPLOY checklist
verifying every configuration item.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the provisioning order matters | "Reasoning framework" |
| What to verify before provisioning | "Prerequisites" |
| The ordered provisioning steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Key policy, grants, multi-Region, CloudHSM | "Deployment procedure" Steps 2-8 |
| Workload-specific defaults | "Workload matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/deployment-cli-commands.md` |
| Key policy, grants, multi-Region, CloudHSM, cross-account, envelope | `references/key-policy-and-multiregion-guide.md` |

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
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING`.
3. `CHECKLIST:` followed by indented lines with status markers
   (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented `aws kms ...` commands.

### FORBIDDEN output patterns

- **No prose preamble before `KEY:`** — the first non-empty line MUST be `KEY:`.
- **No markdown variants of labels** — write `VERDICT:`, not `**VERDICT:**`,
  `### Verdict`, `Verdict =`, or `` `VERDICT` ``.
- **No swapping verdict tokens** — exactly `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`. Not "ready", "missing", "BLOCKED", "OK".
- **No omitting `VERIFICATION_COMMANDS:`** — include even when
  PREREQUISITES_MISSING; the operator needs commands to verify gaps.
- **No extra sections after `VERIFICATION_COMMANDS:`** — the checklist
  block is the entire response. Put deeper explanation in `references/`.
- **No status marker drift** — use only `[✓]`, `[✗]`, `[OPTIONAL]`,
  `[INPUT NEEDED]`. Do not invent `[?]`, `[!]`, `[WARN]`, or emoji.

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

KMS key provisioning has **dependency and ordering constraints** that make
the procedure non-trivial. Applying configurations in the wrong order causes
locked-out keys, un-decryptable data, or compliance violations:

1. **Key spec + key usage FIRST** — the `KeySpec` and `KeyUsage` determine
   what crypto operations the key supports. A `SYMMETRIC_DEFAULT` key cannot
   sign; an `RSA_4096` `SIGN_VERIFY` key cannot encrypt. Changing spec after
   creation requires a new key and re-encrypting all data.
2. **Key policy separates administrators from users** — the ONLY way to
   grant CMK access (IAM alone is not enough). Conflating admin and user
   produces lockouts (users disable the key) or over-permission (admins
   decrypt production data).
3. **Root account break-glass** — every CMK key policy MUST include account
   root with `kms:*`. Without this, an accidental policy lockout is
   unrecoverable — AWS support cannot restore access.
4. **Aliases after key creation** — human-readable names (`alias/<name>`)
   that decouple the application reference from the underlying key material
   (useful for rotation cutover).
5. **Automatic rotation** — symmetric CMKs support annual rotation (key
   material only, ARN/ID unchanged). Asymmetric, HMAC, and multi-Region
   primaries do NOT support auto-rotation.
6. **Multi-Region keys** — primary + replicas share key material but have
   independent key policies. Create primary first, then replicate. Cannot
   auto-rotate.
7. **Deletion window** — 7-30 day mandatory waiting period before irreversible
   deletion. Set to 30 days for production to allow recovery from accidents.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **AWS account root access or break-glass** | Every CMK policy MUST include root. | `aws sts get-caller-identity` |
| **Key administrator principal** | IAM role/user that can administer the key. | `aws iam get-role --role-name <admin-role>` |
| **Key user principals** | Application roles needing Encrypt/Decrypt/GenerateDataKey. | `aws iam get-role --role-name <app-role>` |
| **CloudHSM cluster** (if custom key store) | Must be ACTIVE with >= 2 HSMs across AZs. | `aws cloudhsmv2 describe-clusters` |
| **Cross-account caller IAM** (if cross-account) | Caller IAM must ALSO grant KMS actions. | `aws iam get-role` in caller account |
| **Alias name uniqueness** | Unique within account/Region. `alias/aws/*` reserved. | `aws kms list-aliases` |
| **IAM permissions** | Caller needs `kms:CreateKey`, `iam:PutRolePolicy`, `kms:CreateAlias`. | `aws sts get-caller-identity` |

## Deployment procedure (apply in order)

### Step 1: Key spec + key usage selection

**Symmetric (the common case):**

| KeySpec | KeyUsage | What it does |
|---|---|---|
| `SYMMETRIC_DEFAULT` | `ENCRYPT_DECRYPT` | AES-256-GCM. Default for 95% of workloads (EBS, S3, RDS, Lambda, Secrets Manager). |

**Asymmetric / HMAC:**

| KeySpec | KeyUsage | What it does |
|---|---|---|
| `RSA_2048` / `RSA_3072` / `RSA_4096` | `ENCRYPT_DECRYPT` | RSA encryption (public key downloadable) |
| `RSA_2048` / `RSA_3072` / `RSA_4096` | `SIGN_VERIFY` | RSA signing (code/document signing) |
| `ECC_NIST_P256` / `P384` / `P521` | `SIGN_VERIFY` | ECDSA signing (lower latency) |
| `ECC_NIST_P256` / `P384` | `KEY_AGREEMENT` | ECDH key agreement (mTLS) |
| `HMAC_256` | `GENERATE_VERIFY_MAC` | HMAC-SHA-256 (JWT, API tokens) |

**Choose `SYMMETRIC_DEFAULT` unless you have a specific reason not to.**
It is the only spec supporting automatic rotation, AWS service integration,
and the cheapest.

### Step 2: Key policy (separate administrators from users)

The key policy is the ONLY way to grant CMK access — IAM cannot override a
key policy denial. A production key policy contains four statements:

1. **Break-glass (root)** — `kms:*` on account root. Mandatory recovery path.
2. **Key administrators** — lifecycle actions only (`Create*`, `Put*`,
   `Disable*`, `ScheduleKeyDeletion`). NO Encrypt/Decrypt.
3. **Key users** — `Encrypt`, `Decrypt`, `ReEncrypt*`, `GenerateDataKey*`,
   `DescribeKey`.
4. **Grant creation** — allows AWS service integrations to create grants
   when `kms:GrantIsForAWSResource=true`.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Enable IAM User Permissions (break-glass)",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::123456789012:root" },
      "Action": "kms:*", "Resource": "*"
    },
    {
      "Sid": "Allow access for Key Administrators",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::123456789012:role/kms-admin" },
      "Action": ["kms:Create*","kms:Describe*","kms:Enable*","kms:List*",
        "kms:Put*","kms:Update*","kms:Revoke*","kms:Disable*","kms:Get*",
        "kms:Delete*","kms:ScheduleKeyDeletion","kms:CancelKeyDeletion",
        "kms:RotateKeyOnDemand"],
      "Resource": "*"
    },
    {
      "Sid": "Allow use of the key",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::123456789012:role/payments-svc" },
      "Action": ["kms:Encrypt","kms:Decrypt","kms:ReEncrypt*",
        "kms:GenerateDataKey*","kms:DescribeKey"],
      "Resource": "*"
    },
    {
      "Sid": "Allow attachment of persistent resources",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::123456789012:role/payments-svc" },
      "Action": ["kms:CreateGrant","kms:ListGrants","kms:RevokeGrant"],
      "Resource": "*",
      "Condition": { "Bool": { "kms:GrantIsForAWSResource": "true" } }
    }
  ]
}
```

**NEVER grant `kms:*` to anyone but root.**

### Step 3: Key administrators vs. key users (separation principle)

| Capability | Key administrators | Key users |
|---|---|---|
| `kms:Create*`, `kms:Put*`, `kms:Update*` | YES | NO |
| `kms:Enable*`, `kms:Disable*` | YES | NO |
| `kms:ScheduleKeyDeletion`, `kms:CancelKeyDeletion` | YES | NO |
| `kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey*` | NO | YES |
| `kms:Describe*`, `kms:List*` | YES | YES (read-only) |
| `kms:CreateGrant` | NO | YES (with condition) |

### Step 4: Grants vs. key policy

- **Key policy** — persistent JSON on the key. Use for stable, long-term
  access (app roles, break-glass root, key admin role).
- **Grants** — temporary, programmatic permissions with constraints. Use
  for AWS service integrations (Lambda, EBS), temporary access (migration),
  tighter scoping (Encrypt only on specific encryption context).

Grants are subject to the key policy and eventually consistent (~5s
propagation). Prefer key policy for human/long-term roles; grants for
service integrations and temporary access.

```bash
aws kms create-grant \
  --key-id alias/payments-cmk \
  --grantee-principal arn:aws:iam::123456789012:role/migration-tool \
  --operations Decrypt \
  --constraints '{"EncryptionContextSubset": {"department": "finance"}}' \
  --retiring-principal arn:aws:iam::123456789012:role/kms-admin
```

### Step 5: Aliases

```bash
aws kms create-alias --alias-name alias/payments-cmk --target-key-id <key-id>
```

- Prefix `alias/` mandatory. `alias/aws/*` reserved for AWS-managed keys.
- Can be updated to point at a different key (rotation cutover).
- Name after the workload (`alias/payments-cmk`), not generic (`alias/my-key`).

### Step 6: Automatic rotation

```bash
aws kms enable-key-rotation --key-id alias/payments-cmk
```

- **Symmetric CMKs**: annual auto-rotation. ARN, ID, policy unchanged.
  Existing ciphertext remains decryptable.
- **Asymmetric / HMAC**: do NOT support auto-rotation. Manual rotation
  required (create new key, update alias, re-encrypt).
- **Multi-Region primaries**: cannot auto-rotate (would desync replicas).
- **Custom key store (CloudHSM)**: supports auto-rotation since 2023.
- **On-demand rotation (2024-2025)**: `kms:RotateKeyOnDemand` triggers
  immediate rotation for eligible symmetric keys.

### Step 7: Multi-Region keys (primary + replicas)

```bash
# Primary (multi-Region)
aws kms create-key --description "Payments CMK (primary)" \
  --origin AWS_KMS --multi-region --policy file://policy.json

# Replica in us-west-2
aws kms replicate-key \
  --key-id arn:aws:kms:us-east-1:123456789012:key/<primary-key-id> \
  --replica-region us-west-2 --policy file://replica-policy.json
```

Each replica shares key material with the primary but has an INDEPENDENT
key policy. Multi-Region keys CANNOT auto-rotate. Use for cross-Region DR,
global DynamoDB table encryption, cross-Region EBS snapshot restore.

### Step 8: Custom key store (CloudHSM)

For FIPS 140-2 Level 3 compliance or regulatory key custody:

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
aws kms create-key --custom-key-store-id cks-xxx \
  --description "Payments CMK (CloudHSM)" --policy file://policy.json
```

Rules:
- `kmsuser` CU must be logged out before KMS connects.
- Cluster must have >= 2 active HSMs across different AZs.
- Supports `SYMMETRIC_DEFAULT`, `RSA_*`, `ECC_*`, `HMAC_256`.
- A disconnected key store blocks all Encrypt/Decrypt on its keys.

### Step 9: Deletion window

```bash
aws kms schedule-key-deletion --key-id alias/payments-cmk --pending-window-in-days 30
```

- Window: 7-30 days. Default is 30 days. For production, ALWAYS set 30 days.
- Deletion is IRREVERSIBLE — once the window expires, the key material is
  destroyed and all ciphertext encrypted under the key becomes permanently
  unrecoverable.
- The key is in `PendingDeletion` state during the window. It can be
  cancelled with `CancelKeyDeletion`.
- During `PendingDeletion`, the key CANNOT be used for Encrypt or
  GenerateDataKey, but CAN be used for Decrypt (so existing data can be
  migrated to a new key).

### Step 10: Tagging + verification

```bash
aws kms tag-resource --key-id <key-id> \
  --tags '[{"TagKey":"Environment","TagValue":"production"}]'
aws kms describe-key --key-id alias/payments-cmk
aws kms get-key-rotation-status --key-id alias/payments-cmk
aws kms get-key-policy --key-id <key-id> --policy-name default
```

## Envelope encryption and cross-account access

**Envelope encryption:** KMS has a 4 KB payload limit. Use
`GenerateDataKey` to get a plaintext data key + encrypted data key, encrypt
payloads client-side (AWS Encryption SDK), store ciphertext + encrypted key.
Decrypt by calling `Decrypt` on the encrypted data key.

```bash
aws kms generate-data-key --key-id alias/payments-cmk \
  --key-spec AES_256 \
  --encryption-context '{"department":"finance","app":"payments"}'

aws kms decrypt --ciphertext-blob fileb://encrypted-data-key.bin \
  --encryption-context '{"department":"finance","app":"payments"}'
```

The encryption context is authenticated AAD — MUST be identical on Encrypt
and Decrypt. Full reference in `references/key-policy-and-multiregion-guide.md`.

**Cross-account access:** KMS is a "both-must-allow" service. Account A's
key policy must grant account B, AND account B's IAM must grant the KMS
actions. A missing key policy statement fails silently with
`AccessDeniedException`. Full reference in
`references/key-policy-and-multiregion-guide.md`.

## Edge-case handling

Edge-case quick list moved verbatim to
`references/key-policy-and-multiregion-guide.md` (load on demand).

## Workload matrix

| Workload | KeySpec | Rotation | Multi-Region | Origin | Notes |
|---|---|---|---|---|---|
| EBS / S3 / RDS / Lambda env vars | `SYMMETRIC_DEFAULT` | Annual | Optional | AWS_KMS | Default for AWS service integration |
| DynamoDB / Aurora / SQS / SNS | `SYMMETRIC_DEFAULT` | Annual | Optional | AWS_KMS | Use CMK for full control |
| Secrets Manager | `SYMMETRIC_DEFAULT` | Annual | No | AWS_KMS | One CMK per secret-class |
| Code signing (Signer) | `RSA_4096` SIGN_VERIFY | Manual | Optional | AWS_KMS | Cannot auto-rotate |
| JWT / API tokens | `HMAC_256` | Manual | Optional | AWS_KMS | Cannot auto-rotate |
| Cross-Region DR | `SYMMETRIC_DEFAULT` | Manual | YES | AWS_KMS | Replica per Region |
| FIPS / regulatory | `SYMMETRIC_DEFAULT` | Annual | No | CloudHSM | Custom key store |
| Document signing | `ECC_NIST_P384` SIGN_VERIFY | Manual | Optional | AWS_KMS | Lower latency than RSA |

## Recent AWS features (2024-2026)

2024-2026 feature details moved verbatim to
`references/advanced-patterns.md` (load on demand).

## NEVER (top 5 — full list of 13 anti-patterns in references)

- NEVER create a CMK without the account root as break-glass
  (`{"AWS": "arn:aws:iam::<account>:root"}` with `kms:*`). Without root,
  an accidental lockout is unrecoverable — AWS support cannot help.
- NEVER grant `kms:*` to any non-root principal. Use scoped statements for
  users (Encrypt/Decrypt/GenerateDataKey) vs administrators (Create*/Disable*).
- NEVER combine key administrator and key user into one role. Separation of
  duties: admins manage lifecycle, users access data — never both.
- NEVER skip automatic rotation on a `SYMMETRIC_DEFAULT` CMK. Annual rotation
  is free, invisible to callers, and limits blast radius of compromise.
- NEVER delete a CMK without confirming no ciphertext is encrypted under it.
  Audit CloudTrail for recent Encrypt/GenerateDataKey usage.

## Expert heuristic — choosing key spec, administrators, and users

- **Key spec** — default to `SYMMETRIC_DEFAULT`. Choose asymmetric only for
  public-key encryption, digital signatures verifiable outside AWS, or HMAC.
- **Administrators** — one `kms-admin` role per security team. Lifecycle
  actions only, NO `kms:Decrypt`.
- **Users** — one role per application. Never grant to broad groups like
  "Developers" — that lets engineers read production ciphertext.
- **Break-glass** — root always in the policy with `kms:*`. Not a violation
  of least privilege — it is the recovery path.
- **Rotation** — symmetric: on; asymmetric/HMAC: document manual procedure.
- **Multi-Region** — only when needed (cross-Region DR, global tables).
  Single-Region is the right default.
- **Encryption context** — always include identifying fields like
  `{"app":"payments","env":"prod"}`. Scopes grants, provides audit trail.

## Pre-flight safety checks (run before any provisioning CLI)

Pre-flight command listing moved verbatim to
`references/deployment-cli-commands.md` (load on demand).

## Output format — MANDATORY literal labels

When invoked with a key provisioning request, your ENTIRE response MUST
be the checklist block below. The labels are **case-sensitive all-caps
keywords** — write them EXACTLY as shown. Do NOT write a preamble. Start
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
- `[✓]` — applied and verified.
- `[✗]` — NOT applied or misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required for the workload type.
- `[INPUT NEEDED]` — prerequisite value missing; operator must provide.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is missing
(administrator role ARN, application role ARN, CloudHSM cluster), the
verdict is `PREREQUISITES_MISSING` with each gap listed.

## References (load on demand)

- [`references/deployment-cli-commands.md`](references/deployment-cli-commands.md) — full copy-pasteable CLI sequence for all 10 provisioning steps, Terraform/CloudFormation equivalents, pre-flight safety checks.
- [`references/key-policy-and-multiregion-guide.md`](references/key-policy-and-multiregion-guide.md) — key policy structure, grants, multi-Region, CloudHSM, envelope encryption, cross-account, edge-case handling.
- [`references/advanced-patterns.md`](references/advanced-patterns.md) — recent AWS features 2024-2026 (on-demand rotation, HMAC GA, ECDH, XKS, VPC endpoint policies).

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

- `references/deployment-cli-commands.md` — full copy-pasteable CLI command
  sequence for all 10 provisioning steps, including Terraform equivalents.

- `references/key-policy-and-multiregion-guide.md` — deep reference on key
  policy structure, multi-Region internals, CloudHSM lifecycle, envelope
  encryption, cross-account access, full NEVER list, and edge-case handling.
