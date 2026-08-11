---
description: Provision an AWS ACM certificate (public, private, or imported) with production-grade defaults (DNS validation, wildcard/SAN domains, CloudFront us-east-1 requirement, automatic renewal, AWS Private CA integration). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "request acm certificate"
  - "create acm certificate"
  - "deploy acm certificate"
  - "acm certificate"
  - "dns validation acm"
  - "route53 cname acm"
  - "acm wildcard certificate"
  - "acm cloudfront certificate"
  - "acm renewal"
  - "import certificate acm"
  - "aws private ca"
  - "acm private certificate"
  - "acm cross-account"
  - "pem certificate import"
  - "tls certificate aws"
routes_to: acm-certificate-deployer
---

# /aws:deploy-acm-certificate

Activate the `acm-certificate-deployer` skill and provision an AWS
Certificate Manager certificate with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Public vs private certificate (boundary call)
2. Domain names (apex, www, wildcard, SAN)
3. DNS validation (Route53 CNAME, cross-account)
4. Email validation (deprecated)
5. Certificate renewal (automatic, managed by ACM)
6. Import third-party certificates (PEM format)
7. CloudFront integration (us-east-1 requirement)
8. Cross-account sharing (service principals)
9. AWS Private CA integration / private certificates
10. Recent features

## When to use

- You need to request a new ACM certificate (public or private).
- You are setting up DNS validation via Route53.
- You need a wildcard or multi-SAN certificate.
- You need to import a third-party certificate (PEM).
- You need to deploy a certificate for CloudFront (us-east-1).
- You need to integrate with AWS Private CA.
- You need to share a private certificate cross-account.

## When NOT to use

- **IAM server certificates** (deprecated) — use ACM instead.
- **Self-signed certificates outside ACM** — not this skill.
- **Auditing existing certificate expiry** — use
  `acm-certificate-expiry-auditor`.

## How to invoke

### Slash command

```
/aws:deploy-acm-certificate
```

Then provide: domain names, validation method (DNS recommended),
region (us-east-1 for CloudFront), Route53 zone ID, certificate type
(public/private/imported), Private CA ARN (if private), PEM file
paths (if imported), CloudFront distribution ID (if applicable).

### Natural language

Any of these routes to the same skill:

- "request a public ACM certificate for example.com"
- "set up DNS validation for my ACM certificate"
- "import a DigiCert certificate into ACM"
- "create a wildcard certificate for CloudFront"
- "request a private certificate via AWS Private CA"

### CLI routing

```bash
node cli/bin/cli.js route "request an acm certificate"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or import
ACM certificates. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-acm-certificate

     Request a public ACM certificate for example.com and
     *.example.com with DNS validation in us-east-1. Attach it to
     CloudFront distribution E1234567890ABC. Route53 zone
     Z2KVMGOMGDOOU2. Account: 123456789012.

Skill:
  ACM_CERTIFICATE: *.example.com
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Certificate type: Public
    [✓] Domain names: example.com, *.example.com
    [✓] Validation method: DNS (recommended)
    [✓] DNS validation CNAME: Route53 zone Z2KVMGOMGDOOU2
    [✓] Region: us-east-1 (required for CloudFront)
    [✓] CloudFront integration: E1234567890ABC
    [✓] Renewal: Automatic (ACM-managed)
  VERIFICATION_COMMANDS:
    aws acm describe-certificate --certificate-arn <arn> --region us-east-1
    aws cloudfront get-distribution-config --id E1234567890ABC
```

## References

- Skill definition: `skills/acm-certificate-deployer/SKILL.md`
- Validation and renewal guide: `skills/acm-certificate-deployer/references/validation-and-renewal.md`
- Provisioning CLI commands: `skills/acm-certificate-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/acm-certificate-deployer/evals/evals.json`
