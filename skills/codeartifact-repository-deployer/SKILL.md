---
name: codeartifact-repository-deployer
description: 'Provisions AWS CodeArtifact repositories: domain creation, repository creation across package formats (npm, pip, maven, nuget, cargo, rubygems, generic, swift), upstream repositories (public: npmjs, pypi, maven-central, nuget-org), external connections, package ingestion via copy-package, cross-account domain sharing via RAM, repository IAM policies (read/write/consume), codeartifact login CLI for npm/pip/maven, package versions, and lifecycle policies. Emits a READY_TO_DEPLOY checklist with every prerequisite verified. Use when creating a CodeArtifact domain or repository, configuring upstreams, sharing a domain across accounts, or wiring a package build to CodeArtifact. Triggers: codeartifact domain, codeartifact repository, npm pip maven nuget cargo rubygems swift repository, codeartifact upstream, codeartifact external connection, codeartifact login, codeartifact copy-package, codeartifact domain sharing, RAM codeartifact, codeartifact IAM policy.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with codeartifact, ram, iam, sts, and resourcegroupstaggingapi access. Works with Terraform aws_codeartifact_domain / aws_codeartifact_repository / aws_codeartifact_domain_permissions_policy resources, CloudFormation AWS::CodeArtifact::Domain / AWS::CodeArtifact::Repository, and the CodeArtifact login CLI for npm / pip / maven.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: DevTools
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, codeartifact, devtools, cloudops, deploy, package-repository, npm, pip, maven
  dependencies: aws-orchestrator
  keywords: aws, codeartifact, devtools, cloudops, deploy, provisioning, package-repository, npm, pip, maven, nuget, cargo, rubygems, swift, upstream, external-connection, domain-sharing, ram
  when_to_use: Invoke when the user wants to create a CodeArtifact domain or repository, configure upstream repositories (npmjs, pypi, maven-central, nuget-org), share a domain across AWS accounts via RAM, set repository permissions (read/write/consume), wire a CI build to CodeArtifact via the login CLI, or ingest packages from upstream. Do NOT invoke for plain S3-backed package storage, GitHub Packages (separate service), or for general artifact management outside CodeArtifact.
---

# CodeArtifact Repository Deployer

An AWS CloudOps agent skill that provisions AWS CodeArtifact domains and
repositories with correct production defaults — package-format-aware
configuration, upstream chaining, external connections, cross-account
domain sharing, and repository IAM. Emits a READY_TO_DEPLOY checklist
verifying every prerequisite.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the provisioning order matters | "Reasoning framework" |
| What to verify before provisioning | "Prerequisites" |
| The ordered provisioning steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Upstreams, external connections, domain sharing, IAM | "Deployment procedure" Steps 3-8 |
| Format-specific defaults | "Workload matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/deployment-cli-commands.md` |
| Upstream chaining, domain sharing, IAM, login CLI guide | `references/upstreams-and-cross-account-guide.md` |

## STRICT output contract

