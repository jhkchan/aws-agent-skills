---
name: codeartifact-domain-deployer
description: >-
  Provisions AWS CodeArtifact domains with production defaults: domain
  creation (create-domain), repository creation within a domain
  (create-repository), upstream repository configuration (npm, pip,
  maven, nuget), external connection cascade (npmjs.com, pypi.org,
  mavencentral, nuget.org), package ingest via publish/copy-package,
  package consumption via authorization token (aws codeartifact login,
  12-hour expiry), repository policy (cross-account read/write),
  domain owner vs repository admin separation, asset retention and
  lifecycle policy, package version immutability, VPC interface
  endpoint for private access, KMS encryption (customer managed key),
  CloudWatch metrics (DownloadPackageVersion, PublishPackageVersion).
  Emits a READY_TO_DEPLOY checklist with verification commands. Use
  when creating a CodeArtifact domain, configuring upstream/external
  connection cascade for dependency resolution, setting up package
  consumption auth tokens, sharing repositories cross-account, or
  enabling private VPC access. Triggers: codeartifact domain, codeartifact
  external connection, codeartifact upstream cascade, codeartifact login,
  codeartifact authorization token, codeartifact VPC endpoint, codeartifact
  KMS encryption, codeartifact repository policy, codeartifact lifecycle
  policy, codeartifact package immutability, codeartifact cross-account.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with codeartifact,
  iam, kms, ec2 (VPC endpoint), and sts access. Works with Terraform
  aws_codeartifact_domain / aws_codeartifact_repository /
  aws_codeartifact_domain_permissions_policy resources, CloudFormation
  AWS::CodeArtifact::Domain / AWS::CodeArtifact::Repository templates,
  and the CodeArtifact login CLI for npm / pip / maven / nuget.
keywords:
  - aws
  - codeartifact
  - domain
  - devtools
  - cloudops
  - deploy
  - provisioning
  - upstream
  - external-connection
  - authorization-token
  - kms
  - vpc-endpoint
  - lifecycle
  - immutability
  - cross-account
  - repository-policy
  - package-registry
tags:
  - aws
  - codeartifact
  - domain
  - devtools
  - cloudops
  - deploy
  - provisioning
  - upstream
  - external-connection
  - kms
  - vpc-endpoint
  - lifecycle
  - cross-account
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: DevTools
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - codeartifact
    - domain
    - devtools
    - cloudops
    - deploy
    - provisioning
    - upstream
    - external-connection
    - kms
    - vpc-endpoint
    - lifecycle
    - cross-account
  dependencies:
    - aws-orchestrator
  keywords:
    - codeartifact domain
    - codeartifact external connection
    - codeartifact upstream cascade
    - codeartifact login
    - codeartifact authorization token
    - codeartifact vpc endpoint
    - codeartifact kms encryption
    - codeartifact repository policy
    - codeartifact lifecycle policy
    - codeartifact package immutability
    - codeartifact cross-account
  when_to_use: >-
    Invoke when the user wants to create a CodeArtifact domain, configure
    the upstream and external-connection cascade for dependency resolution,
    set up package consumption authorization tokens (aws codeartifact login),
    share repositories cross-account via repository policy, enable private
    access via VPC interface endpoint, configure KMS encryption, set
    lifecycle/retention policies, or enforce package version immutability.
    Do NOT invoke for CodeArtifact repository-only operations without domain
    context (use codeartifact-repository-deployer), plain S3-backed package
    storage, or GitHub Packages (separate service).
---

# CodeArtifact Domain Deployer

An AWS CloudOps agent skill that provisions AWS CodeArtifact domains
with correct production defaults. The skill walks the domain-as-IAM-
boundary model, the upstream and external-connection cascade for
dependency resolution, authorization token lifecycle (12-hour expiry
via `aws codeartifact login`), cross-account repository policy,
VPC interface endpoint for private access, KMS encryption, lifecycle
policy, and package version immutability, captures governance and
dependency-resolution decisions, explains why each default matters,
and emits a READY_TO_DEPLOY checklist with copy-pasteable verification
commands.

