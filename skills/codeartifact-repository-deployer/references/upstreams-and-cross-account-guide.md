# Upstreams and Cross-Account Guide — CodeArtifact Repository Deployer

Deep reference on upstream chaining semantics, external connection
internals, cross-account RAM sharing, IAM policy patterns, the full
NEVER list, lifecycle policy internals, and edge-case handling.

## Upstream chaining — resolution semantics

A CodeArtifact repository resolves packages through an ordered chain:

```
[repository itself] -> [upstream 1] -> [upstream 2] -> ... -> [external connection]
```

### Resolution algorithm

1. CodeArtifact checks the repository itself for the requested
   package@version.
2. If not found, walks upstream repositories left-to-right.
3. If not found in any upstream, checks the external connection (if
   associated).
4. If found in the external connection, CodeArtifact caches a copy in
   the repository (lazy resolution). Subsequent requests for the same
   package@version are served from the local cache.

### Shadowing and security implications

The first match wins. This means:

- **Internal-first ordering is critical.** If an internal package named
  `express` exists in `team-internal`, and the external connection
  `public:npmjs` also has `express`, the internal version must resolve
  first. Putting the external connection upstream of the internal
  mirror would cause the public `express` to shadow the internal one
  — a supply-chain attack vector.
- **External connections are always last.** CodeArtifact enforces
  this: external connections cannot be upstream of repositories. But
  within the `upstreams` array, the order matters.

### Multi-hop chain example

```
team-payments-npm -> team-payments-internal -> shared-npm -> shared-internal -> public:npmjs
```

Resolution order:
1. `team-payments-npm` (team-specific packages)
2. `team-payments-internal` (curated team mirror)
3. `shared-npm` (org-wide npm mirror)
4. `shared-internal` (org-wide curated)
5. `public:npmjs` (external — last resort)

### Upstream vs external connection

| Aspect | Upstream repository | External connection |
|---|---|---|
| Source | Another CodeArtifact repository | Public registry (npmjs, pypi, etc.) |
| Managed by | Your organization | CodeArtifact service |
| Caching | Package stays in upstream repo | Package cached in your repo on first access |
| Configuration | `--upstreams repository=<name>` | `--external-connection public:<registry>` |
| Ordering | Position in upstreams chain | Always last (enforced by CodeArtifact) |

## External connection internals

External connections are CodeArtifact-managed bridges to public
registries. CodeArtifact maintains the connection server-side; clients
never talk to the public registry directly.

### Available external connections

| External connection | Public registry | Format |
|---|---|---|
| `public:npmjs` | npm (npmjs.com) | npm |
| `public:pypi` | Python Package Index | pip / Python |
| `public:maven-central` | Maven Central | maven / Java |
| `public:maven-googleandroid` | Google Android Maven | maven / Android |
| `public:maven-gradleplugins` | Gradle plugins portal | maven / Gradle |
| `public:nuget-org` | NuGet Gallery | nuget / .NET |
| `public:cargo` | crates.io | cargo / Rust |
| `public:rubygems` | RubyGems | rubygems / Ruby |

### Region availability

Most external connections are available in all CodeArtifact-supported
Regions. Swift and some newer format external connections may not be
available in all Regions. Always verify:

```bash
aws codeartifact list-external-connections --domain <domain-name>
```

### Caching behavior

When a package is first requested via the external connection,
CodeArtifact:

1. Fetches the package from the public registry server-side.
2. Stores a copy in your repository (lazy caching).
3. Serves subsequent requests from the local copy.

Cached packages are immutable — they are not re-fetched from the public
registry unless explicitly deleted via `delete-package-versions`.

### Rate limiting

CodeArtifact applies per-account rate limits on external connection
fetches. High-traffic CI pipelines may hit rate limits when fetching
many new packages. Mitigate by:

- Pre-warming the cache via `copy-package-versions` in a batch job.
- Using an internal mirror as the primary upstream, with the external
  connection as fallback only.

## Cross-account domain sharing

CodeArtifact domains can be shared across AWS accounts. Two mechanisms:

### Option A: Domain permissions policy (direct)