When this skill is invoked with a CodeArtifact provisioning request
(domain name, repository name, package format, upstreams, or a partial
existing configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in "Output format" using the literal
all-caps labels `REPOSITORY:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response.

### Required output structure

1. `REPOSITORY: <repository-arn-or-name>` — the CodeArtifact repository
   being provisioned.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING`.
3. `CHECKLIST:` followed by indented lines with status markers
   (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented `aws codeartifact ...`
   commands.

### FORBIDDEN output patterns

- **No prose preamble before `REPOSITORY:`** — the first non-empty line
  MUST be `REPOSITORY:`.
- **No markdown variants of labels** — write `VERDICT:`, not
  `**VERDICT:**`, `### Verdict`, `Verdict =`, or `` `VERDICT` ``.
- **No swapping verdict tokens** — exactly `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`. Not "ready", "missing", "BLOCKED", "OK".
- **No omitting `VERIFICATION_COMMANDS:`** — include even when
  PREREQUISITES_MISSING; the operator needs commands to verify gaps.
- **No extra sections after `VERIFICATION_COMMANDS:`** — the checklist
  block is the entire response. Put deeper explanation in `references/`.
- **No status marker drift** — use only `[✓]`, `[✗]`, `[OPTIONAL]`,
  `[INPUT NEEDED]`. Do not invent `[?]`, `[!]`, `[WARN]`, or emoji.

### Perfect example (copy the shape exactly)

```text
REPOSITORY: shared-npm
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Domain — shared (existing, owner 123456789012)
  [✓]      Repository — shared-npm
  [✓]      Format — npm
  [✓]      Upstream — shared-internal (internal npm mirror) + external:npmjs
  [✓]      External connection — public:npmjs (CodeArtifact managed)
  [✓]      Connection — arn:aws:codeartifact:us-east-1:123456789012:repository/shared/shared-npm
  [✓]      Domain owner IAM — arn:aws:iam::123456789012:role/devops-admin (codeartifact:* on domain)
  [✓]      Repository consume policy — arn:aws:iam::123456789012:role/ci-build (codeartifact:ReadFromRepository, codeartifact:GetPackageVersionAsset, codeartifact:GetAuthorizationToken)
  [✓]      Repository publish policy — arn:aws:iam::123456789012:role/release-pipeline (codeartifact:PublishPackageVersion, codeartifact:PutPackageMetadata, codeartifact:UpdatePackageVersionsStatus)
  [OPTIONAL] Cross-account domain share — none (single-account deployment)
  [OPTIONAL] Package ingestion — copy-package from upstream as needed
  [OPTIONAL] Lifecycle policy — retain last 100 versions per package
VERIFICATION_COMMANDS:
  aws codeartifact describe-domain --domain shared --domain-owner 123456789012
  aws codeartifact describe-repository --domain shared --repository shared-npm
  aws codeartifact list-repositories-in-domain --domain shared
  aws codeartifact list-external-connections --domain shared
  aws codeartifact get-repository-endpoint --domain shared --repository shared-npm --format npm
  aws codeartifact login --tool npm --repository shared-npm --domain shared --domain-owner 123456789012
```

## Reasoning framework (why the provisioning order matters)

CodeArtifact provisioning has **dependency and ordering constraints**
that make the procedure non-trivial. Applying configurations in the
wrong order causes empty repositories, failed `npm install`, broken
cross-account shares, or packages that cannot be published:

1. **Domain FIRST, then repository** — a CodeArtifact repository MUST
   belong to a domain. The domain is the unit of sharing (via RAM),
   billing, and policy inheritance. Creating a repository without a
   parent domain is impossible.
2. **External connection BEFORE upstream** — an external connection
   (`public:npmjs`, `public:pypi`, `public:maven-central`,
   `public:nuget-org`, `public:cargo`, `public:rubygems`) is a
   CodeArtifact-managed bridge to a public registry. It is attached
   to a repository in the domain, not directly to the repository
   chain. Misordering creates a repository with no upstream.
3. **Upstream chain order matters** — a repository points at upstream
   repositories in priority order. Package resolution walks the chain
   left-to-right. A package published in an earlier upstream shadows
   a package with the same name in a later upstream. The order is
   `internal-mirror -> ... -> external-connection` (most-internal
   first).
4. **Domain sharing via RAM BEFORE consumer IAM** — to share a domain
   across accounts, the domain owner attaches a domain permissions
   policy granting `codeartifact:*` to the consumer account root.
   THEN the consumer account's IAM grants its principals
   `codeartifact:CreateRepository`, `ReadFromRepository`, etc.
5. **IAM is resource-scoped, not repository-scoped** — CodeArtifact
   IAM policies attach to the domain, not individual repositories.
   A repository policy is OPTIONAL and supplements the domain policy.
6. **`codeartifact login` requires an authorization token** — the
   `codeartifact login` CLI generates a short-lived (default 12-hour)
   authorization token via `GetAuthorizationToken`. The token must
   be exchanged for a per-format credential (npm: `.npmrc`, pip:
   `pip config`, maven: `settings.xml`). The caller IAM must allow
   `codeartifact:GetAuthorizationToken`.
7. **Package version immutability** — once a package version is
   published, it cannot be overwritten. `PublishPackageVersion` with
   the same version+revision is rejected. CI pipelines must use
   unique versions or `--revision` overrides.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **AWS account ID (domain owner)** | Domain ARN includes the owner account. Cross-account references must use the owner ID. | `aws sts get-caller-identity --query Account --output text` |
| **Domain exists OR is being created** | A repository cannot exist without a parent domain. | `aws codeartifact describe-domain --domain <name>` |
| **Domain owner IAM role** | Caller needs `codeartifact:CreateDomain`, `codeartifact:CreateRepository`, `codeartifact:AssociateExternalConnection`. | `aws sts get-caller-identity` |
| **External connection availability** | `public:npmjs` etc. are managed by CodeArtifact; availability is Region-dependent. | `aws codeartifact list-external-connections --domain <name>` |
| **KMS key (optional)** | CodeArtifact domains can be encrypted with a customer-managed KMS key. Default is AWS-owned. | `aws codeartifact describe-domain --domain <name> --query domain.encryptionKey` |
| **Cross-account consumer account ID** (if sharing) | The consumer account root ARN appears in the domain permissions policy. | `aws sts get-caller-identity` in consumer account |
| **Consumer IAM principal** (if cross-account) | Consumer account must grant its role `codeartifact:ReadFromRepository` etc. | `aws iam get-role --role-name <role>` in consumer account |
| **VPC endpoints** (if private network) | CodeArtifact interface VPC endpoints keep traffic off the public internet. | `aws ec2 describe-vpc-endpoints --filters service-name=codeartifact.<region>.amazonaws.com` |
| **IAM permissions for caller** | Caller needs `codeartifact:Create*`, `codeartifact:PutRepositoryPermissionsPolicy`, `ram:CreateResourceShare`. | `aws sts get-caller-identity` |

## Deployment procedure (apply in order)

### Step 1: Create (or reuse) the domain

A domain is the unit of organization, sharing, and policy inheritance.
Create the domain in the owner account:

```bash
aws codeartifact create-domain \
  --domain shared \
  --encryption-key arn:aws:kms:us-east-1:123456789012:key/<cmk-id>  # optional
```

Domain naming rules:

- Domain names are unique within an account + Region.
- Use a short, organization-wide name (`shared`, `companyname`), not
  a per-team name (per-team separation is at the repository level).
- Domain names cannot be renamed — choose carefully.

If the domain already exists, `describe-domain` returns the ARN
without error. Reusing a domain is the common case.

### Step 2: Create the repository

A repository holds packages of one or more formats. CodeArtifact
repositories are format-aware — the format is implied by the endpoint
used (`npm`, `pip`, `maven`, `nuget`, `cargo`, `rubygems`, `swift`,
`generic`).

```bash
aws codeartifact create-repository \
  --domain shared \
  --repository shared-npm \
  --description "Shared npm packages with npmjs public upstream" \
  --tags '[{"Key":"Environment","Value":"production"},{"Key":"Format","Value":"npm"}]'
```

Repository naming rules:

- Repository names are unique within a domain.
- Use a `<domain>-<format>` convention (`shared-npm`, `shared-pip`,
  `shared-maven`) to avoid collisions.
- Repositories can hold multiple formats in principle, but the
  standard pattern is one repository per format.

### Step 3: Configure external connections (public upstreams)

External connections are CodeArtifact-managed bridges to public
registries. Available external connections:

| External connection | Public registry |
|---|---|
| `public:npmjs` | npm (npmjs.com) |
| `public:pypi` | Python Package Index |
| `public:maven-central` | Maven Central |
| `public:maven-googleandroid` | Google Android Maven |
| `public:maven-gradleplugins` | Gradle plugins |
| `public:nuget-org` | NuGet Gallery |
| `public:cargo` | crates.io |
| `public:rubygems` | RubyGems |

Associate an external connection with a repository:

```bash
aws codeartifact associate-external-connection \
  --domain shared \
  --repository shared-npm \
  --external-connection public:npmjs
```

Once associated, the external connection appears in the repository's
`externalConnections` list. The repository can resolve packages from
the public registry without further configuration.

### Step 4: Configure upstream repositories (internal chaining)

Upstream repositories chain internal repos + external connections.
Resolution walks the chain left-to-right; the first match wins.

```bash
# shared-npm points at shared-internal (a curated internal mirror)
# which in turn points at the public:npmjs external connection
aws codeartifact update-repository \
  --domain shared \
  --repository shared-npm \
  --upstreams repository=shared-internal
```

For multi-hop chains:

```bash
aws codeartifact update-repository \
  --domain shared \
  --repository team-payments-npm \
  --upstreams repository=team-payments-internal,repository=shared-npm
```

Resolution order for `team-payments-npm`:
1. `team-payments-npm` itself (first-party packages)
2. `team-payments-internal` (curated internal mirror)
3. `shared-npm` (org-wide mirror)
4. `shared-internal` (org-wide curated)
5. `public:npmjs` (external)

**NEVER put an external connection upstream of an internal mirror.**
Public packages with the same name would shadow internal packages,
creating a supply-chain risk.

### Step 5: Configure repository IAM policies

CodeArtifact IAM is resource-scoped (the domain). A repository policy
is OPTIONAL and supplements the domain policy. Two patterns:

**Domain owner admin policy (apply to a DevOps admin role):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DomainAdmin",
      "Effect": "Allow",
      "Action": ["codeartifact:*"],
      "Resource": "arn:aws:codeartifact:us-east-1:123456789012:domain/shared"
    },
    {
      "Sid": "RepositoryAdmin",
      "Effect": "Allow",
      "Action": ["codeartifact:*"],
      "Resource": "arn:aws:codeartifact:us-east-1:123456789012:repository/shared/*"
    }
  ]
}
```

**CI build consume policy (apply to a CI role):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Login",
      "Effect": "Allow",
      "Action": ["codeartifact:GetAuthorizationToken", "codeartifact:ReadFromRepository"],
      "Resource": "arn:aws:codeartifact:us-east-1:123456789012:domain/shared"
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
      "Resource": "arn:aws:codeartifact:us-east-1:123456789012:repository/shared/shared-npm/*"
    }
  ]
}
```