## Activation keywords

codeartifact domain, codeartifact external connection, codeartifact
upstream cascade, codeartifact login, codeartifact authorization token,
codeartifact VPC endpoint, codeartifact KMS encryption, codeartifact
repository policy, codeartifact lifecycle policy, codeartifact package
immutability, codeartifact cross-account.

## STRICT output contract

When this skill is invoked with a CodeArtifact-domain-provisioning
request (create a domain, configure upstream/external-connection cascade,
set up auth tokens, share cross-account, enable VPC endpoint, configure
KMS, set lifecycle, enforce immutability, or a partial configuration),
the agent MUST respond with the READY_TO_DEPLOY checklist defined in
the "Output format" section using the literal all-caps labels
`CODEARTIFACT_DOMAIN:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Domain as IAM boundary | Core domain model |
| Step 2 — Repository creation within domain | Repository setup |
| Step 3 — Upstream repository cascade | Dependency resolution chain |
| Step 4 — External connection (public registry) | npmjs.com, pypi.org, etc. |
| Step 5 — Authorization token (aws codeartifact login) | Package consumption auth |
| Step 6 — Package ingest (publish / copy-package) | Publishing packages |
| Step 7 — Cross-account repository policy | Sharing repositories |
| Step 8 — VPC interface endpoint (private access) | Network isolation |
| Step 9 — KMS encryption | Encryption at rest |
| Step 10 — Lifecycle policy and immutability | Retention governance |
| Step 11 — CloudWatch metrics | Monitoring |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/upstream-cascade-and-auth-tokens.md | Upstream + auth detail |
| references/encryption-vpc-endpoint-and-metrics.md | KMS + VPCe + metrics |

## Mindset

**One-line takeaway:** The CodeArtifact domain is the IAM and
encryption boundary. Every repository lives inside a domain. The
upstream and external-connection cascade determines how package
dependencies are resolved — a package not found locally cascades
through the upstream chain to public registries. The authorization
token from `aws codeartifact login` expires every 12 hours and MUST
be refreshed by CI/CD pipelines.

Three misconceptions dominate CodeArtifact domain misdesign at
provisioning time:

- **"The repository is the boundary."** It is NOT. The domain is the
  boundary. The domain owns the KMS encryption key, the domain
  permissions policy controls who can administer it, and the domain
  owner account pays for all storage. Repositories within the domain
  inherit the domain's encryption and are governed by repository-level
  policies for read/write — but the domain is the immutable container.

- **"Upstream and external connection are the same thing."** They are
  NOT. An upstream repository is another CodeArtifact repository
  (internal or shared). An external connection is a link to a PUBLIC
  registry (npmjs.com, pypi.org, mavencentral, nuget.org). The cascade
  order matters: local repo first, then upstream repos in order, then
  external connection last. A package request traverses this chain
  until a match is found.

- **"The auth token is permanent."** It is NOT. The token from
  `aws codeartifact login` expires after 12 hours. CI/CD pipelines
  MUST regenerate it on every run (or at least every 12 hours). A
  common failure is a pipeline that caches the token and breaks
  silently after expiry.

## Configuration dependency graph (novel heuristic)

CodeArtifact domain configurations are NOT independent. The domain
must exist before repositories. External connections are domain-level
resources. Upstream chains must form a valid cascade. VPC endpoints
require DNS private hostnames. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Domain | KMS key (if encryption-key arn specified); caller has codeartifact:CreateDomain | domain encryption CANNOT be changed after creation — the KMS key is immutable | repository creation, external connections |
| Repository | Parent domain exists; caller has codeartifact:CreateRepository | repository domain association CANNOT be changed — a repo cannot move domains | upstream configuration, package publish/consume |
| Upstream repository | Repository exists; upstream repository exists in same domain or shared domain | upstream order matters — cascade traverses in list order | internal dependency resolution |
| External connection | Domain exists; only ONE external connection per external source per domain | external connection connects to public registry — cannot be scoped or filtered | public package resolution (npmjs.com, pypi.org, etc.) |
| Authorization token | Domain or repository exists; caller has codeartifact:GetAuthorizationToken | token expires after 12 hours — MUST be refreshed | package consumption (npm install, pip install, etc.) |
| Repository policy (cross-account) | Repository exists; target account ID known; caller has codeartifact:PutRepositoryPermissionsPolicy | policy CANNOT be set at domain level for repository access — must be per-repository | cross-account read/write to specific repositories |
| VPC interface endpoint | VPC exists; private DNS enabled for codeartifact.<region>.amazonaws.com | without private DNS, the endpoint does NOT intercept the default CodeArtifact hostname | private package access without internet gateway |
| KMS encryption | KMS CMK exists; domain being created (NOT updateable post-creation) | encryption CANNOT be changed after domain creation — default AWS-managed key vs CMK is a create-time decision | encryption-at-rest governance |
| Lifecycle policy | Repository exists; caller has codeartifact:PutLifecyclePolicy | lifecycle rules apply to future package versions — existing versions are NOT retroactively affected | automated package retention/cleanup |
| Package immutability | Domain exists; immutability enforced at domain level | published package versions CANNOT be overwritten or deleted (unless lifecycle policy removes them) | supply-chain integrity |

**The domain-is-the-boundary row is the one a baseline model misses.**
A model that treats the repository as the primary entity will try to
change encryption at the repo level (impossible), set domain-wide access
at the repo level (wrong scope), or forget that the domain owner pays
for all storage. The procedure below forces an explicit decision on
the domain boundary first.

**Cross-dependency gotchas:**
- The domain KMS key is immutable. If you create the domain with the
  default AWS-managed key, you CANNOT switch to a CMK later without
  recreating the domain and all repositories.
- External connections are domain-scoped, not repository-scoped. One
  external connection to npmjs.com serves ALL repositories in the
  domain that reference it as an upstream.
- Upstream cascade order determines resolution. If repo-A has upstreams
  [repo-B, ext:npmjs], a package not in repo-A is searched in repo-B
  first, then npmjs. Reversing the order changes behavior.
- The auth token is scoped to a domain (or a specific repository). A
  domain-scoped token grants access to ALL repositories in the domain.
  A repository-scoped token is more restrictive.

## Expert heuristic: the upstream and external-connection cascade

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

## Expert heuristic: the 12-hour authorization token

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

## Expert heuristic: domain owner vs repository admin

The domain owner account is the account that created the domain. This
account pays for all storage and data transfer. Repository admins can
be different accounts (via cross-account repository policies), but
they do NOT pay for storage — the domain owner does.

```text
Account topology:
  Domain owner account (123456789012)
    ├── Created the domain → owns it → pays for ALL storage
    ├── Can set domain permissions policy (who can create repos)
    └── Can delete the domain (destroys ALL repos)

  Repository admin account (999999999999)
    ├── Has repository policy granting codeartifact:ReadFromRepository
    ├── Can consume packages from the repository
    └── Does NOT pay for storage (domain owner pays)