The owner account attaches a resource-based policy to the domain,
granting the consumer account root principal. The consumer account's
IAM then grants its principals access.

**Owner account:**

```bash
aws codeartifact put-domain-permissions-policy \
  --domain shared \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<consumer>:root"},
      "Action": [
        "codeartifact:DescribeDomain",
        "codeartifact:DescribeRepository",
        "codeartifact:GetAuthorizationToken",
        "codeartifact:ReadFromRepository",
        "codeartifact:ListRepositoriesInDomain"
      ],
      "Resource": "arn:aws:codeartifact:us-east-1:<owner>:domain/shared"
    }]
  }'
```

**Consumer account IAM:**

```bash
aws iam put-role-policy --role-name consumer-ci-build \
  --policy-name codeartifact-consume \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "codeartifact:GetAuthorizationToken",
        "codeartifact:ReadFromRepository",
        "codeartifact:DescribeRepository",
        "codeartifact:ListRepositoriesInDomain"
      ],
      "Resource": [
        "arn:aws:codeartifact:us-east-1:<owner>:domain/shared",
        "arn:aws:codeartifact:us-east-1:<owner>:repository/shared/*"
      ]
    }]
  }'
```

**Both-must-allow:** CodeArtifact is a both-must-allow service. The
owner's domain policy must grant the consumer account, AND the
consumer's IAM must grant its principals. A missing policy on either
side fails with `AccessDeniedException`.

### Option B: RAM resource share (Organizations)

For multi-account setups with Organizations or OUs, use a RAM resource
share. RAM integrates with AWS Organizations for automatic principal
discovery.

**Owner account:**

```bash
aws ram create-resource-share \
  --name codeartifact-shared-domain \
  --principals arn:aws:iam::<consumer-account-id>:root \
  --resource-arns arn:aws:codeartifact:us-east-1:<owner>:domain/shared
```

Or share with an entire OU:

```bash
aws ram create-resource-share \
  --name codeartifact-shared-domain \
  --principals arn:aws:organizations::<org-id>:ou/o-<org-id>/ou-<ou-id> \
  --resource-arns arn:aws:codeartifact:us-east-1:<owner>:domain/shared
```

RAM sharing also requires the owner account to enable sharing with
Organizations:

```bash
aws ram enable-sharing-with-aws-organization
```

**RAM vs policy-only:** RAM is recommended for multi-account setups
because it integrates with Organizations governance, supports OU-based
sharing, and provides a centralized view of shares. Policy-only sharing
is fine for one-off account pairs.

### Cross-account login

The consumer account uses the owner's domain ARN (with the owner
account ID) for `codeartifact login`:

```bash
aws codeartifact login \
  --tool npm \
  --domain shared \
  --domain-owner <owner-account-id> \
  --repository shared-npm
```

The `--domain-owner` flag is REQUIRED for cross-account access. Without
it, CodeArtifact looks for the domain in the caller's account and
returns `ResourceNotFoundException`.

## IAM policy patterns

CodeArtifact IAM is resource-scoped. The hierarchy is:
domain -> repository -> package -> version.

### Least-privilege consume (read-only)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "codeartifact:GetAuthorizationToken",
        "codeartifact:ReadFromRepository"
      ],
      "Resource": "arn:aws:codeartifact:<region>:<account>:domain/<domain>"
    },
    {
      "Effect": "Allow",
      "Action": [
        "codeartifact:GetPackageVersionAsset",
        "codeartifact:ListPackageVersionAssets",
        "codeartifact:DescribePackageVersion",
        "codeartifact:ListPackageVersions"
      ],
      "Resource": "arn:aws:codeartifact:<region>:<account>:repository/<domain>/<repo>/*"
    }
  ]
}
```

### Least-privilege publish

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "codeartifact:PublishPackageVersion",
        "codeartifact:PutPackageMetadata",
        "codeartifact:UpdatePackageVersionsStatus"
      ],
      "Resource": "arn:aws:codeartifact:<region>:<account>:repository/<domain>/<repo>/*"
    },
    {
      "Effect": "Allow",
      "Action": ["codeartifact:ReadFromRepository"],
      "Resource": "arn:aws:codeartifact:<region>:<account>:domain/<domain>"
    }
  ]
}
```

