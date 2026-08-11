# Deployment CLI Commands — CodeArtifact Repository Deployer

Full copy-pasteable CLI command sequence for all 10 provisioning steps.
Variables to substitute: `<region>`, `<account-id>`, `<domain-name>`,
`<repository-name>`, `<format>`, `<ci-role>`, `<release-role>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=${AWS_DEFAULT_REGION:-us-east-1}

# Confirm or inspect existing domain
aws codeartifact describe-domain --domain <domain-name> 2>/dev/null \
  || echo "Domain does not exist — will be created"

# Confirm CI role exists
aws iam get-role --role-name <ci-role>

# Confirm external connections available in the Region
aws codeartifact list-external-connections --domain <domain-name> 2>/dev/null

# Confirm KMS key (if using a customer-managed key)
aws kms describe-key --key-id <cmk-id>
```

## Step 1: Create (or reuse) the domain

```bash
# Create new domain (optional KMS key)
aws codeartifact create-domain \
  --domain <domain-name> \
  --encryption-key arn:aws:kms:${REGION}:${ACCOUNT_ID}:key/<cmk-id>

# Or reuse existing domain — verify
aws codeartifact describe-domain \
  --domain <domain-name> \
  --query 'domain.{Name:name, Owner:owner, Arn:arn, EncryptionKey:encryptionKey}'
```

Domain naming rules:
- Unique within account + Region
- Use a short, org-wide name (`shared`, `companyname`)
- Cannot be renamed — choose carefully

## Step 2: Create the repository

```bash
aws codeartifact create-repository \
  --domain <domain-name> \
  --repository <repository-name> \
  --description "Shared <format> packages" \
  --tags '[{"Key":"Environment","Value":"production"},{"Key":"Format","Value":"<format>"}]'
```

Convention: `<domain>-<format>` (e.g., `shared-npm`, `shared-pip`).

## Step 3: Configure external connections

```bash
# Associate external connection (public registry bridge)
aws codeartifact associate-external-connection \
  --domain <domain-name> \
  --repository <repository-name> \
  --external-connection public:npmjs

# Verify
aws codeartifact describe-repository \
  --domain <domain-name> \
  --repository <repository-name> \
  --query 'repository.externalConnections'
```

Available external connections:
- `public:npmjs` — npm
- `public:pypi` — Python Package Index
- `public:maven-central` — Maven Central
- `public:maven-googleandroid` — Google Android Maven
- `public:maven-gradleplugins` — Gradle plugins
- `public:nuget-org` — NuGet Gallery
- `public:cargo` — crates.io
- `public:rubygems` — RubyGems

## Step 4: Configure upstream repositories

```bash
# Single upstream (chain to an internal mirror)
aws codeartifact update-repository \
  --domain <domain-name> \
  --repository <repository-name> \
  --upstreams repository=<internal-mirror-name>

# Multi-hop chain
aws codeartifact update-repository \
  --domain <domain-name> \
  --repository team-payments-npm \
  --upstreams repository=team-payments-internal,repository=shared-npm
```

Resolution order (left-to-right):
1. The repository itself
2. First upstream
3. Second upstream
4. External connection (always last)

**NEVER put an external connection upstream of an internal mirror.**

## Step 5: Configure repository IAM policies

### Domain owner admin policy

```bash
cat > /tmp/domain-admin-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DomainAdmin",
      "Effect": "Allow",
      "Action": ["codeartifact:*"],
      "Resource": "arn:aws:codeartifact:<region>:<account-id>:domain/<domain-name>"
    },
    {
      "Sid": "RepositoryAdmin",
      "Effect": "Allow",
      "Action": ["codeartifact:*"],
      "Resource": "arn:aws:codeartifact:<region>:<account-id>:repository/<domain-name>/*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name devops-admin \
  --policy-name codeartifact-admin \
  --policy-document file:///tmp/domain-admin-policy.json
```

### CI build consume policy

```bash
cat > /tmp/ci-consume-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Login",
      "Effect": "Allow",
      "Action": ["codeartifact:GetAuthorizationToken", "codeartifact:ReadFromRepository"],
      "Resource": "arn:aws:codeartifact:<region>:<account-id>:domain/<domain-name>"
    },
    {
      "Sid": "ReadPackages",
      "Effect": "Allow",
      "Action": [
        "codeartifact:ReadFromRepository",
        "codeartifact:GetPackageVersionAsset",
        "codeartifact:ListPackageVersionAssets",
        "codeartifact:DescribePackageVersion"
      ],
      "Resource": "arn:aws:codeartifact:<region>:<account-id>:repository/<domain-name>/<repository-name>/*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name ci-build \
  --policy-name codeartifact-consume \
  --policy-document file:///tmp/ci-consume-policy.json
```

### Release pipeline publish policy

