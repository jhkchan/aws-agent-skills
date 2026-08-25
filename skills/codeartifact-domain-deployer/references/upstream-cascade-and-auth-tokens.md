# Upstream Cascade and Auth Tokens — CodeArtifact Domain Deployer

Deep reference on the CodeArtifact upstream and external-connection
cascade for dependency resolution, authorization token mechanics
(12-hour expiry, domain-scoped vs repository-scoped, CI/CD refresh
patterns), package ingest (publish and copy-package), and package
version immutability. Loaded on demand by the skill — kept out of
the main SKILL.md body so the provisioning procedure stays scannable.

## Upstream and external-connection cascade

### How dependency resolution works

When a package manager requests a package (e.g., `npm install lodash`),
CodeArtifact searches repositories in cascade order:

```text
npm install lodash
  → CodeArtifact resolves the repository endpoint from .npmrc
  → Searches my-team-packages (local repo)
    ├── Found lodash@4.17.21? → Return package
    └── Not found? → Continue to next upstream
  → Searches shared-team-packages (upstream repo 1)
    ├── Found lodash@4.17.20? → Return package
    └── Not found? → Continue to next upstream
  → Searches npmjs (external connection)
    ├── Found lodash@4.17.21 on npmjs.com? → Return package
    └── Not found? → 404 to the client
```

### Configuring the cascade

```bash
# View current upstream configuration
aws codeartifact describe-repository \
  --domain my-domain \
  --repository my-team-packages \
  --query 'repository.upstreams' \
  --region us-east-1 --output table

# Set upstreams (order is significant — first match wins)
aws codeartifact update-repository \
  --domain my-domain \
  --repository my-team-packages \
  --upstreams repository=shared-team-packages \
  --upstreams repository=company-approved-packages \
  --upstreams external-connection=npmjs \
  --region us-east-1

# Remove all upstreams
aws codeartifact update-repository \
  --domain my-domain \
  --repository my-team-packages \
  --region us-east-1
# (omit --upstreams to clear)
```

### Supply-chain security: cascade order matters

The cascade order is a security boundary. Placing external connections
before internal repositories enables dependency confusion attacks:

```text
ATTACK SCENARIO (wrong order — external before internal):
  Upstreams: [ext:npmjs, shared-team-packages]
  → Attacker publishes "internal-lib@1.0.0" on npmjs.com
  → npm install internal-lib resolves from npmjs FIRST
  → Malicious package executes in your environment

CORRECT ORDER (internal before external):
  Upstreams: [shared-team-packages, ext:npmjs]
  → npm install internal-lib searches shared-team-packages FIRST
  → Finds legitimate package, never reaches npmjs
  → Attack blocked
```

**Rule:** always list internal repositories BEFORE external connections
in the upstream cascade.

### External connections reference

| External connection name | Public registry | Package format |
|---|---|---|
| `npmjs` | npmjs.com | npm |
| `pypi` | pypi.org | pip (Python) |
| `mavencentral` | search.maven.org | maven (Java) |
| `nuget-org` | nuget.org | nuget (.NET) |
| `rubygems` | rubygems.org | gem (Ruby) |
| `cargo` | crates.io | cargo (Rust) |
| `swift` | (Swift package index) | swift |

Only ONE external connection per public source per domain is allowed.

```bash
# Verify available external connections
aws codeartifact list-external-connections \
  --region us-east-1
```

## Authorization token mechanics

### Token lifecycle

CodeArtifact authorization tokens are short-lived:

```text
Token properties:
  ├── Validity: 12 hours (configurable up to 12 hours max)
  ├── Scope: domain-level (all repos) OR repository-level (one repo)
  ├── Generation: aws codeartifact login OR get-authorization-token API
  └── Storage: .npmrc (npm), pip.conf (pip), settings.xml (maven)
```

### Login CLI per package format

