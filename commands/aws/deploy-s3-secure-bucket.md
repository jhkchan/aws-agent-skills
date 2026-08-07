---
description: Provision an S3 bucket with production-grade security defaults (BPA, SSE-KMS, BucketOwnerEnforced, versioning, lifecycle, access logging). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create secure s3 bucket"
  - "provision s3 bucket"
  - "deploy s3 bucket"
  - "secure bucket setup"
  - "s3 security baseline"
  - "s3 production bucket"
  - "enable bpa on bucket"
  - "s3 bucket encryption"
  - "sse-kms bucket"
  - "bucket owner enforced"
  - "s3 versioning setup"
  - "s3 lifecycle policy"
  - "s3 replication setup"
  - "crr configuration"
  - "s3 access logging setup"
  - "harden s3 bucket"
routes_to: s3-secure-bucket-deployer
---

# /aws:deploy-s3-secure-bucket

Activate the `s3-secure-bucket-deployer` skill and provision an S3 bucket
with production-grade security defaults.

## What it does

The skill walks a 10-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Create bucket + Block Public Access (account + bucket, all 4 settings)
2. Default encryption (SSE-KMS with Bucket Keys or SSE-S3)
3. Object Ownership = BucketOwnerEnforced (disable ACLs)
4. Versioning (optional MFA Delete for compliance)
5. Bucket policy (HTTPS-only + SSE-KMS upload enforcement)
6. Access logging + CloudTrail data events
7. Lifecycle policy (cost optimization)
8. Replication (CRR/SRR, optional)
9. Tags
10. Verification commands

## When to use

- You need to create a new S3 bucket with security defaults.
- You are hardening an existing bucket to production baseline.
- You want to validate that a bucket meets the security baseline.
- You need copy-pasteable provisioning commands or Terraform templates.

## How to invoke

### Slash command

```
/aws:deploy-s3-secure-bucket
```

Then provide: bucket name, region, workload type, encryption preference,
and any optional features (lifecycle, replication, logging).

### Natural language

Any of these routes to the same skill:

- "create a secure S3 bucket"
- "provision a production S3 bucket"
- "set up an S3 bucket with SSE-KMS"
- "harden my S3 bucket"
- "S3 security baseline"

### CLI routing

```bash
node cli/bin/cli.js route "create a secure s3 bucket"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline. The
orchestrator routes to it when the user wants to create or harden S3
storage. The output checklist feeds into verification pipelines and
audit skills (s3-public-access-auditor for post-deployment audit).

## Example

```
You: /aws:deploy-s3-secure-bucket

     Create a production bucket "app-data-prod" in us-east-1 for
     general-purpose app storage. Use SSE-KMS with alias/app-s3-key.
     Enable access logging to "s3-access-logs". Lifecycle:
     STANDARD_IA@30d → GLACIER@90d. Versioning on. Account: 123456789012.

Skill:
  BUCKET: app-data-prod
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Block Public Access — bucket level (all 4 settings)
    [✓]      Block Public Access — account level (defense-in-depth)
    [✓]      Default encryption — SSE-KMS (alias/app-s3-key, BucketKeyEnabled)
    [✓]      Object Ownership — BucketOwnerEnforced (ACLs disabled)
    [✓]      Versioning — Enabled
    [OPTIONAL] MFA Delete — Not enabled
    [✓]      Bucket policy — HTTPS-only + SSE-KMS enforcement
    [✓]      Access logging — Target: s3-access-logs
    [✓]      Lifecycle — STANDARD_IA@30d → GLACIER@90d
    [OPTIONAL] Replication — Not configured
    [✓]      Tags — Environment=production
  VERIFICATION_COMMANDS:
    aws s3api get-public-access-block --bucket app-data-prod
    aws s3api get-bucket-encryption --bucket app-data-prod
    aws s3api get-bucket-ownership-controls --bucket app-data-prod
    ...
```

## References

- Skill definition: `skills/s3-secure-bucket-deployer/SKILL.md`
- Provisioning CLI commands: `skills/s3-secure-bucket-deployer/references/provisioning-cli-commands.md`
- Encryption and lifecycle guide: `skills/s3-secure-bucket-deployer/references/encryption-and-lifecycle-guide.md`
- Eval suite: `skills/s3-secure-bucket-deployer/evals/evals.json`