Cross-account sharing flow:
  1. Domain owner creates domain + repository
  2. Domain owner puts repository policy granting access to account 999999999999
  3. Consumer account uses `aws codeartifact login` with the domain owner's
     domain-owner ID to get an auth token
  4. Consumer installs packages (npm install, pip install)
```

**Key implication:** the domain owner is the cost center. If multiple
teams share a domain, the domain owner account bears all storage costs.
Plan cost allocation accordingly (tags, billing alerts).

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Domain name decided | Domain names are immutable identifiers | Confirm domain name (unique per account per region) |
| KMS key ARN (if custom encryption) | Encryption key is immutable at domain creation | `aws kms describe-key --key-id <key-id>` |
| Package format identified (npm, pip, maven, nuget) | Determines external connection and login tool | Confirm format(s) needed |
| External connection source (if consuming public packages) | External connection must exist in the domain | `aws codeartifact list-external-connections` |
| Target account ID (if cross-account repository policy) | Repository policy needs the consumer account ID | `aws sts get-caller-identity` (consumer account) |
| VPC ID and subnet (if VPC interface endpoint) | VPC endpoint needs a VPC and subnet | `aws ec2 describe-vpcs --vpc-ids <vpc-id>` |
| IAM permissions (codeartifact:CreateDomain, CreateRepository) | Caller must have permissions | `aws iam get-user` + check attached policies |
| CI/CD token refresh strategy | Auth token expires every 12 hours | Confirm pipeline can run login per build |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Domain as IAM boundary

The CodeArtifact domain is the top-level container. It owns the
encryption key, the domain permissions policy, and all repositories
within it. The domain cannot be renamed or moved — it is immutable.

| Property | Domain-level | Repository-level |
|---|---|---|
| KMS encryption key | Owned by domain (immutable at creation) | Inherited from domain |
| Permissions policy | Domain permissions policy (who can create/manage repos) | Repository policy (who can read/write packages) |
| Storage cost | Borne by domain owner account | N/A (domain owner pays) |
| External connections | Domain-scoped (one per public registry) | Referenced as upstream |
| Lifecycle policy | N/A | Per-repository |
| Deletion | Deletes ALL repositories and packages | Deletes one repo and its packages |

**Create a domain:**

```bash
# Domain with default AWS-managed encryption key
aws codeartifact create-domain \
  --domain my-domain \
  --region us-east-1

