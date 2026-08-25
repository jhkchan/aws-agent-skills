---
name: acm-certificate-deployer
description: 'Provisions AWS ACM certificates with production defaults: certificate request (domain names, wildcard), DNS validation (Route53 CNAME, cross-account), email validation (deprecated), certificate renewal (automatic, managed by ACM), import third-party certificates (PEM format, private key, chain), CloudFront integration (must be in us-east-1), cross-account sharing (resource-based policy with service principals), ACM private CA integration, ACM for private certificates. Emits a READY_TO_DEPLOY checklist with verification commands. Use when requesting an ACM certificate, setting up DNS validation, importing a third-party cert, configuring CloudFront TLS, or deploying private certificates via AWS Private CA. Triggers: request ACM certificate, DNS validation, Route53 CNAME ACM, ACM wildcard certificate, ACM CloudFront certificate, ACM renewal, import certificate ACM, AWS Private CA, ACM private certificate.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with acm, route53, iam, and cloudfront access. Works with Terraform aws_acm_certificate / aws_acm_certificate_validation resources and CloudFormation AWS::CertificateManager::Certificate templates.'
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
  tags: aws, acm, certificate-manager, cloudops, deploy, security, provisioning, tls, dns-validation, cloudfront, private-ca, wildcard
  dependencies: aws-orchestrator
  keywords: aws, acm, certificate manager, cloudops, deploy, provisioning, tls certificate, ssl certificate, dns validation, route53, wildcard certificate, certificate renewal, import certificate, cloudfront integration, us-east-1, private ca, aws private ca, private certificate, cross-account sharing, resource-based policy, pem, email validation
  when_to_use: Invoke when the user wants to request an AWS Certificate Manager (ACM) certificate (public or private), set up DNS validation via Route53, configure a wildcard certificate, import a third-party certificate, deploy a certificate for CloudFront (us-east-1 requirement), integrate with AWS Private CA, or share a private certificate cross-account. Do NOT invoke for IAM server certificates (deprecated), for self-signed certificates outside ACM, or for auditing existing certificate expiry (use acm-certificate-expiry-auditor).
---

# ACM Certificate Deployer

An AWS CloudOps agent skill that provisions AWS Certificate Manager
(ACM) certificates with correct defaults. The skill walks the
operator through certificate request, validation, renewal, and
integration, captures domain and deployment decisions, explains why
each default matters, and emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## Activation keywords

request ACM certificate, DNS validation ACM, Route53 CNAME ACM, ACM
wildcard certificate, ACM CloudFront certificate, ACM renewal, import
certificate ACM, AWS Private CA, ACM private certificate, ACM cross-
account, PEM import certificate.

## STRICT output contract

