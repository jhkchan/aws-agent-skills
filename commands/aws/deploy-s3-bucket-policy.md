---
description: Provision an S3 bucket policy with production-grade defaults (HTTPS-only aws:SecureTransport Deny with Bool, cross-account with ExternalId, VPC-endpoint-only aws:SourceVpce, CloudFront OAC, service access, ACLs disabled via BucketOwnerEnforced, Block Public Access, Access Points delegation, MRAP policy). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "s3 bucket policy"
  - "attach bucket policy"
  - "put bucket policy"
  - "https only s3"
  - "aws secure transport s3"
  - "cross account s3 access"
  - "vpc endpoint only s3"
  - "aws source vpce s3"
  - "cloudfront oac s3"
  - "origin access control"
  - "s3 access points delegation"
  - "mrap policy"
  - "multi-region access point policy"
  - "disable s3 acls"
  - "bucket owner enforced"
  - "s3 block public access"
routes_to: s3-bucket-policy-deployer
---

# /aws:deploy-s3-bucket-policy

Activate the `s3-bucket-policy-deployer` skill and provision an S3
bucket policy with production-grade security defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Policy structure (Principal, Action, Resource, Condition)
2. HTTPS-only enforcement (aws:SecureTransport Deny with Bool)
3. Cross-account access (with ExternalId)
4. VPC-endpoint-only restriction (aws:SourceVpce)
5. CloudFront Origin Access Control (OAC)
6. AWS service access (s3:x-amz-acl)
7. Policy vs ACL (BucketOwnerEnforced — policy preferred)
8. 20 KB policy size limit check
9. Access Points policy delegation
10. MRAP policy
11. Recent features

## When to use

- You need to attach or replace a bucket policy.
- You want to enforce HTTPS-only access (aws:SecureTransport).
- You are granting cross-account access with conditions.
- You want to restrict to a VPC endpoint (aws:SourceVpce).
- You are configuring CloudFront OAC for a CDN origin.
- You want to delegate per-team policies via Access Points.
- You want to disable ACLs (BucketOwnerEnforced).

## When NOT to use

- **Bucket-level hardening without a policy** — use
  `s3-secure-bucket-deployer`.
- **Access point creation** — use `s3-access-points-deployer`.
- **S3 ACLs** — legacy; policies are preferred.
- **Auditing existing policies** — use `s3-public-access-auditor`.

## How to invoke

### Slash command

```
/aws:deploy-s3-bucket-policy
```

Then provide: bucket name, access pattern (HTTPS-only /
cross-account / VPC-endpoint / CloudFront OAC), condition values,
ACL/BPA settings.

### Natural language

Any of these routes to the same skill:

- "attach an https-only bucket policy"
- "grant cross-account access with external id"
- "restrict bucket to vpc endpoint only"
- "set up cloudfront oac for my bucket"
- "disable s3 acls with bucket owner enforced"

### CLI routing

```bash
node cli/bin/cli.js route "attach s3 bucket policy"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps
pipeline. The orchestrator routes to it when the user wants to
attach or replace a bucket policy. The output checklist feeds into
verification pipelines and audit skills
(s3-public-access-auditor for post-deploy audit,
s3-access-troubleshooter for diagnosing access failures).

## Example

```
You: /aws:deploy-s3-bucket-policy

     Attach an HTTPS-only policy to prod-shared-data with
     cross-account access for partner 998877665544 (ExternalId
     partner-ext-abc123) and CloudFront OAC for distribution
     E123ABCDEF456. Account 123456789012.

Skill:
  BUCKET_POLICY: prod-shared-data (3 statements, 1.8 KB)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] HTTPS-only (aws:SecureTransport Deny with Bool): present
    [✓] Cross-account: 998877665544 (PartnerRole, ext-id)
    [✓] CloudFront OAC: distribution E123ABCDEF456
    [✓] ACLs disabled: BucketOwnerEnforced
    [✓] Block Public Access: all 4 settings True
  VERIFICATION_COMMANDS:
    aws s3api get-bucket-policy --bucket prod-shared-data
    aws s3api get-public-access-block --bucket prod-shared-data
```

## References

- Skill definition: `skills/s3-bucket-policy-deployer/SKILL.md`
- Policy patterns deep dive: `skills/s3-bucket-policy-deployer/references/policy-patterns.md`
- Provisioning CLI commands: `skills/s3-bucket-policy-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/s3-bucket-policy-deployer/evals/evals.json`