```bash
cat > /tmp/release-publish-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Publish",
      "Effect": "Allow",
      "Action": [
        "codeartifact:PublishPackageVersion",
        "codeartifact:PutPackageMetadata",
        "codeartifact:UpdatePackageVersionsStatus",
        "codeartifact:ReadFromRepository"
      ],
      "Resource": "arn:aws:codeartifact:<region>:<account-id>:repository/<domain-name>/<repository-name>/*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name release-pipeline \
  --policy-name codeartifact-publish \
  --policy-document file:///tmp/release-publish-policy.json
```

### Repository permissions policy (alternative)

Instead of IAM role policies, apply a resource-based policy on the
repository itself:

```bash
aws codeartifact put-repository-permissions-policy \
  --domain <domain-name> \
  --repository <repository-name> \
  --policy-document file:///tmp/ci-consume-policy.json
```

The repository policy supplements the domain policy. IAM role policies
are recommended for scale.

## Step 6: Wire CI builds via `codeartifact login`

### npm

```bash
aws codeartifact login \
  --tool npm \
  --domain <domain-name> \
  --domain-owner <account-id> \
  --repository <repository-name>

# Updates ~/.npmrc with:
# registry=https://<domain-name>-<account-id>.d.codeartifact.<region>.amazonaws.com/npm/<repository-name>/
# always-auth=true
# //<domain-name>-<account-id>.d.codeartifact.<region>.amazonaws.com/npm/<repository-name>/:_authToken=<token>
```

### pip

```bash
aws codeartifact login \
  --tool pip \
  --domain <domain-name> \
  --domain-owner <account-id> \
  --repository <repository-name>

# Configures pip index-url in ~/.config/pip/pip.conf (Linux/macOS) or
# %APPDATA%\pip\pip.ini (Windows)
```

### Maven

```bash
aws codeartifact login \
  --tool mvn \
  --domain <domain-name> \
  --domain-owner <account-id> \
  --repository <repository-name>

# Updates ~/.m2/settings.xml with <server> credentials and <mirror> config
```

### NuGet

```bash
aws codeartifact login \
  --tool nuget \
  --domain <domain-name> \
  --domain-owner <account-id> \
  --repository <repository-name>

# Adds a package source to nuget.config
```

### Cargo / RubyGems / Swift (manual)

Cargo, RubyGems, and Swift have no native `codeartifact login` —
configure manually:

**Cargo** (`~/.cargo/config.toml`):
```toml
[registry]
default = "codeartifact"

[registries.codeartifact]
index = "sparse+https://<domain-name>-<account-id>.d.codeartifact.<region>.amazonaws.com/cargo/<repository-name>/"
token = "<auth-token>"
```

**RubyGems**:
```bash
gem sources --add https://aws:<auth-token>@<domain-name>-<account-id>.d.codeartifact.<region>.amazonaws.com/rubygems/<repository-name>/
```

**Swift** (`Package.swift`):
```swift
.package(
  url: "https://<domain-name>-<account-id>.d.codeartifact.<region>.amazonaws.com/swift/<repository-name>/",
  from: "1.0.0"
)
```

### Token refresh for CI

```bash
# Request token explicitly with max duration (12 hours = 43200 seconds)
TOKEN=$(aws codeartifact get-authorization-token \
  --domain <domain-name> \
  --domain-owner <account-id> \
  --duration-seconds 43200 \
  --query authorizationToken --output text)

# Use token in subsequent calls
```

## Step 7: Cross-account domain sharing via RAM

### Option A: Domain permissions policy (one-off)

```bash
cat > /tmp/domain-share-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ConsumerAccountRead",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::<consumer-account-id>:root"
      },
      "Action": [
        "codeartifact:DescribeDomain",
        "codeartifact:DescribeRepository",
        "codeartifact:GetAuthorizationToken",
        "codeartifact:ReadFromRepository",
        "codeartifact:ListRepositoriesInDomain"
      ],
      "Resource": "arn:aws:codeartifact:<region>:<account-id>:domain/<domain-name>"
    }
  ]
}
EOF

# Capture current revision (for concurrent-update safety)
REVISION=$(aws codeartifact get-domain-permissions-policy \
  --domain <domain-name> \
  --query 'policy.revision' --output text 2>/dev/null || echo "")

aws codeartifact put-domain-permissions-policy \
  --domain <domain-name> \
  --domain-owner <account-id> \
  ${REVISION:+--policy-revision ${REVISION}} \
  --policy-document file:///tmp/domain-share-policy.json
```

### Option B: RAM resource share (Organizations / multi-account)

