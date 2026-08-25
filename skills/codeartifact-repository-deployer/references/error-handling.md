# Error Handling (load on demand) — CodeArtifact Repository Deployer

Error-handling and remediation detail moved verbatim from SKILL.md. Load on demand.

---

## Edge-case handling (moved from SKILL.md)

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