**Release pipeline publish policy (apply to a release role):**

```json
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
      "Resource": "arn:aws:codeartifact:us-east-1:123456789012:repository/shared/shared-npm/*"
    }
  ]
}
```

Apply a repository policy via `put-repository-permissions-policy` or
attach the policy to the IAM role. The role-based pattern is
recommended (it scales across repositories).

### Step 6: Wire CI builds via the `codeartifact login` CLI

The `codeartifact login` CLI generates a short-lived authorization
token and configures the local package manager. The caller IAM must
allow `codeartifact:GetAuthorizationToken` and
`codeartifact:ReadFromRepository`.

**npm:**

```bash
aws codeartifact login \
  --tool npm \
  --domain shared \
  --domain-owner 123456789012 \
  --repository shared-npm

# Updates ~/.npmrc with:
# registry=https://shared-123456789012.d.codeartifact.us-east-1.amazonaws.com/npm/shared-npm/
# always-auth=true
# //shared-123456789012.d.codeartifact.us-east-1.amazonaws.com/npm/shared-npm/:_authToken=<token>
```

**pip:**

```bash
aws codeartifact login \
  --tool pip \
  --domain shared \
  --domain-owner 123456789012 \
  --repository shared-pip

# Configures pip index-url in ~/.config/pip/pip.conf or ~/.pip/pip.conf
```