When this skill is invoked with an ACM-certificate-provisioning
request (domain names, validation method, CloudFront integration,
private CA, or a partial configuration), the agent MUST respond with
the READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `ACM_CERTIFICATE:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-
based evals and downstream provisioning pipelines rely on; deviating
from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the checklist
(marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Public vs private certificate | Boundary call |
| Step 2 — Domain names (apex, www, wildcard, SAN) | Domain scoping |
| Step 3 — DNS validation (Route53 CNAME, cross-account) | Validation method |
| Step 4 — Email validation (deprecated) | Legacy method |
| Step 5 — Certificate renewal (automatic, managed) | Renewal model |
| Step 6 — Import third-party certificates (PEM) | Import flow |
| Step 7 — CloudFront integration (us-east-1 requirement) | CloudFront TLS |
| Step 8 — Cross-account sharing (service principals) | Sharing scope |
| Step 9 — AWS Private CA integration / private certs | Private PKI |
| Step 10 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/validation-and-renewal.md | DNS validation + renewal detail |
| references/provisioning-cli-commands.md | Copy-pasteable CLI sequence |
| references/advanced-patterns.md | Dependency graph + heuristics + recent features |
| references/error-handling.md | Validation/import/renewal failure remedies |

## Mindset

**One-line takeaway:** ACM is a managed TLS certificate service that
handles issuance, renewal, and deployment for AWS-integrated
endpoints (CloudFront, ALB, API Gateway, etc.). For public
certificates, DNS validation is the default; ACM manages renewal
automatically. For CloudFront, the certificate MUST be in us-east-1.

Three misconceptions in full (ACM auto-renews managed certs only; email validation is deprecated for production; CloudFront certs must be in us-east-1): [Advanced patterns](references/advanced-patterns.md).

## Configuration dependency graph (novel heuristic)

ACM certificate configurations are NOT independent. Many are
immutable after issuance, others silently break downstream
integrations. Use this graph both to sequence provisioning and to
debug "why won't CloudFront see my certificate?" later.

Full dependency table (immutable domain names / validation method / key algorithm, CNAME lifetime, CloudFront region lock, imported-cert renewal) plus cross-dependency gotchas: [Advanced patterns](references/advanced-patterns.md).

## Expert heuristic: DNS validation CNAME lifecycle

Full CNAME lifecycle (per-domain CNAME generation, detection timeline, re-validation, renewal dependency) and cross-account DNS validation: [Validation and renewal](references/validation-and-renewal.md).

## Expert heuristic: CloudFront us-east-1 requirement

us-east-1 mechanics (ViewerCertificate ARN check, "certificate does not exist" behavior, multi-region request pattern): [Advanced patterns](references/advanced-patterns.md).

## Expert heuristic: ACM-managed vs imported renewal matrix

Renewal matrix by certificate source (ACM-issued DNS/email, imported, private via PCA): [Validation and renewal](references/validation-and-renewal.md).

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with ACM access | Can't provision without it | `aws sts get-caller-identity` |
| Region selected | CloudFront requires us-east-1; ALB/API Gateway use the resource's region | `aws configure get region` |
| Domain names identified | Domain names CANNOT be added after request; must re-request | List apex, www, wildcard, SANs |
| DNS validation (recommended) | Route53 hosted zone OR third-party DNS where CNAME can be added | `aws route53 list-hosted-zones` |
| Route53 hosted zone matches domain | The CNAME record must be in the zone for the domain | `aws route53 list-hosted-zones-by-name` |
| CloudFront target (if applicable) | Certificate MUST be in us-east-1 for CloudFront | Confirm region is us-east-1 |
| AWS Private CA (for private certs) | Private certificates require an active PCA in the account/region | `aws acm-pca list-certificate-authorities` |
| PEM files ready (for import) | Certificate, private key, and chain in PEM format | Verify files exist and are valid PEM |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Public vs private certificate

The first decision is whether to request a public certificate (trusted
by browsers) or a private certificate (trusted only within your
organization, via AWS Private CA).

**Decision tree:**

```text
Is the certificate for a public-facing website/API (browser-trusted)?
├── YES → Public certificate  (ACM-issued, DNS validation)
│         Free, auto-renewed, browser-trusted
│         Use for: CloudFront, ALB, API Gateway (public endpoints)
└── NO  → Is it for internal mTLS, private endpoints, or corporate trust?
    ├── YES → Private certificate  (via AWS Private CA)
    │         Requires active PCA; NOT browser-trusted by default
    │         Use for: internal APIs, mTLS, corporate intranet
    └── NO  → Public certificate  (the safest default)
```

**Feature comparison:**

| Feature | Public (ACM-issued) | Private (via Private CA) | Imported (third-party) |
|---|---|---|---|
| Cost | Free | PCA cost (~$400/CA/month) + per-cert | External CA cost |
| Browser trust | Yes | No (must install PCA root) | Yes (if CA is trusted) |
| Auto-renewal | Yes (DNS validation) | Yes (ACM manages) | No (manual re-import) |
| Wildcard support | Yes | Yes | Depends on CA |
| CloudFront support | Yes (us-east-1) | No (CloudFront requires public) | Yes (us-east-1) |
| Key export | No | Yes (private certs can be exported) | Yes (you own the key) |

## Step 2 — Domain names (apex, www, wildcard, SAN)

ACM certificates support multiple domain names via Subject Alternative
Names (SANs). All domains on a certificate share the same validation
and renewal lifecycle.

**Domain name patterns:**

| Pattern | Matches | Does NOT match |
|---|---|---|
| `example.com` | `example.com` only | `www.example.com` |
| `*.example.com` | `www.example.com`, `api.example.com` | `example.com`, `api.v2.example.com` |
| `example.com` + `*.example.com` | `example.com` + one-level subdomains | `api.v2.example.com` |
| `*.v2.example.com` | `api.v2.example.com` | `example.com`, `www.example.com` |

**Best practices:**
- Always include BOTH the apex domain and the wildcard: `example.com`
  and `*.example.com`. This covers the root and one level of
  subdomains.
- For multi-level subdomains, add explicit SANs (e.g.,
  `*.v2.example.com`).
- Wildcard covers ONE level only. `*.example.com` does NOT match
  `api.v2.example.com`.
- Domain names CANNOT be added after request. Plan all domains before
  `request-certificate`.

**Common mistake:** requesting only `*.example.com` (wildcard) and
forgetting the apex `example.com`. The wildcard does NOT cover the
apex domain. Users visiting `https://example.com` get a certificate
error.

