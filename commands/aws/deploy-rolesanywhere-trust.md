---
description: Provision IAM Roles Anywhere trust infrastructure with production-grade defaults (trust anchor binding external CA to AWS IAM, profile mapping external certificates to IAM roles, session policy, credential helper for certificate-based authentication, revocation CRL, CloudTrail audit via AssumeRoot events). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create roles anywhere trust anchor"
  - "deploy roles anywhere"
  - "iam roles anywhere profile"
  - "credential helper"
  - "certificate based authentication aws"
  - "external ca aws"
  - "exchange cert for sts"
  - "roles anywhere session policy"
  - "roles anywhere revocation"
  - "roles anywhere crl"
  - "aws_signing_helper"
  - "roles anywhere"
routes_to: rolesanywhere-trust-deployer
---

# /aws:deploy-rolesanywhere-trust

Activate the `rolesanywhere-trust-deployer` skill and provision IAM
Roles Anywhere trust infrastructure with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Trust anchor (bind external CA to AWS IAM — CERTIFICATE_BUNDLE or
   AWS_ACM_PCA source)
2. Profile (map external cert to IAM role — roleArns, session policy,
   duration)
3. IAM role (trust policy for rolesanywhere.amazonaws.com)
4. Session policy (restrict permissions per profile)
5. Credential helper (AWS signing helper credential-process)
6. Role assumption workflow (exchange cert for STS credentials)
7. Revocation configuration (CRL creation and update)
8. CloudTrail audit (AssumeRoot events)
9. Recent features (session policies, role-passthrough, cross-account)

## When to use

- You need to create a Roles Anywhere trust anchor.
- You are mapping external certificates to IAM roles via a profile.
- You need to configure the credential helper (AWS signing helper).
- You are setting up certificate-based authentication to AWS APIs.
- You need to integrate an external PKI (self-managed CA or ACM PCA).
- You need to configure revocation (CRL).
- You need to audit Roles Anywhere sessions via CloudTrail.

## When NOT to use

- **Standard IAM role assumption via STS** — no certificate involved.
- **AWS IAM Identity Center (SSO)** — different authentication model.
- **AWS Organizations SCC** — service control policies, not auth.
- **EC2 instance profiles** — for EC2 instances, not external workloads.

## How to invoke

### Slash command

```
/aws:deploy-rolesanywhere-trust
```

Then provide: CA certificate (PEM), trust anchor name, profile name,
IAM role ARN, session policy, session duration, CRL (if revocation
needed), region, tags.

### Natural language

Any of these routes to the same skill:

- "create a roles anywhere trust anchor"
- "map my external certificate to an IAM role"
- "configure the aws signing helper"
- "set up certificate-based authentication to AWS"
- "integrate my external PKI with AWS IAM"

### CLI routing

```bash
node cli/bin/cli.js route "create a roles anywhere trust anchor"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Roles
Anywhere trust infrastructure. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-rolesanywhere-trust

     Create a Roles Anywhere trust anchor binding my external CA
     (ca-cert.pem). Map it to IAM role RolesAnywhereCIRunner via
     profile ci-runner-profile. Session policy restricting to
     s3:GetObject on my-ci-artifacts. Configure CRL revocation.

Skill:
  ROLES_ANYWHERE: ta-aaa111222 → p-bbb222333 → RolesAnywhereCIRunner
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Trust anchor: CERTIFICATE_BUNDLE (ca-cert.pem)
    [✓] Profile: ci-runner-profile (duration 3600s)
    [✓] IAM role: trust rolesanywhere.amazonaws.com
    [✓] Session policy: restrict s3:GetObject
    [✓] Revocation: CRL configured
  VERIFICATION_COMMANDS:
    aws rolesanywhere list-trust-anchors --region us-east-1
    aws iam get-role --role-name RolesAnywhereCIRunner
```

## References

- Skill definition: `skills/rolesanywhere-trust-deployer/SKILL.md`
- Trust anchor and profile guide: `skills/rolesanywhere-trust-deployer/references/trust-anchor-and-profile.md`
- Credential helper and revocation guide: `skills/rolesanywhere-trust-deployer/references/credential-helper-and-revocation.md`
- Eval suite: `skills/rolesanywhere-trust-deployer/evals/evals.json`