**maven:**

```bash
aws codeartifact login \
  --tool mvn \
  --domain shared \
  --domain-owner 123456789012 \
  --repository shared-maven

# Updates ~/.m2/settings.xml with <server> credentials and mirror config
```

**nuget:**

```bash
aws codeartifact login \
  --tool nuget \
  --domain shared \
  --domain-owner 123456789012 \
  --repository shared-nuget

# Adds a package source to nuget.config
```

Token lifetime defaults to 12 hours (max 12 hours, configurable via
`--duration-seconds`). For CI pipelines, run `codeartifact login` at
the start of each build.

### Step 7: Cross-account domain sharing via RAM

To share a domain with another AWS account:

```bash
# Owner account — attach a domain permissions policy
cat > /tmp/domain-policy.json <<'EOF'
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
      "Resource": "arn:aws:codeartifact:us-east-1:123456789012:domain/shared"
    }
  ]
}
EOF

aws codeartifact put-domain-permissions-policy \
  --domain shared \
  --domain-owner 123456789012 \
  --policy-revision <current-revision> \
  --policy-document file:///tmp/domain-policy.json
```

Then the consumer account grants its principals
`codeartifact:GetAuthorizationToken` and
`codeartifact:ReadFromRepository` on the shared domain's ARN (owner
account ID embedded in the ARN).

**Cross-account RAM resource share (alternative):** for multi-account
sharing with Organizations or OUs, use a RAM resource share:

```bash
aws ram create-resource-share \
  --name codeartifact-shared-domain \
  --principals arn:aws:iam::<consumer-account-id>:root \
  --resource-arns arn:aws:codeartifact:us-east-1:123456789012:domain/shared
```

RAM-based sharing is the recommended pattern for Organizations-based
multi-account setups. Full reference in
`references/upstreams-and-cross-account-guide.md`.

### Step 8: Package ingestion via `copy-package`

