# Advanced Patterns — ACM Certificate Deployer

Load-on-demand deep dives moved verbatim from SKILL.md: mindset misconceptions, dependency graph, expert heuristics, and recent features.

## Mindset — three provisioning-time misconceptions

Three misconceptions dominate ACM certificate misdesign at
provisioning time:

- **"I need to manually renew my ACM certificates."** You do not.
  ACM-managed certificates (requested via ACM, not imported) are
  renewed automatically by ACM 60 days before expiry. Imported
  certificates (from third-party CAs) are NOT auto-renewed — you
  must re-import the renewed certificate.

- **"Email validation is fine for production."** Email validation is
  DEPRECATED and unreliable. Domain validation (DNS CNAME) is the
  recommended method — it is automatable, repeatable, and enables
  automatic renewal. Email validation sends to WHOIS-registered
  addresses (or five common admin addresses) and requires manual
  click-through.

- **"I can put my CloudFront certificate in any region."** You
  cannot. CloudFront requires the ACM certificate to be in
  us-east-1. This is a hard constraint — no workaround. Certificates
  in other regions are invisible to CloudFront.

## Configuration dependency graph (novel heuristic)

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Domain names | none — `request` argument | domain names CANNOT be added/removed after request (must request a new certificate) | SAN list on cert |
| Validation method | none — `request` argument (DNS or EMAIL) | **CANNOT be changed after request** — must re-request to switch | DNS: automatable renewal; EMAIL: manual click-through |
| DNS validation CNAME | Route53 hosted zone (or third-party DNS) | CNAME must remain in place for the cert's lifetime (ACM re-validates periodically); removing it blocks renewal | automatic renewal |
| Certificate status | validation complete | `PENDING_VALIDATION` → `ISSUED` (DNS: minutes to hours; EMAIL: depends on click-through) | attachment to ALB/CloudFront/API Gateway |
| CloudFront integration | certificate in us-east-1 + `ISSUED` status | cert in any other region is invisible to CloudFront | CloudFront TLS termination |
| Imported certificate | PEM cert + PEM private key + PEM chain | **NOT auto-renewed** — must re-import on expiry | same as ACM-issued (but manual renewal) |
| Private certificate (via Private CA) | AWS Private CA exists in the account/region | private certs are NOT trusted by browsers by default (internal use only) | internal mTLS, private endpoints |
| Resource-based policy (sharing) | certificate ARN exists | sharing is for PRIVATE certificates only; public certs are not shareable this way | cross-account private cert usage |
| Key algorithm | RSA 2048 (default) or EC prime256v1 | **CANNOT be changed after request** — must re-request | TLS cipher suite compatibility |
| Tags | none — optional `--tags` | mutable via `add-tags`/`remove-tags` | cost allocation, governance |

**The immutable rows are the ones a baseline model misses.** Domain
names, validation method, and key algorithm are set at request time
and CANNOT be changed without re-requesting the certificate. The
procedure below forces an explicit decision on each before the
`request-certificate` call.

**Cross-dependency gotchas:**
- A certificate requested with DNS validation CANNOT be switched to
  email validation (or vice versa). You must re-request.
- CloudFront integration is region-locked to us-east-1. This is
  non-negotiable and the #1 cause of "CloudFront can't find my
  certificate" issues.
- The DNS validation CNAME must remain in the DNS for the entire
  lifetime of the certificate. Removing it causes renewal to fail.
- Imported certificates do NOT auto-renew. Set a renewal reminder or
  monitoring for the expiry date.
- Wildcard certificates (*.example.com) cover one level of subdomain
  only. `*.example.com` matches `www.example.com` but NOT
  `api.v2.example.com`. For multi-level, request SANs explicitly.

## Expert heuristic — CloudFront us-east-1 requirement

CloudFront is a global service, but its ACM certificate integration
is region-locked to us-east-1. A baseline model may say "use any
region"; this is wrong.

```text
CloudFront distribution
  → ViewerCertificate → AcmCertificateArn
  → the ARN MUST point to us-east-1
  → arn:aws:acm:us-east-1:<acct>:certificate/<uuid>

If the certificate is in any other region:
  → CloudFront returns: "The specified certificate does not exist"
  → even though the certificate exists (in another region)
```

**Operational pattern for multi-region deployments:**
- Request the certificate in us-east-1 for CloudFront.
- Request a SEPARATE certificate in the ALB's region for the ALB.
- Certificates are region-scoped; they cannot be referenced cross-
  region.

**Common mistake:** requesting the certificate in the same region as
the origin (e.g., us-west-2) and then trying to attach it to
CloudFront. The certificate is invisible to CloudFront. Re-request in
us-east-1.

## Recent AWS features (2023-2026)

**Recent AWS features (2023-2026):**
- **EC key algorithm support (2024-2025):** ACM now supports EC
  prime256v1 (P-256) keys for new certificate requests, in addition
  to RSA 2048. EC keys offer better performance and smaller cert
  sizes.
- **TLS 1.3 enforcement (2024-2025):** CloudFront and ALB now support
  enforcing TLS 1.3 as the minimum protocol version with ACM
  certificates.
- **Multi-region private certificates (2023-2024):** Private
  certificates can be requested in multiple regions from a single
  Private CA (region-bound, but same PCA root).
- **ACM certificate transparency logging (2023-2024):** Public
  certificates are logged to Certificate Transparency (CT) logs by
  default. Opt-out available for private domains.
- **Private CA cross-account sharing via RAM (2023-2024):** Private
  CAs can be shared across accounts via AWS RAM (Resource Access
  Manager) for organization-wide private PKI.
- **ACM for Nitro Enclaves (2024-2025):** Private certificates can
  be used within Nitro Enclaves for secure workloads.
