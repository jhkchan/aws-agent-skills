# Baseline (no-skill) response: tag-mutable-config-gap

This file captures what a generic assistant produces WITHOUT the
ecr-repository-auditor skill loaded.

---

This repository has mutable tags enabled, meaning tags can be
overwritten. The rest of the configuration looks fine with scanning
enabled and a lifecycle policy in place.

You might want to enable tag immutability to prevent tags from being
overwritten, but it depends on your workflow.
