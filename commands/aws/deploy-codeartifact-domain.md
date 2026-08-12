---
description: Provision an AWS CodeArtifact domain with production-grade defaults (domain as IAM boundary, upstream/external-connection cascade, 12-hour auth token, cross-account repository policy, VPC endpoint, KMS encryption, lifecycle policy, package immutability). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "codeartifact domain"
  - "codeartifact external connection"
  - "codeartifact upstream cascade"
  - "codeartifact login"
  - "codeartifact authorization token"
  - "codeartifact vpc endpoint"
  - "codeartifact kms encryption"
  - "codeartifact repository policy"
  - "codeartifact lifecycle policy"
  - "codeartifact package immutability"
  - "codeartifact cross-account"
  - "create codeartifact domain"
  - "deploy codeartifact domain"
routes_to: codeartifact-domain-deployer
---

# /aws:deploy-codeartifact-domain

Activate the `codeartifact-domain-deployer` skill and provision an AWS
CodeArtifact domain with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Domain as IAM boundary (domain owns KMS key, permissions policy)
2. Repository creation within domain
3. Upstream repository cascade (order matters for security)
4. External connection (npmjs.com, pypi.org, etc.)
5. Authorization token (aws codeartifact login, 12-hour expiry)
6. Package ingest (publish / copy-package)
7. Cross-account repository policy
8. VPC interface endpoint (private access — both API + repos endpoints)
9. KMS encryption (immutable at creation)
10. Lifecycle policy and immutability
11. CloudWatch metrics (DownloadPackageVersion, PublishPackageVersion)
12. Recent features (Swift, Cargo, package origin controls)

## When to use

- You need to create a CodeArtifact domain.
- You are configuring the upstream/external-connection cascade.
- You need to set up auth tokens for package consumption.
- You are sharing repositories cross-account.
- You need VPC interface endpoints for private access.
- You need to configure KMS encryption.
- You need lifecycle policies for package retention.

## When NOT to use

- **CodeArtifact repository-only operations** — use codeartifact-
  repository-deployer for repo-level config without domain context.
- **S3-backed package storage** — different service.
- **GitHub Packages** — separate service.

## How to invoke

### Slash command

```
/aws:deploy-codeartifact-domain
```

Then provide: domain name, KMS key ARN (if CMK), package format,
repository name, upstream configuration, external connection, target
account ID (if cross-account), VPC details (if private access),
lifecycle policy requirements, tags.

### Natural language

Any of these routes to the same skill:

- "create a codeartifact domain with npm and pip repositories"
- "set up codeartifact upstream cascade with npmjs external connection"
- "configure codeartifact VPC endpoint for private access"
- "share codeartifact repository with another account"
- "set up codeartifact with custom KMS encryption"

### CLI routing

```bash
node cli/bin/cli.js route "create a codeartifact domain"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create CodeArtifact
domains. The output checklist feeds into verification pipelines and
downstream audit skills.

## Example

```
You: /aws:deploy-codeartifact-domain

     Create a CodeArtifact domain called my-domain with an npm
     repository, internal upstream shared-team-packages, and
     npmjs external connection. Use CMK encryption. Grant read
     access to account 999999999999.

Skill:
  CODEARTIFACT_DOMAIN: my-domain (123456789012)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Domain: my-domain — encryption: CMK
    [✓] Repository: my-team-packages (npm)
    [✓] Upstream cascade: shared-team-packages → ext:npmjs
    [✓] Cross-account: 999999999999 (read)
    [✓] Auth token: 12-hour expiry — CI refresh required
  VERIFICATION_COMMANDS:
    aws codeartifact describe-domain --domain my-domain --region us-east-1
    aws codeartifact describe-repository --domain my-domain --repository my-team-packages --region us-east-1
```

## References

- Skill definition: `skills/codeartifact-domain-deployer/SKILL.md`
- Upstream cascade and auth tokens: `skills/codeartifact-domain-deployer/references/upstream-cascade-and-auth-tokens.md`
- Encryption, VPC endpoint, and metrics: `skills/codeartifact-domain-deployer/references/encryption-vpc-endpoint-and-metrics.md`
- Eval suite: `skills/codeartifact-domain-deployer/evals/evals.json`