To mirror a specific package version from upstream into the local
repository (e.g., to pin a version or air-gap):

```bash
aws codeartifact copy-package-versions \
  --domain shared \
  --repository shared-npm \
  --source-repository shared-upstream-mirror \
  --format npm \
  --package lodash \
  --versions 4.17.21
```

For air-gapped environments, `copy-package-versions` can pull from an
external-connection repository into an internal-only repository.

### Step 9: Configure lifecycle policies (optional)

Lifecycle policies auto-retain or delete old package versions, preventing
unbounded growth on high-velocity internal packages. Policies support
`retain` and `delete` actions scoped by version count or age. Configured
via CloudFormation / IaC; see `references/upstreams-and-cross-account-guide.md`
for the full policy JSON schema and CLI surface.

### Step 10: Tag, verify, and test the login

```bash
aws codeartifact list-repositories-in-domain --domain shared
aws codeartifact describe-repository --domain shared --repository shared-npm
aws codeartifact get-repository-endpoint \
  --domain shared --repository shared-npm --format npm
aws codeartifact list-packages --domain shared --repository shared-npm

# Smoke test: login and install a package
aws codeartifact login --tool npm \
  --domain shared --domain-owner 123456789012 --repository shared-npm
npm install lodash
```

## Edge-case handling

- **`npm install` returns `ENEEDAUTH` after `codeartifact login`:**
  the authorization token expired (default 12h), or the CI runner is
  not using the same IAM role that has `GetAuthorizationToken`. Run
  `codeartifact login` at the start of each build.
- **Repository resolves from public registry instead of internal:** the
  external connection is upstream of the internal mirror in the chain.
  Reorder upstreams — internal mirrors FIRST, external connection LAST.
- **Cross-account consumer gets `AccessDeniedException`:** the domain
  permissions policy in the owner account does not include the consumer
  account root, OR the consumer account's IAM role lacks
  `codeartifact:ReadFromRepository`. Verify both sides.
- **`PublishPackageVersion` rejected with `VersionConflictException`:**
  the package version already exists (versions are immutable). Bump the
  version or use `--revision` to override (rare).
- **External connection missing for Swift / Cargo:** Swift and Cargo
  external connections are not available in all Regions. Verify with
  `list-external-connections`; for unsupported Regions, use a
  `generic`-format repository and `copy-package-versions`.
- **Private network (no internet egress):** CodeArtifact interface VPC
  endpoints (`codeartifact.api` and `codeartifact.repositories`) keep
  client-to-CodeArtifact traffic private. External connections still
  fetch from the public registry server-side.
- **Token expiry in CI pipelines:** the `codeartifact login` token
  expires in 12h. Refresh via `codeartifact login` at the start of each
  build. Do NOT store long-lived tokens in CI secrets.
- **Domain ownership transfer:** CodeArtifact domains cannot be
  transferred between accounts. Migrate by creating a new domain and
  `copy-package-versions` from the old domain.

## Workload matrix

| Format | Repository convention | External connection | Login tool | Notes |
|---|---|---|---|---|
| npm (Node.js) | `<domain>-npm` | `public:npmjs` | `--tool npm` | Default recommendation; updates `~/.npmrc` |
| pip (Python) | `<domain>-pip` | `public:pypi` | `--tool pip` | Configures `pip.conf` |
| maven (Java) | `<domain>-maven` | `public:maven-central` | `--tool mvn` | Updates `~/.m2/settings.xml` |
| nuget (.NET) | `<domain>-nuget` | `public:nuget-org` | `--tool nuget` | Updates `nuget.config` |
| cargo (Rust) | `<domain>-cargo` | `public:cargo` | manual config | No native `--tool cargo` login |
| rubygems (Ruby) | `<domain>-rubygems` | `public:rubygems` | manual config | Configure `gem` source manually |
| swift | `<domain>-swift` | (Region-dependent) | manual config | Use SwiftPM `Package.swift` |
| generic | `<domain>-generic` | n/a | n/a | Any package format; manual publish |

## Recent AWS features (2024-2026)

- **CodeArtifact for Swift (2024-2025):** Swift package format support
  GA, with SwiftPM integration. External connection availability is
  Region-dependent; verify via `list-external-connections`.

- **`codeartifact login` for Maven and NuGet (2024-2025):** the login
  CLI now natively writes `~/.m2/settings.xml` (Maven) and
  `nuget.config` (NuGet), removing the need for manual XML editing.