# Domain with custom KMS CMK (IMMUTABLE — cannot change later)
aws codeartifact create-domain \
  --domain my-domain \
  --encryption-key arn:aws:kms:us-east-1:123456789012:key/abcd1234-... \
  --region us-east-1
```

**Domain permissions policy (controls who can administer the domain):**

```bash
aws codeartifact put-domain-permissions-policy \
  --domain my-domain \
  --policy-document file://domain-policy.json \
  --region us-east-1
```

Where `domain-policy.json` grants domain administration to specific
principals.

## Step 2 — Repository creation within domain

Repositories are created within a domain. Each repository has a
package format (npm, pip, maven, nuget, etc.) and can have upstreams.

```bash
aws codeartifact create-repository \
  --domain my-domain \
  --repository my-team-packages \
  --description "Internal npm packages for my team" \
  --region us-east-1
```

**Repository description** is mutable. **Repository name** is immutable.

## Step 3 — Upstream repository cascade

Upstream repositories form the dependency resolution chain. When a
package is requested from a repository, CodeArtifact searches the
local repository first, then traverses upstreams in order.

```bash
# Set upstreams (order matters — first match wins)
aws codeartifact update-repository \
  --domain my-domain \
  --repository my-team-packages \
  --upstreams repository=shared-team-packages \
  --upstreams repository=company-approved-packages \
  --region us-east-1
```

**Cascade order is a security control.** Internal repositories should
come before external connections to prevent dependency confusion
attacks.

## Step 4 — External connection (public registry)

External connections link the domain to a PUBLIC package registry.
They are created at the DOMAIN level and referenced by repositories
as upstreams.

```bash
# Check available external connections
aws codeartifact list-external-connections \
  --region us-east-1

# Common external connections:
#   npmjs         → npmjs.com
#   pypi          → pypi.org
#   mavencentral  → search.maven.org
#   nuget-org     → nuget.org
```

External connections do NOT require creation — they are pre-provisioned
by AWS. You reference them as an upstream:

```bash
# Add external connection as the LAST upstream (after internal repos)
aws codeartifact update-repository \
  --domain my-domain \
  --repository my-team-packages \
  --upstreams repository=shared-team-packages \
  --upstreams external-connection=npmjs \
  --region us-east-1
