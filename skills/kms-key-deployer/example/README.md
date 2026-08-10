# End-to-End Example: KMS Customer-Managed Key Provisioning

A walkthrough showing how to use the `kms-key-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a customer-managed KMS key (CMK) for the payments
service. The key protects EBS volumes, S3 objects, and Secrets Manager
secrets. The key requires:

- Symmetric AES-256 (`SYMMETRIC_DEFAULT`), `ENCRYPT_DECRYPT` usage
- Key administrators: the `kms-admin` IAM role (lifecycle only, no crypto)
- Key users: the `payments-svc` IAM role (Encrypt, Decrypt, GenerateDataKey)
- Account root break-glass
- Annual automatic rotation
- Alias `alias/payments-cmk`
- Deletion window 30 days
- Tags Environment=production, Application=payments

Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-kms-key
```

Then paste the key requirements.

### Option B: Natural language

```
You: "Provision a customer-managed KMS key in us-east-1. Alias
      alias/payments-cmk. Encrypt EBS, S3, Secrets Manager for the
      payments service. Admins: kms-admin role. Users: payments-svc
      role. Enable annual rotation. 30-day deletion window. Tags:
      Environment=production, Application=payments. Account:
      123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy kms key"
```

Output:

```
[Phase: Deploy | Skills routed: kms-key-deployer]

Primary route: kms-key-deployer (score: 18)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
KEY: alias/payments-cmk
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Key spec — SYMMETRIC_DEFAULT (AES-256-GCM)
  [✓]      Key usage — ENCRYPT_DECRYPT
  [✓]      Origin — AWS_KMS
  [✓]      Key administrators — arn:aws:iam::123456789012:role/kms-admin (lifecycle only, no Encrypt/Decrypt)
  [✓]      Key users — arn:aws:iam::123456789012:role/payments-svc (Encrypt, Decrypt, GenerateDataKey)
  [✓]      Root account break-glass — arn:aws:iam::123456789012:root (kms:*)
  [✓]      Automatic rotation — enabled (annual)
  [✓]      Alias — alias/payments-cmk
  [✓]      Deletion window — 30 days
  [✓]      Tags — Environment=production, Application=payments
VERIFICATION_COMMANDS:
  aws kms describe-key --key-id alias/payments-cmk
  aws kms get-key-rotation-status --key-id alias/payments-cmk
  aws kms get-key-policy --key-id alias/payments-cmk --policy-name default
  aws kms list-aliases --key-id alias/payments-cmk
  aws kms list-resource-tags --key-id alias/payments-cmk
```

---

## Step 3 — Provisioning commands

The skill generates the CLI sequence (from
`references/deployment-cli-commands.md`):

```bash
# Step 1: Build the key policy (root break-glass FIRST, then admins, then users)
cat > /tmp/payments-cmk-policy.json <<'EOF'
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
        "kms:Create*", "kms:Describe*", "kms:Enable*", "kms:List*",
        "kms:Put*", "kms:Update*", "kms:Revoke*", "kms:Disable*",
        "kms:Get*", "kms:Delete*", "kms:ScheduleKeyDeletion",
        "kms:CancelKeyDeletion", "kms:RotateKeyOnDemand"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Allow use of the key (Cryptographic operations)",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::123456789012:role/payments-svc" },
      "Action": [
        "kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*",
        "kms:GenerateDataKey*", "kms:DescribeKey"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Allow attachment of persistent resources",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::123456789012:role/payments-svc" },
      "Action": ["kms:CreateGrant", "kms:ListGrants", "kms:RevokeGrant"],
      "Resource": "*",
      "Condition": { "Bool": { "kms:GrantIsForAWSResource": "true" } }
    }
  ]
}
EOF

# Step 2: Create the CMK with policy + tags
KEY_ID=$(aws kms create-key \
  --description "Payments service CMK for data encryption" \
  --policy file:///tmp/payments-cmk-policy.json \
  --tags '[{"TagKey":"Environment","TagValue":"production"},{"TagKey":"Application","TagValue":"payments"}]' \
  --query 'KeyMetadata.KeyId' --output text)

# Step 3: Create the alias
aws kms create-alias \
  --alias-name alias/payments-cmk \
  --target-key-id ${KEY_ID}

# Step 4: Enable annual automatic rotation
aws kms enable-key-rotation --key-id ${KEY_ID}

# Step 5: Caller IAM — add kms:Decrypt etc. to the payments-svc role
aws iam put-role-policy \
  --role-name payments-svc \
  --policy-name payments-svc-kms \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*",
                 "kms:GenerateDataKey*", "kms:DescribeKey"],
      "Resource": "arn:aws:kms:us-east-1:123456789012:key/'${KEY_ID}'"
    }]
  }'
```

---

## Step 4 — Post-provisioning verification

```bash
# Key metadata (state, spec, usage, deletion window)
aws kms describe-key --key-id alias/payments-cmk

# Rotation status (must be Enabled)
aws kms get-key-rotation-status --key-id alias/payments-cmk

# Key policy (verify root break-glass, admins, users statements)
aws kms get-key-policy --key-id alias/payments-cmk --policy-name default

# Aliases pointing to the key
aws kms list-aliases --key-id alias/payments-cmk

# Tags
aws kms list-resource-tags --key-id alias/payments-cmk

# Active grants (should be empty or service-created only)
aws kms list-grants --key-id alias/payments-cmk
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Root break-glass | Often omitted | Always included | Without root fallback, an accidental policy misconfiguration permanently locks everyone out — AWS support cannot recover the CMK. |
| Administrator / user separation | Admins granted `kms:*` | Admins get lifecycle only; users get crypto | Separation of duties: admins cannot read production data, applications cannot disable or delete the key. |
| Automatic rotation | Often skipped | Enabled (annual) | Annual rotation is free, invisible to callers, and limits the blast radius of a key material compromise. |
| Caller IAM (payments-svc) | Not configured | Inline policy granting KMS actions on the key ARN | KMS is both-must-allow: the key policy AND the caller IAM must grant. IAM alone is not enough; key policy alone is not enough. |
| Alias creation | Often forgotten | Explicit step | The alias decouples the application reference from the underlying key ID, enabling rotation cutover. |
| Deletion window | Default (7-30) or unset | Explicit 30 days | A 7-day window leaves too little recovery time. 30 days is the production default. |
| Key spec selection | Generic `SYMMETRIC_DEFAULT` always | Workload-aware | Symmetric for AWS service integration; RSA for signing; HMAC for tokens — choosing the wrong spec breaks integration or loses rotation. |

---

## Related artifacts

- **Skill definition:** `skills/kms-key-deployer/SKILL.md`
- **Deployment CLI commands:** `skills/kms-key-deployer/references/deployment-cli-commands.md`
- **Key policy, multi-Region, CloudHSM guide:** `skills/kms-key-deployer/references/key-policy-and-multiregion-guide.md`
- **Slash command:** `commands/aws/deploy-kms-key.md`
- **Eval suite:** `skills/kms-key-deployer/evals/evals.json`
- **Legacy test cases:** `skills/kms-key-deployer/eval/test-cases.yaml`