- **Package version immutability enforcement (2024-2025):**
  `PublishPackageVersion` with an existing version+revision is
  explicitly rejected with `VersionConflictException`. Use unique
  versions or `--revision` overrides for legitimate re-publishes.

- **Domain permissions policy revision tracking (2024):**
  `put-domain-permissions-policy` accepts `--policy-revision` to
  prevent concurrent-update drift. Capture the current revision via
  `get-domain-permissions-policy` before updating.

- **Cross-account via RAM GA (2024-2025):** CodeArtifact domains can
  be shared via RAM resource shares, including with Organizations OUs.
  The legacy `put-domain-permissions-policy` flow remains but RAM is
  recommended for multi-account setups.

- **VPC endpoints for CodeArtifact (2024-2025):** interface VPC
  endpoints for both the API and repositories keep client traffic off
  the public internet. Required for air-gapped or regulated
  environments.

- **Lifecycle policies (2024-2025):** repository lifecycle policies
  support `retain` and `delete` actions scoped by version count or
  age. Useful for high-velocity internal packages.

- **`copy-package-versions` batch (2025):** batch ingestion from
  upstream supports up to 100 versions per call, simplifying air-gap
  mirroring workflows.

## NEVER (top 5 — full list in references)

- NEVER put an external connection (`public:npmjs`, `public:pypi`, etc.)
  upstream of an internal mirror in the chain. Public packages with the
  same name would shadow internal packages — a supply-chain attack
  vector. Order upstreams internal-first, external-last.
- NEVER grant `codeartifact:*` to broad principals (e.g., `*` or
  `Developers`). Scope repository consume and publish policies to the
  specific role and the specific repository ARN.
- NEVER create a repository without verifying the parent domain exists
  (or is being created in the same stack). The repository creation
  silently fails with `ResourceNotFoundException`.
- NEVER store long-lived `GetAuthorizationToken` output in CI secrets.
  Tokens expire in 12h; refresh via `codeartifact login` at the start
  of each build. Long-lived tokens in CI secrets are a credential
  leak risk.
- NEVER assume external connections are available in all Regions. Swift
  and Cargo external connections are Region-limited. Verify with
  `list-external-connections` before configuring upstreams.

## Expert heuristic — designing domains, repositories, and upstreams

- **One domain per organization.** Domains are the unit of sharing and
  billing. Multi-domain orgs fragment governance. Use
  `<companyname>` or `shared`.
- **One repository per format.** `shared-npm`, `shared-pip`,
  `shared-maven` keeps format-specific tooling isolated.
- **Upstream chain: internal-first, external-last.** The order is
  `team-internal -> org-shared -> external-connection`. This catches
  supply-chain attacks (a public package with the same name as an
  internal one resolves to the internal version).
- **External connection per repository.** Associate
  `public:npmjs` with `shared-npm`, not with the org-wide repo
  directly. This lets each format's external connection be removed
  independently if a public registry is compromised.
- **Cross-account via RAM, not policy-only.** RAM resource shares
  integrate with Organizations and OU-based governance. Policy-only
  sharing (`put-domain-permissions-policy`) is fine for one-off
  account pairs but does not scale.
- **CI: `codeartifact login` at the start of every build.** The token
  is 12h max. Caching the token across builds risks expiry-related
  build failures.
- **Publish via release pipeline, not developer machines.** Only the
  release-pipeline role should have `PublishPackageVersion`. Developer
  machines consume via `ReadFromRepository`.
- **Lifecycle policies for internal high-velocity packages.** Retain
  the last 100 versions; old versions accumulate storage cost without
  value.
- **VPC endpoints for regulated environments.** Both the API and
  repositories endpoints are available as interface VPC endpoints.

## Pre-flight safety checks (run before any provisioning CLI)

- **Confirm the domain owner account ID:**
  `aws sts get-caller-identity --query Account --output text`
- **Confirm the domain exists or is being created:**
  `aws codeartifact describe-domain --domain <name>` (or create in
  the same stack).
- **Confirm external connections available in the Region:**
  `aws codeartifact list-external-connections --domain <name>`
- **Confirm the CI role exists:**
  `aws iam get-role --role-name ci-build`
- **For cross-account:** confirm the consumer account ID and that the
  consumer account root is referenced in the domain permissions policy.
- **For VPC endpoints:** confirm `codeartifact.api` and
  `codeartifact.repositories` endpoints exist in the VPC.
