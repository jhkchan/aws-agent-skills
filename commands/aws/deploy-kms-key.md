---
description: Provision an AWS KMS customer-managed key (CMK) with production-grade configuration (correct key spec — symmetric AES-256, asymmetric RSA/ECDSA, or HMAC; key policy separating key administrators from key users; root account break-glass; automatic rotation where supported; aliases; deletion window 7-30 days; multi-Region primary and replicas; CloudHSM custom key store; cross-account access). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create kms key"
  - "provision kms key"
  - "customer managed key"
  - "cmk provisioning"
  - "kms key policy"
  - "kms key administrators"
  - "kms key users"
  - "kms automatic rotation"
  - "multi-region kms key"
  - "kms replica"
  - "cloudhsm custom key store"
  - "kms grants"
  - "kms deletion window"
  - "kms alias"
  - "cross-account kms"
  - "envelope encryption"
  - "kms symmetric"
  - "kms asymmetric"
  - "kms hmac"
  - "kms signing key"
routes_to: kms-key-deployer
---

# /aws:deploy-kms-key

Activate the `kms-key-deployer` skill and provision an AWS KMS
customer-managed key with production-grade configuration.

## What it does

The skill walks a 10-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Key spec + key usage selection (symmetric / asymmetric / HMAC)
2. Key policy (separated administrators vs. users)
3. Key administrators vs. key users (separation principle)
4. Grants vs. key policy (when to use which)
5. Aliases (human-readable name)
6. Automatic rotation (symmetric only)
7. Multi-Region keys (primary + replicas)
8. CloudHSM custom key store (when needed)
9. Deletion window (7-30 days, irreversible)
10. Tagging + verification commands

## When to use

- You need to create a new customer-managed KMS key (CMK) with
  production defaults.
- You are provisioning a multi-Region key for disaster recovery.
- You need a CloudHSM-backed key for compliance (FIPS 140-2 L3).
- You want to validate a key policy for least-privilege / separation
  of duties.
- You are setting up cross-account KMS access (both-must-allow).
- You want to check for provisioning blockers (missing root
  break-glass, unsupported rotation spec, missing replica policy).

## How to invoke

### Slash command

```
/aws:deploy-kms-key
```

Then provide: key alias, workload (what the key protects), key spec
(symmetric/asymmetric/HMAC), key usage, administrator role ARN,
application role ARN, rotation preference, deletion window, and any
optional features (multi-Region, CloudHSM, grants).

### Natural language

Any of these routes to the same skill:

- "create a KMS customer-managed key"
- "provision a CMK for EBS / S3 / Secrets Manager"
- "set up a multi-Region KMS key for DR"
- "configure a CloudHSM custom key store"
- "create an HMAC key for JWT signing"
- "validate a KMS key policy"

### CLI routing

```bash
node cli/bin/cli.js route "deploy kms key"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The output checklist feeds into verification pipelines and audit
skills (e.g., a KMS key policy auditor for post-provisioning checks,
and the `lambda-function-deployer` skill which references CMKs for
env-var encryption).

## Example

```
You: /aws:deploy-kms-key

     Provision a customer-managed KMS key in us-east-1. Alias
     alias/payments-cmk. Encrypt EBS, S3, Secrets Manager for the
     payments service. Admins: kms-admin role. Users: payments-svc
     role. Enable annual rotation. 30-day deletion window. Tags:
     Environment=production, Application=payments. Account:
     123456789012.

Skill:
  KEY: alias/payments-cmk
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Key spec — SYMMETRIC_DEFAULT (AES-256-GCM)
    [✓]      Key usage — ENCRYPT_DECRYPT
    [✓]      Key administrators — arn:aws:iam::123456789012:role/kms-admin (lifecycle only)
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

## References

- Skill definition: `skills/kms-key-deployer/SKILL.md`
- Deployment CLI commands: `skills/kms-key-deployer/references/deployment-cli-commands.md`
- Key policy, multi-Region, CloudHSM guide: `skills/kms-key-deployer/references/key-policy-and-multiregion-guide.md`
- Eval suite: `skills/kms-key-deployer/evals/evals.json`
