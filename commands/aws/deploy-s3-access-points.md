---
description: Provision S3 Access Points (Internet or VPC origin) with prefix-scoped policies, the through-AP-only bucket-policy Deny, per-AP Block Public Access, optional Object Lambda / MRAP / cross-account delegation. Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create s3 access point"
  - "provision s3 access point"
  - "s3 access point setup"
  - "vpc-only bucket access"
  - "vpc origin access point"
  - "object lambda access point"
  - "transform s3 objects on the fly"
  - "multi-region access point"
  - "mrap configuration"
  - "s3 access point alias"
  - "access point policy"
  - "cross-account access point"
  - "delegate access point creation"
  - "s3 on outposts access point"
  - "per-access-point block public access"
  - "block global hostname bypass"
routes_to: s3-access-points-deployer
---

# /aws:deploy-s3-access-points

Activate the `s3-access-points-deployer` skill and provision S3 Access
Points and their dependent primitives with production-grade defaults.

## What it does

The skill walks a 9-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Confirm bucket baseline (BPA, SSE, versioning)
2. Choose network origin (Internet vs VPC)
3. (VPC only) Provision / confirm VPC gateway endpoint + private DNS
4. Create the access point
5. Attach access point policy (scope to prefix + principal)
6. Enforce "through-AP-only" via bucket-policy Deny on `s3:DataAccessPointArn`
7. Per-AP Block Public Access (VPC-origin)
8. Optional: Object Lambda / MRAP / cross-account delegation / alias / Outposts
9. Verify every configuration item against actual state

## When to use

- You need a per-application or per-team entry point to a shared bucket.
- You must enforce VPC-only access to a bucket (with the global-hostname bypass blocked).
- You want Object Lambda to transform objects on retrieval (PII redaction, format conversion).
- You need a Multi-Region Access Point for active-active or failover data access.
- You are delegating access-point creation to a partner account and need containment.
- You want to generate CloudFormation / Terraform for any of the above.

## How to invoke

### Slash command

```
/aws:deploy-s3-access-points
```

Then provide: bucket name, account ID, region, AP name, network origin,
and (if VPC) the VPC ID. Add any optional features (Object Lambda, MRAP,
cross-account, alias, Outposts).

### Natural language

Any of these routes to the same skill:

- "create an S3 access point"
- "make this bucket VPC-only"
- "set up Object Lambda to redact PII"
- "build a multi-region access point"
- "delegate access point creation to my partner account"
- "block the global hostname bypass"

### CLI routing

```bash
node cli/bin/cli.js route "create s3 access point"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or harden
an S3 access point. The output checklist feeds into verification
pipelines and audit skills (s3-public-access-auditor for post-deploy
audit, s3-access-troubleshooter for diagnosing access failures).

## Example

```
You: /aws:deploy-s3-access-points

     Provision a VPC-only access point for prod-shared-data in
     us-east-1, account 123456789012. AP name team-a-vpc-ap, VPC
     vpc-0abc123def456. Team A's role TeamARole should read/write
     the team-a/ prefix only. Include the bucket-policy Deny that
     blocks the global hostname and enable per-AP BPA.

Skill:
  ACCESS_POINT: team-a-vpc-ap
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Bucket baseline verified (BPA, SSE-KMS, versioning)
    [✓] Network origin: VPC (vpc-0abc123def456)
    [✓] VPC endpoint + private DNS configured
    [✓] Access point created: team-a-vpc-ap
    [✓] Access point policy: principal TeamARole, prefix team-a/
    [✓] Through-AP-only bucket-policy Deny (s3:DataAccessPointArn)
    [✓] Per-AP Block Public Access: all 4 settings True
    [OPTIONAL] Object Lambda / MRAP / cross-account: none
  VERIFICATION_COMMANDS:
    aws s3control get-access-point --account-id 123456789012 --name team-a-vpc-ap
    aws s3control get-access-point-policy --account-id 123456789012 --name team-a-vpc-ap
    aws s3control get-access-point-public-access-block --account-id 123456789012 --name team-a-vpc-ap
    aws s3api get-bucket-policy --bucket prod-shared-data
    ...
```

## References

- Skill definition: `skills/s3-access-points-deployer/SKILL.md`
- Policy templates: `skills/s3-access-points-deployer/references/access-point-policy-examples.md`
- Provisioning CLI commands: `skills/s3-access-points-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/s3-access-points-deployer/evals/evals.json`
