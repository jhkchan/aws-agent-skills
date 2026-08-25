# Diagnostic commands — CloudFront Response Headers Deployer

Pre-flight and pre-remediation command listings moved out of SKILL.md for
progressive disclosure. Load on demand.

## Live-account pre-flight (skip if offline plan audit)

**Live-account pre-flight (skip if offline plan audit):**
1. `aws cloudfront get-distribution-config --id <id>` — confirm the
   target distribution exists and is in `Deployed` state.
2. `aws cloudfront list-response-headers-policies` — verify whether a
   policy with the target name already exists (create vs. update).
3. `aws cloudfront get-response-headers-policy --id <id>` — if updating,
   snapshot the existing config.
4. For CORS: verify the origin is reachable on HTTPS
   (`curl -I https://origin.example.com`). HTTP origins cannot serve
   credentialed CORS.
5. `aws cloudfront list-cache-policies` — verify the cache policy on
   the target behavior does not already inject conflicting headers.
6. For managed policy references: verify the managed policy ID is
   correct (`0857826db9cffff310d5ad62955c9c26` for `SecurityHeadersPolicy`).

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-response-headers-policy`, `update-response-headers-policy`,
  `delete-response-headers-policy`, `update-distribution` to attach),
  emit: `CONFIRM: About to <operation> on policy <name> / distribution
  <id>. This affects <consequence>. Proceed? (yes/no)`.

- **Verify the distribution is in `Deployed` state.**
  `aws cloudfront get-distribution --id <id> --query 'Distribution.Status'`.

- **Snapshot the existing policy and distribution config.**
  `aws cloudfront get-response-headers-policy --id <id> --output json > /tmp/policy-backup.json`
  and `get-distribution-config --id <id> --output json > /tmp/dist-backup.json`.

- **Capture the ETag for `update-distribution`.** The
  `update-distribution` call requires `--if-match <etag>` from the
  latest `get-distribution-config`.

- **Before emitting CSP, verify the site's script inventory.** CSP
  blocks unknown inline scripts and external CDNs. A CSP audit
  (browser DevTools → Console with Report-Only mode) prevents
  breakage.

- **Before emitting HSTS with `includeSubDomains`, verify all
  subdomains serve HTTPS.** HTTP-only subdomains will break.

- Prefer additive changes (attach a policy to a new behavior) over
  destructive changes (remove a policy from an existing behavior).