```

**Key rule:** only ONE external connection per public source per
domain. You cannot have two npmjs connections in the same domain.

## Step 5 — Authorization token (aws codeartifact login)

Package consumption requires an authorization token. The `aws
codeartifact login` command generates a token (valid for 12 hours)
and configures the package manager.

```bash
# npm login (writes .npmrc)
aws codeartifact login \
  --tool npm \
  --domain my-domain \
  --domain-owner 123456789012 \
  --repository my-team-packages \
  --region us-east-1

# pip login (writes pip.conf under codeartifact directory)
aws codeartifact login \
  --tool pip \
  --domain my-domain \
  --domain-owner 123456789012 \
  --repository my-team-packages \
  --region us-east-1

# Alternative: generate token via API (for CI/CD)
TOKEN=$(aws codeartifact get-authorization-token \
  --domain my-domain \
  --domain-owner 123456789012 \
  --query authorizationToken --output text \
  --region us-east-1)
# Token expires in 12 hours — MUST be refreshed
```

**Critical:** the token expires after 12 hours. CI/CD pipelines MUST
run `aws codeartifact login` (or call `get-authorization-token`) on
every build. Caching the token across runs causes silent auth failures.

## Step 6 — Package ingest (publish / copy-package)

Packages can be published directly (npm publish, twine upload) or
copied from upstream repositories.

**Direct publish (npm):**

```bash
# After aws codeartifact login --tool npm ...
cd my-package/
npm publish
```

**Copy from upstream (ingest from public without consuming in CI):**

```bash
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

**Package version immutability:** once a package version is published,
it CANNOT be overwritten. A new version number is required for updates.
This is a supply-chain integrity guarantee.

## Step 7 — Cross-account repository policy

Repository policies grant cross-account access to specific repositories.
The domain owner account sets the policy; the consumer account uses the
token to access.

```bash
# Domain owner grants read access to consumer account 999999999999
aws codeartifact put-repository-permissions-policy \
  --domain my-domain \
  --repository my-team-packages \
  --policy-revision 1 \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::999999999999:root"
        },
        "Action": [
          "codeartifact:ReadFromRepository",
          "codeartifact:GetAuthorizationToken",
          "codeartifact:GetRepositoryEndpoint"
        ],
        "Resource": "*"
      }
    ]
  }' \
  --region us-east-1
```

**Consumer account access flow:**

```bash
# Consumer account gets auth token from the DOMAIN OWNER's domain
aws codeartifact login \
  --tool npm \
  --domain my-domain \
  --domain-owner 123456789012 \
  --repository my-team-packages \
  --region us-east-1
# Consumer can now npm install from the repository
```

**Key distinction:** domain permissions policy controls who can
administer the domain (create/delete repos). Repository policy controls
who can read/write packages in a specific repository. These are
separate scopes.

## Step 8 — VPC interface endpoint (private access)

By default, CodeArtifact is accessed over the public internet. For
network isolation, a VPC interface endpoint routes traffic through
AWS PrivateLink.

```bash
# Create VPC interface endpoint for CodeArtifact
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.codeartifact.repositories \
  --subnet-ids subnet-aaa111 subnet-bbb222 \
  --security-group-ids sg-priv-1 \
  --private-dns-enabled \
  --region us-east-1

# Also create endpoint for the API (codeartifact.api)
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.codeartifact.api \
  --subnet-ids subnet-aaa111 subnet-bbb222 \
  --security-group-ids sg-priv-1 \
  --private-dns-enabled \
  --region us-east-1
```

**Critical:** `--private-dns-enabled` is REQUIRED for the endpoint to
intercept the default CodeArtifact hostname. Without it, the package
manager resolves to the public IP. Two endpoints are needed: one for
the API (codeartifact.api) and one for repositories
(codeartifact.repositories).