- **For KMS-encrypted domains:** confirm the CMK policy grants
  CodeArtifact service access.

## Output format — MANDATORY literal labels

When invoked with a CodeArtifact provisioning request, your ENTIRE
response MUST be the checklist block below. The labels are
**case-sensitive all-caps keywords** — write them EXACTLY as shown.
Do NOT write a preamble. Start with `REPOSITORY:` and stop after the
`VERIFICATION_COMMANDS:` block.

```text
REPOSITORY: <repository-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Domain — <domain-name> (existing | new, owner <account-id>)
  [✓]      Repository — <repository-name>
  [✓]      Format — <npm | pip | maven | nuget | cargo | rubygems | swift | generic>
  [✓]      Upstream chain — <internal-mirror> -> ... -> external:<registry>
  [✓]      External connection — public:<registry>
  [✓]      Connection — arn:aws:codeartifact:<region>:<account>:repository/<domain>/<repo>
  [✓]      Domain owner IAM — <admin-role-arn> (codeartifact:* on domain)
  [✓]      Repository consume policy — <ci-role-arn> (ReadFromRepository, GetAuthorizationToken, GetPackageVersionAsset)
  [✓]      Repository publish policy — <release-role-arn> (PublishPackageVersion, PutPackageMetadata)
  [OPTIONAL] Cross-account domain share — <none | RAM resource share | consumer account IDs>
  [OPTIONAL] Package ingestion — <none | copy-package-versions batch>
  [OPTIONAL] Lifecycle policy — <none | retain last N versions>
VERIFICATION_COMMANDS:
  aws codeartifact describe-domain --domain <domain> --domain-owner <account-id>
  aws codeartifact describe-repository --domain <domain> --repository <repo>
  aws codeartifact list-repositories-in-domain --domain <domain>
  aws codeartifact list-external-connections --domain <domain>
  aws codeartifact get-repository-endpoint --domain <domain> --repository <repo> --format <format>
  aws codeartifact login --tool <tool> --repository <repo> --domain <domain> --domain-owner <account-id>
```

**Status marker semantics:**
- `[✓]` — applied and verified.
- `[✗]` — NOT applied or misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required for the workload type.
- `[INPUT NEEDED]` — prerequisite value missing; operator must provide.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is
missing (parent domain, external connection unavailable in Region,
CI role ARN, KMS key for encrypted domain), the verdict is
`PREREQUISITES_MISSING` with each gap listed.

## Domain

AWS CloudOps / Package Repository Provisioning.

## AWS documentation

- **CodeArtifact User Guide** — https://docs.aws.amazon.com/codeartifact/latest/ug/welcome.html
- **CodeArtifact Domains** — https://docs.aws.amazon.com/codeartifact/latest/ug/codeartifact-concepts.html#codeartifact-concepts-domain
- **CodeArtifact Repositories** — https://docs.aws.amazon.com/codeartifact/latest/ug/codeartifact-concepts.html#codeartifact-concepts-repository
- **CodeArtifact Upstreams** — https://docs.aws.amazon.com/codeartifact/latest/ug/codeartifact-concepts.html#codeartifact-concepts-upstream
- **CodeArtifact External Connections** — https://docs.aws.amazon.com/codeartifact/latest/ug/codeartifact-concepts.html#codeartifact-concepts-externalconnection
- **CodeArtifact IAM** — https://docs.aws.amazon.com/codeartifact/latest/ug/auth-and-access-control-iam.html
- **CodeArtifact Domain Sharing** — https://docs.aws.amazon.com/codeartifact/latest/ug/domain-share.html
- **CodeArtifact `login` CLI** — https://docs.aws.amazon.com/codeartifact/latest/ug/npm-auth.html
- **CodeArtifact VPC Endpoints** — https://docs.aws.amazon.com/codeartifact/latest/ug/vpc-support.html
- **CodeArtifact CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/codeartifact/

## References

- `references/deployment-cli-commands.md` — full copy-pasteable CLI
  command sequence for all 10 provisioning steps, including Terraform
  equivalents and per-format (npm / pip / maven / nuget / cargo /
  rubygems / swift) snippets.

- `references/upstreams-and-cross-account-guide.md` — deep reference
  on upstream chaining semantics, external connection internals,
  cross-account RAM sharing, IAM policy patterns, the full NEVER
  list, and edge-case handling.
