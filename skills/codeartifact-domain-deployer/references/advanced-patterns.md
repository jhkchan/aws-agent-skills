# Advanced Patterns (load on demand) — CodeArtifact Domain Deployer

Expert-knowledge deep dives, edge-case catalogs, and recent-feature notes moved verbatim from SKILL.md. Load on demand.

---

## Mindset — three misconceptions at provisioning time (moved from SKILL.md)

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

## Expert heuristic — domain owner vs repository admin (moved from SKILL.md)

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

## Recent AWS features (2023-2026) (moved from SKILL.md)

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