## Step 9 — KMS encryption

CodeArtifact encrypts all data at rest. The encryption key is set at
DOMAIN CREATION and is IMMUTABLE.

| Option | Description | When to use |
|---|---|---|
| Default (AWS-managed) | CodeArtifact uses an AWS-managed KMS key | Simple setups, no key rotation control needed |
| Customer-managed key (CMK) | Domain created with a specific KMS CMK ARN | Enterprise compliance, key rotation control, cross-account key access |

```bash
# Create a CMK for CodeArtifact
KMS_KEY_ID=$(aws kms create-key \
  --description "CodeArtifact domain encryption key" \
  --query 'KeyMetadata.KeyId' --output text \
  --region us-east-1)

# Create domain with CMK (IMMUTABLE — cannot change later)
aws codeartifact create-domain \
  --domain my-domain \
  --encryption-key arn:aws:kms:us-east-1:123456789012:key/$KMS_KEY_ID \
  --region us-east-1
```

**Key policy for the CMK** must allow CodeArtifact service to use the
key (kms:Encrypt, kms:Decrypt, kms:ReEncrypt, kms:GenerateDataKey,
kms:DescribeKey).

## Step 10 — Lifecycle policy and immutability

Lifecycle policies automate package version retention. Package versions
are immutable once published — lifecycle policies are the only way to
remove old versions.

```bash
# Apply lifecycle policy (retain last 50 versions, delete older)
aws codeartifact put-lifecycle-configuration \
  --domain my-domain \
  --repository my-team-packages \
  --lifecycle-configuration '{
    "rules": [
      {
        "rulePriority": 1,
        "description": "Keep last 50 versions",
        "actions": [
          {
            "type": "retention",
            "maxVersions": 50
          }
        ]
      }
    ]
  }' \
  --region us-east-1
```

**Immutability guarantee:** published package versions CANNOT be
overwritten, modified, or selectively deleted (only lifecycle policies
remove them based on rules). This prevents supply-chain tampering.

## Step 11 — CloudWatch metrics

CodeArtifact emits CloudWatch metrics for monitoring:

| Metric | Description |
|---|---|
| `DownloadPackageVersion` | Number of package version downloads |
| `PublishPackageVersion` | Number of package version publishes |
| `AssetSizeBytes` | Storage consumed by assets |

```bash
# Monitor download/publish rates
aws cloudwatch get-metric-statistics \
  --namespace AWS/CodeArtifact \
  --metric-name PublishPackageVersion \
  --start-time 2026-08-01T00:00:00Z \
  --end-time 2026-08-11T00:00:00Z \
  --period 86400 \
  --statistics Sum \
  --dimensions Name=DomainName,Value=my-domain \
  --region us-east-1
```

Set CloudWatch alarms for abnormal publish/download patterns (security
monitoring for supply-chain anomalies).

## Step 12 — Recent features

**Recent AWS features (2023-2026):**

- **Swift package support (2023-2024):** CodeArtifact added Swift
  package format support, enabling iOS/macOS development teams to use
  CodeArtifact as a package registry.

- **Cargo package support (2023-2024):** Rust Cargo package format
  support was added, rounding out the major ecosystem coverage.

- **Lifecycle policy GA (2023-2024):** Lifecycle policies graduated
  from preview, enabling automated package version retention and
  cleanup to control storage costs.

- **Cross-region replication improvements (2024-2025):** Enhanced
  cross-region package replication for DR scenarios, reducing latency
  for geographically distributed development teams.

- **VPC endpoint private DNS enhancements (2024-2025):** Improved
  private DNS resolution for CodeArtifact VPC endpoints, simplifying
  network isolation setups.

- **Package origin controls (2024-2025):** Package origin controls
  allow administrators to restrict whether a package can be published
  directly, pulled from upstream, or both — a key supply-chain security
  feature preventing dependency confusion.

