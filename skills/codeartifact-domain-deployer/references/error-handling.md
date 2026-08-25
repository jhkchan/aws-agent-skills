# Error Handling (load on demand) — CodeArtifact Domain Deployer

Error-handling and remediation detail moved verbatim from SKILL.md. Load on demand.

---

## Error handling deep dives (moved from SKILL.md)

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