```bash
# npm — writes .npmrc in the current directory
aws codeartifact login \
  --tool npm \
  --domain my-domain \
  --domain-owner 123456789012 \
  --repository my-team-packages \
  --region us-east-1

# pip — writes pip.conf under a codeartifact directory
aws codeartifact login \
  --tool pip \
  --domain my-domain \
  --domain-owner 123456789012 \
  --repository my-team-packages \
  --region us-east-1

# twine (Python publish) — configures upload endpoint
aws codeartifact login \
  --tool twine \
  --domain my-domain \
  --domain-owner 123456789012 \
  --repository my-team-packages \
  --region us-east-1
```

### CI/CD token refresh patterns

**Pattern 1: Login per build (recommended)**

```yaml
# GitHub Actions / GitLab CI / CodeBuild
steps:
  - name: Configure CodeArtifact
    run: |
      aws codeartifact login \
        --tool npm \
        --domain my-domain \
        --domain-owner 123456789012 \
        --repository my-team-packages \
        --region us-east-1
  - name: Install dependencies
    run: npm ci
```

**Pattern 2: API token as environment variable**

```bash
# Generate short-lived token via API
TOKEN=$(aws codeartifact get-authorization-token \
  --domain my-domain \
  --domain-owner 123456789012 \
  --query 'authorizationToken' --output text \
  --region us-east-1)

# Inject into npm config
REPO_ENDPOINT="https://my-domain-123456789012.d.codeartifact.us-east-1.amazonaws.com/npm/my-team-packages/"
npm config set "${REPO_ENDPOINT}:_authToken" "$TOKEN"
npm config set registry "${REPO_ENDPOINT}"
```

**Pattern 3: AWS credential chain (CodeBuild role)**

In CodeBuild or ECS, the task role can call `get-authorization-token`
directly. Use the AWS SDK in a build step to refresh the token before
package installation.

### Domain-scoped vs repository-scoped tokens

```bash
# Domain-scoped token (access ALL repos in the domain)
TOKEN=$(aws codeartifact get-authorization-token \
  --domain my-domain \
  --domain-owner 123456789012 \
  --region us-east-1)

# Repository-scoped token (access ONE repo only — more restrictive)
# Note: repository-scoped tokens are obtained via login with --repository
```

**Security best practice:** use repository-scoped tokens in CI/CD to
limit blast radius. A domain-scoped token grants access to ALL repos.

## Package ingest

### Direct publish

```bash
# npm publish (after aws codeartifact login --tool npm)
cd my-package/
npm publish

# pip publish via twine (after aws codeartifact login --tool twine)
twine upload dist/*

# maven deploy (configure settings.xml with repository endpoint)
mvn deploy
```

### Copy from upstream (ingest without consuming in CI)

```bash
# Copy a specific package version from upstream to local repo
aws codeartifact copy-package-versions \
  --domain my-domain \
  --repository my-team-packages \
  --source-repository shared-team-packages \
  --format npm \
  --namespace lodash \
  --package lodash \
  --versions 4.17.21 \
  --region us-east-1
```

This ingests a package version from an upstream repository into the
local repository, creating a permanent copy that persists even if the
upstream removes it.

## Package version immutability

Published package versions are IMMUTABLE:

```text
- Version 1.0.0 published → CANNOT be overwritten with 1.0.0
- Version 1.0.0 published → CANNOT be selectively deleted
- Version 1.0.0 published → CAN be removed by lifecycle policy rules
- New version 1.0.1 → CAN be published (different version number)
```

This immutability is a supply-chain integrity guarantee. It prevents
silent tampering with published artifacts.

### Package origin controls (2024-2025 feature)

Package origin controls restrict how a package can enter a repository:

```bash
# Restrict a package to only be published internally (not from upstream)
aws codeartifact put-package-origin-configuration \
  --domain my-domain \
  --repository my-team-packages \
  --format npm \
  --namespace my-company \
  --package critical-lib \
  --restrictions publish=ALLOW,upstream=BLOCK \
  --region us-east-1
```