- **Terraform provider maturity (2024-2025):** The Terraform provider
  added full support for lifecycle configurations, package origin
  controls, and domain permissions policies.

## NEVER do these things

1. **NEVER create a domain without deciding on KMS encryption first.**
   The encryption key is IMMUTABLE at domain creation. If you start
   with the default AWS-managed key, you CANNOT switch to a CMK later
   without recreating the domain and all repositories.

2. **NEVER assume the authorization token is permanent.** The token
   from `aws codeartifact login` expires after 12 hours. CI/CD
   pipelines MUST regenerate it on every build. Caching the token
   causes silent auth failures after expiry.

3. **NEVER put external connections before internal upstreams in the
   cascade.** The cascade order is a supply-chain security control.
   Internal repos must come before public registries to prevent
   dependency confusion attacks.

4. **NEVER confuse domain permissions policy with repository policy.**
   Domain permissions policy controls who can administer the domain
   (create/delete repos). Repository policy controls who can read/write
   packages in a specific repo. These are separate scopes and must be
   configured independently.

5. **NEVER create a VPC endpoint without private DNS enabled.** Without
   `--private-dns-enabled`, the endpoint does NOT intercept the default
   CodeArtifact hostname. Package managers will resolve to the public
   IP, bypassing the endpoint.

6. **NEVER forget that TWO VPC endpoints are needed.** CodeArtifact
   requires separate endpoints for the API (codeartifact.api) and
   repositories (codeartifact.repositories). Creating only one breaks
   either login or package download.

7. **NEVER assume package versions can be overwritten.** Published
   versions are IMMUTABLE. A new version number is required for every
   change. Use lifecycle policies to clean up old versions — manual
   deletion of specific versions is not supported (only lifecycle
   rules remove them).

8. **NEVER assume the domain owner and repository admin are the same
   account.** The domain owner account pays for ALL storage. Repository
   admins (potentially different accounts) do not pay. Plan cost
   allocation and billing alerts on the domain owner account.

9. **NEVER create multiple external connections for the same public
   registry in one domain.** Only ONE external connection per public
   source per domain is allowed. Duplicate attempts fail.

10. **NEVER assume lifecycle policies apply retroactively.** Lifecycle
    rules apply to FUTURE package versions. Existing versions are NOT
    affected until the policy evaluates them. Plan the transition
    carefully.

## Output format

```text
CODEARTIFACT_DOMAIN: <domain-name> (<domain-owner-account>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Domain: <domain-name> — encryption: <aws-managed | CMK <key-arn>>
  [✓|✗] Repository: <repo-name> (format: <npm|pip|maven|nuget>)
  [✓|✗] Upstream cascade: <repo-1> → <repo-2> → <external-connection>
  [✓|✗] External connection: <npmjs|pypi|mavencentral|nuget-org> (domain-scoped)
  [✓|✗] Authorization token: aws codeartifact login (12-hour expiry — CI refresh required)
  [✓|✗] Package ingest: <publish | copy-package> — immutability enforced
  [✓|✗] Cross-account repository policy: <account-id> (read | read+write)
  [✓|✗] VPC endpoint: <vpce-id> (api + repositories, private DNS enabled)
  [✓|✗] KMS encryption: <aws-managed | CMK> — immutable at domain creation
  [✓|✗] Lifecycle policy: <retain N versions | delete after N days>
  [✓|✗] Package immutability: enforced (published versions cannot be overwritten)
  [✓|✗] CloudWatch metrics: DownloadPackageVersion, PublishPackageVersion
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws codeartifact describe-domain --domain <domain-name> --region <region>
  aws codeartifact describe-repository --domain <domain-name> --repository <repo-name> --region <region>
  aws codeartifact list-repositories-in-domain --domain <domain-name> --region <region>
```

### Worked example — npm domain with external connection and cross-account access

