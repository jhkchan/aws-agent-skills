# Baseline (no-skill) response: privileged-dind-no-docker

This file captures what a generic assistant produces WITHOUT the
codebuild-project-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, blast-radius reasoning).

---

This CodeBuild project has privilegedMode set to true. The build runs a
Maven build (`mvn clean install`) and copies the resulting JAR to S3.
There is no Docker-related command in the buildspec.

Privileged mode grants the build container elevated permissions. Since
the build does not appear to need Docker, you could turn this off. Use
the AWS CLI to update the project.

The project otherwise has logging to CloudWatch enabled and runs in a
VPC. There is no badge enabled.
