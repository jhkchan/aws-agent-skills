# Baseline (no-skill) response: badge-public-status-leak

This file captures what a generic assistant produces WITHOUT the
codebuild-project-auditor skill loaded.

---

This project looks well-configured. Privileged mode is off, no plaintext
secrets are visible, S3 logs are encrypted with a customer-managed KMS
key, the service role is scoped to specific actions on specific resources,
and the build runs in a VPC with private subnets.

The only notable setting is that badgeEnabled is true. The build-status
badge is a small SVG image that shows whether the latest build for a
branch succeeded or failed. It is convenient for embedding in a README
but the URL is publicly accessible.

You could disable the badge if you do not need it.
