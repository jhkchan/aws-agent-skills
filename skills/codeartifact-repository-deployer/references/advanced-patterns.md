# Advanced Patterns (load on demand) — CodeArtifact Repository Deployer

Expert-knowledge deep dives, edge-case catalogs, and recent-feature notes moved verbatim from SKILL.md. Load on demand.

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

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

## Expert heuristic — designing domains, repositories, and upstreams (moved from SKILL.md)

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