## Step 3 — DNS validation (Route53 CNAME, cross-account)

DNS validation is the recommended validation method. ACM provides a
CNAME record that you add to your DNS. Once detected, the certificate
is issued.

**Request with DNS validation:**

Request CLI: [Provisioning CLI commands](references/provisioning-cli-commands.md).

**Retrieve the CNAME records:**

Retrieval CLI: [Provisioning CLI commands](references/provisioning-cli-commands.md).

**Add the CNAME to Route53:**

Route53 UPSERT CLI: [Provisioning CLI commands](references/provisioning-cli-commands.md).

**Cross-account DNS validation:** when the Route53 hosted zone is in
a different account, create the CNAME in the hosted zone's account.
This requires IAM permissions in both accounts, or manual creation.

**Common mistake:** deleting the CNAME record after the certificate
is issued. The CNAME must REMAIN for the certificate's lifetime. ACM
re-validates periodically; removing the CNAME blocks renewal.

## Step 4 — Email validation (deprecated)

Email validation sends a validation email to the domain's registered
contacts (WHOIS + admin@/administrator@/webmaster@/hostmaster@/postmaster@).
The recipient must click a link to validate. **Email validation is
DEPRECATED.** Use DNS validation instead.

Why email validation fails in production and the switch-to-DNS procedure: [Validation and renewal](references/validation-and-renewal.md).

## Step 5 — Certificate renewal (automatic, managed by ACM)

ACM-managed certificates (DNS or email validated) are renewed
automatically by ACM.

**Renewal timeline:**
- ACM begins the renewal process **60 days before expiry**.
- For DNS-validated certs: ACM checks the CNAME is present. If yes,
  auto-renews silently.
- For email-validated certs: ACM sends a renewal email. The recipient
  must click the link.
- Renewed certificates maintain the same ARN — no need to update
  CloudFront/ALB/API Gateway references.

Renewal-eligibility rules and expiry monitoring: [Validation and renewal](references/validation-and-renewal.md).

## Step 6 — Import third-party certificates (PEM format)

ACM can import certificates from third-party CAs (DigiCert, Let's
Encrypt, internal PKI, etc.). Imported certificates are NOT auto-
renewed.

**Import requires three PEM files:**

```bash
aws acm import-certificate \
  --certificate fileb://certificate.pem \
  --private-key fileb://private-key.pem \
  --certificate-chain fileb://chain.pem \
  --region us-east-1
```