### Repository-scoped policy

Apply a resource-based policy on a single repository (supplements the
domain-level IAM):

```bash
aws codeartifact put-repository-permissions-policy \
  --domain shared \
  --repository shared-npm \
  --policy-document file:///repo-policy.json
```

Repository policies are useful for granting access to a specific
repository without modifying domain-wide IAM.

## Lifecycle policy internals

Lifecycle policies automate package version retention. They are defined
as a JSON rule set applied to a repository.

### Policy structure

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Retain last 100 versions per package",
      "actions": [
        {"type": "retain", "count": 100}
      ],
      "selection": {
        "tagStatus": "any",
        "countType": "versions",
        "countNumber": 100
      }
    },
    {
      "rulePriority": 2,
      "description": "Archive versions older than 90 days",
      "actions": [
        {"type": "archive"}
      ],
      "selection": {
        "tagStatus": "untagged",
        "countType": "age",
        "countUnit": "days",
        "countNumber": 90
      }
    }
  ]
}
```

### Rule evaluation

- Rules are evaluated in priority order (lowest priority number first).
- The first matching rule wins for each package version.
- `retain` keeps the specified count; older versions are candidates
  for downstream rules.
- `delete` removes the version permanently.
- `archive` marks the version as read-only (no re-publish).

### Common patterns

| Pattern | Rule | Use case |
|---|---|---|
| Retain last 100 | `retain count=100` | High-velocity internal packages |
| Delete untagged > 90 days | `delete tagStatus=untagged age=90d` | Cleanup of dev/test versions |
| Archive all > 1 year | `archive age=365d` | Compliance retention |

## Full NEVER list (extended)

1. NEVER put an external connection (`public:npmjs`, `public:pypi`, etc.)
   upstream of an internal mirror in the chain. Public packages with the
   same name would shadow internal packages — a supply-chain attack
   vector. Order upstreams internal-first, external-last.
2. NEVER grant `codeartifact:*` to broad principals (e.g., `*` or
   `Developers`). Scope consume and publish policies to the specific
   role and the specific repository ARN.
3. NEVER create a repository without verifying the parent domain exists
   (or is being created in the same stack). The repository creation
   silently fails with `ResourceNotFoundException`.
4. NEVER store long-lived `GetAuthorizationToken` output in CI secrets.
   Tokens expire in 12h; refresh via `codeartifact login` at the start
   of each build. Long-lived tokens in CI secrets are a credential
   leak risk.
5. NEVER assume external connections are available in all Regions. Swift
   and Cargo external connections are Region-limited. Verify with
   `list-external-connections` before configuring upstreams.
6. NEVER use `--domain-owner` with your own account ID in single-account
   deployments. It works but creates confusion. Use `--domain-owner`
   ONLY for cross-account access.
7. NEVER overwrite a published package version. CodeArtifact versions
   are immutable; `PublishPackageVersion` with an existing version
   returns `VersionConflictException`. Bump the version instead.
8. NEVER share a domain without verifying both sides of the
   both-must-allow contract. Owner domain policy + consumer IAM must
   both grant access. Missing either side fails silently with
   `AccessDeniedException`.
9. NEVER delete a domain with repositories still in it. The deletion
   fails with `ResourceInUseException`. Delete repositories first.
10. NEVER use CodeArtifact for Docker/OCI images. CodeArtifact does not
    support container image formats. Use Amazon ECR instead.
11. NEVER skip `codeartifact login` in CI pipelines relying on cached
    tokens. The token expires in 12h; builds fail with `ENEEDAUTH`
    (npm) or 401 (pip) without a clear error.
12. NEVER configure external connections on every repository in a
    multi-repo chain. One repository at the end of the chain should
    have the external connection; upstreams point at it.
13. NEVER use lifecycle policies as a replacement for versioning
    discipline. Lifecycle policies manage storage; they do not replace
    semantic versioning or release management.

## Edge-case handling (extended)

### `npm install` returns `ENEEDAUTH`

The authorization token expired (default 12h), or the CI runner is not
using the IAM role that has `codeartifact:GetAuthorizationToken`. Run
`codeartifact login` at the start of each build.

**Diagnostic:**
```bash
# Check token expiry
TOKEN=$(aws codeartifact get-authorization-token \
  --domain <domain> --domain-owner <owner> \
  --duration-seconds 60 --query authorizationToken --output text)