```text
CODEARTIFACT_DOMAIN: my-domain (123456789012)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Domain: my-domain — encryption: CMK arn:aws:kms:us-east-1:123456789012:key/abcd1234
  [✓] Repository: my-team-packages (format: npm)
  [✓] Upstream cascade: my-team-packages → shared-team-packages → ext:npmjs
  [✓] External connection: npmjs (domain-scoped)
  [✓] Authorization token: aws codeartifact login (12-hour expiry — CI refresh required)
  [✓] Package ingest: npm publish — immutability enforced
  [✓] Cross-account repository policy: 999999999999 (read)
  [✓] VPC endpoint: vpce-aaa111 (api + repositories, private DNS enabled)
  [✓] KMS encryption: CMK — immutable at domain creation
  [✓] Lifecycle policy: retain last 50 versions
  [✓] Package immutability: enforced (published versions cannot be overwritten)
  [✓] CloudWatch metrics: DownloadPackageVersion, PublishPackageVersion
  [✓] Tags: Environment=production, Team=platform
VERIFICATION_COMMANDS:
  aws codeartifact describe-domain --domain my-domain --region us-east-1
  aws codeartifact describe-repository --domain my-domain --repository my-team-packages --region us-east-1
  aws codeartifact list-repositories-in-domain --domain my-domain --region us-east-1
```

## Error handling

### Domain creation fails with encryption key error
- The KMS key ARN is invalid or the caller does not have
  `kms:CreateGrant` on the key. Verify the key exists and the key
  policy allows CodeArtifact to use it. The encryption key is immutable
  — you cannot change it after domain creation.

### Auth token expired in CI/CD
- The token from `aws codeartifact login` expires after 12 hours. The
  pipeline MUST run `login` before every build (or call
  `get-authorization-token`). Check the pipeline logs for 401/403
  errors that start appearing 12 hours after the last successful login.

### Cross-account access denied
- The repository policy does not grant the consumer account access, or
  the consumer is using the wrong `--domain-owner` value. The consumer
  must specify the DOMAIN OWNER account ID in the `login` command.
  Verify the repository policy includes the consumer account.

### Package not found despite upstream configured
- The upstream cascade order may be wrong, or the external connection
  is not set. Verify the upstream chain with `describe-repository` and
  confirm the external connection exists in the domain. Also verify
  the package format matches (an npm upstream will not resolve pip
  packages).

### VPC endpoint not intercepting traffic
- Private DNS is not enabled. Recreate the endpoint with
  `--private-dns-enabled`, or verify that the VPC's DNS resolution
  supports private hosted zones. Also verify BOTH endpoints (api and
  repositories) exist.

## Domain

AWS CloudOps / AWS CodeArtifact Domain Provisioning & Package Registry
Governance.

## AWS documentation

- **CodeArtifact domains** — https://docs.aws.amazon.com/codeartifact/latest/ug/domains.html
- **Domain creation** — https://docs.aws.amazon.com/codeartifact/latest/ug/create-domain.html
- **Upstream repositories** — https://docs.aws.amazon.com/codeartifact/latest/ug/repo-upstream.html
- **External connections** — https://docs.aws.amazon.com/codeartifact/latest/ug/external-connection.html
- **Auth tokens and login** — https://docs.aws.amazon.com/codeartifact/latest/ug/using-private-npm-repo.html
- **Repository policies** — https://docs.aws.amazon.com/codeartifact/latest/ug/repo-policies.html
- **VPC endpoints** — https://docs.aws.amazon.com/codeartifact/latest/ug/vpc-endpoints.html
- **Lifecycle policies** — https://docs.aws.amazon.com/codeartifact/latest/ug/lifecycle-policies.html
- **CloudWatch metrics** — https://docs.aws.amazon.com/codeartifact/latest/ug/metrics.html
- **Package origin controls** — https://docs.aws.amazon.com/codeartifact/latest/ug/package-origin-controls.html