**PEM format requirements:**
- `certificate.pem`: the end-entity certificate (leaf cert).
- `private-key.pem`: the private key (unencrypted PEM, PKCS#1 or
  PKCS#8).
- `chain.pem`: the intermediate certificate chain (root CA →
  intermediates → leaf), excluding the leaf cert.

**Common import errors:**
MalformedCertificate / CertificateValidator Timeout / InvalidCertificate: [Error handling](references/error-handling.md).

**Renewal for imported certificates:**
Re-import workflow: [Validation and renewal](references/validation-and-renewal.md).

## Step 7 — CloudFront integration (us-east-1 requirement)

CloudFront requires the ACM certificate to be in **us-east-1**. This
is a hard constraint with no workaround.

**Attaching a certificate to CloudFront:**

update-distribution ViewerCertificate CLI: [Provisioning CLI commands](references/provisioning-cli-commands.md).

**Key rules:**
- Certificate MUST be in us-east-1 (global CloudFront requirement).
- Certificate MUST be `ISSUED` (not `PENDING_VALIDATION`).
- `sni-only`: serves TLS only to clients that support SNI (all modern
  browsers). Use `vip` for legacy clients (incurs extra cost).
- `MinimumProtocolVersion`: `TLSv1.2_2021` is the recommended minimum.

**Common mistake:** requesting the certificate in the origin's region
(e.g., us-west-2) and then trying to attach to CloudFront. The cert
is invisible. Re-request in us-east-1.

## Step 8 — Cross-account sharing (resource-based policy)

Cross-account sharing applies to **private certificates** (issued via
AWS Private CA). Public ACM certificates are not shared via resource-
based policy — they are referenced by ARN within the same account.

**Sharing private certificates:**
- Private certificates are issued by AWS Private CA.
- To use a private certificate in another account, share the Private
  CA (not the certificate) via `acm-pca create-permission`.
- The consuming account can then request certificates from the shared
  PCA.

acm-pca create-permission CLI: [Provisioning CLI commands](references/provisioning-cli-commands.md).

**For public certificates across accounts:**
- ACM certificates are region-scoped and account-scoped.
- Cross-account referencing is NOT supported for public certs.
- Each account must request its own certificate for its own resources.

**Service principals:** when sharing with AWS services (e.g.,
allowing Elastic Beanstalk to use a certificate), the resource-based
policy must include the service principal (e.g.,
`elasticbeanstalk.amazonaws.com`).

## Step 9 — AWS Private CA integration / private certificates

AWS Private Certificate Authority (Private CA) is a managed private CA
service for issuing private TLS certificates within your organization.

**Private certificate workflow:**

Create-CA / issue-certificate / request-private-certificate CLI: [Provisioning CLI commands](references/provisioning-cli-commands.md).

**Private certificate characteristics:**
- NOT trusted by browsers (must install the PCA root/intermediate).
- Auto-renewed by ACM (same as public certs with DNS validation).
- Can be exported (private key + cert + chain) for use outside AWS.
- Cost: PCA is ~$400/CA/month + per-certificate issuance fee.

**Use cases:** internal mTLS, private API endpoints, corporate
intranet, IoT device authentication.

## Step 10 — Recent features

2023-2026 features — EC key support, TLS 1.3 enforcement, multi-region private certs, CT logging, PCA sharing via RAM, Nitro Enclaves: [Advanced patterns](references/advanced-patterns.md).

## NEVER do these things

1. **NEVER request a CloudFront certificate outside us-east-1.**
   CloudFront requires the certificate to be in us-east-1. A
   certificate in any other region is invisible to CloudFront and
   will produce "certificate does not exist" errors.

2. **NEVER delete the DNS validation CNAME after issuance.** The
   CNAME must remain in DNS for the certificate's lifetime. ACM re-
   validates periodically; removing the CNAME blocks renewal and the
   certificate will expire.

3. **NEVER use email validation for production certificates.** Email
   validation is deprecated, requires manual click-through for each
   renewal, and is unreliable. Use DNS validation.

4. **NEVER assume imported certificates auto-renew.** ACM does NOT
   renew imported certificates. You must monitor the expiry date and
   re-import the renewed certificate before it lapses.

5. **NEVER assume a wildcard certificate covers the apex domain.**
   `*.example.com` matches `www.example.com` but NOT `example.com`.
   Always request BOTH the apex and wildcard as separate domain names
   on the same certificate.

6. **NEVER request only a wildcard for multi-level subdomains.**
   `*.example.com` covers one level only. `api.v2.example.com` is NOT
   covered. Add explicit SANs for multi-level subdomains.

7. **NEVER change the validation method after request.** DNS and email
   validation are set at request time and CANNOT be changed. Re-request
   to switch.

8. **NEVER use a private certificate for public-facing endpoints.**
   Private certificates (via AWS Private CA) are NOT trusted by
   browsers. Use public ACM certificates for public CloudFront/ALB/API
   Gateway.

9. **NEVER assume domain names can be added after request.** The list
   is immutable after `request-certificate`. Plan all domains (apex,
   www, wildcard, SANs) before requesting.

10. **NEVER export a private certificate key without a secure storage
    plan.** Private keys exported via ACM (`export-certificate`) must
    be stored in a secure secret store (Secrets Manager). Never commit
    to source control.

11. **NEVER forget to monitor imported certificate expiry.** Set a
    CloudWatch alarm on `DaysToExpiry` < 30 for imported certificates.

12. **NEVER use `sni-only` without confirming client compatibility.**
    `sni-only` fails for legacy clients without SNI support. Use `vip`
    if legacy clients are required (incurs extra cost).

## Output format

```text
ACM_CERTIFICATE: <domain-name> (<certificate-arn>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Certificate type: Public | Private (via Private CA <ca-arn>) | Imported
  [✓|✗] Domain names: <apex>, <wildcard>, <SANs>
  [✓|✗] Validation method: DNS (recommended) | Email (deprecated)
  [✓|✗] DNS validation CNAME: added to Route53 zone <zone-id> (or third-party DNS)
  [✓|✗] Certificate status: ISSUED | PENDING_VALIDATION
  [✓|✗] Key algorithm: RSA_2048 | EC_prime256v1
  [✓|✗] Renewal: Automatic (ACM-managed, 60 days before expiry) | Manual (imported)
  [✓|✗] Region: <region> (us-east-1 required for CloudFront)
  [✓|✗] CloudFront integration: <distribution-id> → cert in us-east-1 | N/A
  [✓|✗] Cross-account sharing: <scope> (resource-based policy) | Same account
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws acm describe-certificate --certificate-arn <arn> --region <region>
  aws acm list-certificates --region <region>
  aws route53 list-resource-record-sets --hosted-zone-id <zone-id>
  aws cloudfront get-distribution-config --id <distribution-id>  # if CloudFront
```

### Worked example — public wildcard cert with DNS validation for CloudFront

```text
ACM_CERTIFICATE: *.example.com (arn:aws:acm:us-east-1:123456789012:certificate/abc-123)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Certificate type: Public
  [✓] Domain names: example.com, *.example.com
  [✓] Validation method: DNS (recommended)
  [✓] DNS validation CNAME: added to Route53 zone Z2KVMGOMGDOOU2
  [✓] Certificate status: ISSUED
  [✓] Key algorithm: RSA_2048
  [✓] Renewal: Automatic (ACM-managed, 60 days before expiry)
  [✓] Region: us-east-1 (required for CloudFront)
  [✓] CloudFront integration: E1234567890ABC → cert in us-east-1
  [✓] Cross-account sharing: Same account (no sharing needed)
  [✓] Tags: Environment=production, Service=website
VERIFICATION_COMMANDS:
  aws acm describe-certificate --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc-123 --region us-east-1
  aws acm list-certificates --region us-east-1
  aws route53 list-resource-record-sets --hosted-zone-id Z2KVMGOMGDOOU2
  aws cloudfront get-distribution-config --id E1234567890ABC
```

## Error handling

PENDING_VALIDATION, CloudFront "certificate does not exist", MalformedCertificate, renewal-failed remedies: [Error handling](references/error-handling.md).

## References (load on demand)

- [Validation and renewal](references/validation-and-renewal.md) — DNS/email validation internals, CNAME lifecycle, renewal matrix, imported-cert lifecycle
- [Provisioning CLI commands](references/provisioning-cli-commands.md) — copy-pasteable request/validate/attach/import/PCA CLI sequence
- [Advanced patterns](references/advanced-patterns.md) — dependency graph, CloudFront us-east-1 heuristic, recent features
- [Error handling](references/error-handling.md) — validation, CloudFront, import, and renewal failure remedies

## Domain

AWS CloudOps / AWS Certificate Manager Provisioning & TLS Certificate
Management.

## AWS documentation

- **ACM User Guide** — https://docs.aws.amazon.com/acm/latest/userguide/acm-overview.html
- **DNS validation** — https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html
- **Email validation** — https://docs.aws.amazon.com/acm/latest/userguide/email-validation.html
- **Importing certificates** — https://docs.aws.amazon.com/acm/latest/userguide/import-certificate.html
- **ACM + CloudFront** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/RequestACMCert.html
- **AWS Private CA** — https://docs.aws.amazon.com/acm-pca/latest/userguide/PcaIntroduction.html
- **Certificate renewal** — https://docs.aws.amazon.com/acm/latest/userguide/managed-renewal.html
- **Cross-account PCA sharing** — https://docs.aws.amazon.com/acm-pca/latest/userguide/PcaSharing.html