# Decode the token (base64) — the payload includes an expiration timestamp
```

### Repository resolves from public registry instead of internal

The external connection is upstream of the internal mirror. Reorder:

```bash
aws codeartifact update-repository \
  --domain <domain> \
  --repository <repo> \
  --upstreams repository=<internal-mirror>,repository=<org-wide>
```

Internal-first ordering ensures internal packages shadow public ones.

### Cross-account consumer gets `AccessDeniedException`

Both-must-allow contract failure. Check:

1. Owner domain policy includes the consumer account root:
   `aws codeartifact get-domain-permissions-policy --domain <domain>`
2. Consumer IAM grants its principal access to the owner's domain ARN:
   `aws iam get-role-policy --role-name <role> --policy-name <policy>`

The ARN in the consumer's IAM policy MUST include the owner's account
ID, not the consumer's. This is the most common cross-account
misconfiguration.

### `PublishPackageVersion` rejected

Package versions are immutable. The version already exists. Bump the
version, or (rarely) use `--revision` to publish a different revision
of the same version (requires the `PublishPackageVersion` action with
a `revision` field — only supported for some formats).

### External connection unavailable for Swift

Swift external connections are Region-limited. For unsupported Regions:

1. Create a `generic`-format repository.
2. Use `copy-package-versions` from a Region that has the Swift
   external connection.
3. Cross-Region replicate or use VPC endpoints for access.

### VPC endpoint configuration

For air-gapped or regulated environments, create interface VPC endpoints:

```bash
aws ec2 create-vpc-endpoint \
  --vpc-id <vpc-id> \
  --service-name com.amazonaws.<region>.codeartifact.api \
  --vpc-endpoint-type Interface \
  --subnet-ids <subnet-1> <subnet-2> \
  --security-group-ids <sg-id>

aws ec2 create-vpc-endpoint \
  --vpc-id <vpc-id> \
  --service-name com.amazonaws.<region>.codeartifact.repositories \
  --vpc-endpoint-type Interface \
  --subnet-ids <subnet-1> <subnet-2> \
  --security-group-ids <sg-id>
```

Both endpoints are required — `codeartifact.api` for the control plane
(create, describe, login), `codeartifact.repositories` for the data
plane (package downloads/uploads). External connections still require
the CodeArtifact service to fetch from the public registry server-side.

### Token refresh in long-running pipelines

For pipelines longer than 12 hours (rare but possible for monorepo
builds):

```bash
# Refresh token mid-pipeline
REFRESHED_TOKEN=$(aws codeartifact get-authorization-token \
  --domain <domain> \
  --domain-owner <owner> \
  --duration-seconds 43200 \
  --query authorizationToken --output text)

# Update npm config
npm config set //${DOMAIN}-${OWNER}.d.codeartifact.${REGION}.amazonaws.com/npm/${REPO}/:_authToken ${REFRESHED_TOKEN}
```

Do NOT cache the token across builds. Each build should call
`codeartifact login` fresh.

## Reference links

- **CodeArtifact User Guide** — https://docs.aws.amazon.com/codeartifact/latest/ug/welcome.html
- **Upstream repositories** — https://docs.aws.amazon.com/codeartifact/latest/ug/codeartifact-concepts.html#codeartifact-concepts-upstream
- **External connections** — https://docs.aws.amazon.com/codeartifact/latest/ug/codeartifact-concepts.html#codeartifact-concepts-externalconnection
- **Domain sharing** — https://docs.aws.amazon.com/codeartifact/latest/ug/domain-share.html
- **CodeArtifact IAM** — https://docs.aws.amazon.com/codeartifact/latest/ug/auth-and-access-control-iam.html
- **VPC endpoints** — https://docs.aws.amazon.com/codeartifact/latest/ug/vpc-support.html
- **Lifecycle policies** — https://docs.aws.amazon.com/codeartifact/latest/ug/lifecycle-policies.html