```bash
aws ram create-resource-share \
  --name codeartifact-shared-domain \
  --principals arn:aws:iam::<consumer-account-id>:root \
  --resource-arns arn:aws:codeartifact:<region>:<account-id>:domain/<domain-name>

# Or share with an entire OU
aws ram create-resource-share \
  --name codeartifact-shared-domain \
  --principals arn:aws:organizations::<account-id>:ou/o-<org-id>/ou-<ou-id> \
  --resource-arns arn:aws:codeartifact:<region>:<account-id>:domain/<domain-name>
```

### Consumer account IAM

In the consumer account, grant principals access to the shared domain:

```bash
cat > /tmp/consumer-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "codeartifact:GetAuthorizationToken",
        "codeartifact:ReadFromRepository",
        "codeartifact:DescribeRepository",
        "codeartifact:ListRepositoriesInDomain"
      ],
      "Resource": [
        "arn:aws:codeartifact:<region>:<owner-account-id>:domain/<domain-name>",
        "arn:aws:codeartifact:<region>:<owner-account-id>:repository/<domain-name>/*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name consumer-ci-build \
  --policy-name codeartifact-shared-consume \
  --policy-document file:///tmp/consumer-policy.json
```

## Step 8: Package ingestion via `copy-package-versions`

```bash
# Single version
aws codeartifact copy-package-versions \
  --domain <domain-name> \
  --repository <repository-name> \
  --source-repository <upstream-repo> \
  --format npm \
  --package lodash \
  --versions 4.17.21

# Batch (up to 100 versions)
aws codeartifact copy-package-versions \
  --domain <domain-name> \
  --repository <repository-name> \
  --source-repository <upstream-repo> \
  --format npm \
  --package lodash \
  --versions 4.17.21 4.17.20 4.17.19
```

## Step 9: Lifecycle policy (CloudFormation)

```yaml
Type: AWS::CodeArtifact::Repository
Properties:
  DomainName: <domain-name>
  RepositoryName: <repository-name>
  LifecyclePolicy: |
    {
      "rules": [
        {
          "rulePriority": 1,
          "description": "Retain last 100 versions per package",
          "actions": [{"type": "retain", "count": 100}],
          "selection": {
            "tagStatus": "any",
            "countType": "versions",
            "countNumber": 100
          }
        }
      ]
    }
```

## Step 10: Final verification

```bash
# Domain
aws codeartifact describe-domain --domain <domain-name>

# Repository
aws codeartifact describe-repository --domain <domain-name> --repository <repository-name>

# All repositories in domain
aws codeartifact list-repositories-in-domain --domain <domain-name>

# External connections
aws codeartifact describe-repository --domain <domain-name> \
  --repository <repository-name> --query 'repository.externalConnections'

# Repository endpoint URL
aws codeartifact get-repository-endpoint \
  --domain <domain-name> \
  --repository <repository-name> \
  --format npm

# Packages in repository
aws codeartifact list-packages --domain <domain-name> --repository <repository-name>

# Smoke test: login and install a package
aws codeartifact login --tool npm \
  --domain <domain-name> \
  --domain-owner <account-id> \
  --repository <repository-name>
npm install lodash
```

## Terraform equivalents

```hcl
# 1. Domain
resource "aws_codeartifact_domain" "shared" {
  domain_name    = "shared"
  encryption_key = aws_kms_key.codeartifact.arn
}

# 2. Repository
resource "aws_codeartifact_repository" "shared_npm" {
  domain       = aws_codeartifact_domain.shared.domain_name
  repository   = "shared-npm"
  description  = "Shared npm packages"
  upstream {
    repository_name = aws_codeartifact_repository.shared_internal.name
  }
}

# 3. External connection
resource "aws_codeartifact_repository" "public_npmjs" {
  domain       = aws_codeartifact_domain.shared.domain_name
  repository   = "public-npmjs"
  external_connections {
    external_connection_name = "public:npmjs"
  }
}

# 4. Cross-account via RAM
resource "aws_ram_resource_share" "codeartifact" {
  name                      = "codeartifact-shared-domain"
  allow_external_principals = true
}

resource "aws_ram_principal_association" "consumer" {
  resource_share_arn = aws_ram_resource_share.codeartifact.arn
  principal          = "arn:aws:iam::<consumer-account-id>:root"
}

resource "aws_ram_resource_association" "domain" {
  resource_share_arn = aws_ram_resource_share.codeartifact.arn
  resource_arn       = aws_codeartifact_domain.shared.arn
}
```

## Cleanup

```bash
# Delete repository (must have no packages OR --allow-keep)
aws codeartifact delete-repository \
  --domain <domain-name> \
  --repository <repository-name>

# Delete domain (must have no repositories)
aws codeartifact delete-domain --domain <domain-name>

# Detach RAM resource share
aws ram delete-resource-share --resource-share-arn <ram-arn>

# DO NOT delete IAM policies until repositories are confirmed deleted
```
