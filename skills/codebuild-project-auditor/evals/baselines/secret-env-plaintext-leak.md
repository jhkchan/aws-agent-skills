# Baseline (no-skill) response: secret-env-plaintext-leak

This file captures what a generic assistant produces WITHOUT the
codebuild-project-auditor skill loaded.

---

The project defines several environment variables. Two of them —
DB_PASSWORD and GITHUB_TOKEN — look like secrets and are stored as
plaintext strings in the environmentVariables array.

You should move these to AWS Secrets Manager and reference them from the
build project. Storing secrets as plaintext environment variables means
anyone with read access to the project config can see them.

Otherwise the project runs as a non-privileged container, logs to
CloudWatch, and lives in a VPC. No badge is enabled.