This prevents a dependency confusion attack where a malicious package
from npmjs.com overwrites an internal package name via the upstream
cascade.

## Terraform examples

```hcl
# Domain with CMK encryption
resource "aws_kms_key" "codeartifact" {
  description             = "CodeArtifact domain encryption key"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

resource "aws_codeartifact_domain" "main" {
  name           = "my-domain"
  encryption_key = aws_kms_key.codeartifact.arn
}

# Repository within domain
resource "aws_codeartifact_repository" "npm" {
  domain     = aws_codeartifact_domain.main.name
  repository = "my-team-packages"
  description = "Internal npm packages"
}

# Upstream configuration (internal first, external last)
resource "aws_codeartifact_repository" "shared" {
  domain     = aws_codeartifact_domain.main.name
  repository = "shared-team-packages"
}

resource "aws_codeartifact_repository" "npm_repo" {
  domain     = aws_codeartifact_domain.main.name
  repository = "my-team-packages"

  upstream {
    repository_name = aws_codeartifact_repository.shared.repository
  }

  # External connection must be configured separately
}

# Repository policy for cross-account access
resource "aws_codeartifact_repository_permissions_policy" "cross_account" {
  domain     = aws_codeartifact_domain.main.name
  repository = aws_codeartifact_repository.npm.repository
  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::999999999999:root" }
        Action = [
          "codeartifact:ReadFromRepository",
          "codeartifact:GetAuthorizationToken",
          "codeartifact:GetRepositoryEndpoint"
        ]
        Resource = "*"
      }
    ]
  })
}
```
---

## Expert heuristic — the upstream and external-connection cascade (moved from SKILL.md)

A baseline model says "connect to npmjs.com." The correct heuristic
recognizes that dependency resolution follows a cascade chain and the
order is significant.

```text
Package request (e.g., npm install lodash):

  1. Local repository (my-team-packages)
     → found? return. not found? continue.

  2. Upstream repository 1 (shared-team-packages)
     → found? return. not found? continue.

  3. Upstream repository 2 (company-approved-packages)
     → found? return. not found? continue.

  4. External connection (npmjs.com)
     → found? return from public registry. not found? 404.

Cascade configuration:
  aws codeartifact update-repository \
    --repository my-team-packages \
    --domain my-domain \
    --upstreams repository=shared-team-packages \
    --upstreams repository=company-approved-packages \
    --upstreams external-connection=npmjs

Order matters: the first match wins. Put internal repos before public.
```

**Key implication:** the cascade is a supply-chain security control.
Putting internal repos before the external connection ensures that
internal (vetted) packages take precedence over public ones. This
prevents dependency confusion attacks where a malicious package on
npmjs.com shadows an internal package name.

## Expert heuristic — the 12-hour authorization token (moved from SKILL.md)

CodeArtifact authorization tokens expire. A baseline model generates
the token once and assumes it is permanent. The correct heuristic
recognizes the 12-hour expiry and builds refresh into the pipeline.

```text
Token lifecycle:
  aws codeartifact login --tool npm --domain my-domain --domain-owner 123456789012
  → writes .npmrc with: //my-domain-123456789012.d.codeartifact.us-east-1.amazonaws.com/npm/my-repo/:_authToken=<token>
  → token expires in 12 hours

CI/CD implication:
  ├── Pipeline MUST run `aws codeartifact login` before every build
  ├── Caching the token across runs > 12 hours = SILENT FAILURE
  └── Alternative: generate a short-lived token via GetAuthorizationToken API
      and inject as an environment variable

Token scope:
  ├── Domain-scoped: access ALL repositories in the domain
  └── Repository-scoped: access only ONE repository (more restrictive)
```

**Key implication:** CI/CD pipelines that cache the `.npmrc` or
`pip.conf` with the auth token will break after 12 hours. The login
command must be part of the build step, not a one-time setup.

