# Eval: swift-repo-with-region-check

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Region-limited Swift external connection, generic-format approach

## Prompt

Provision a CodeArtifact repository for Swift packages in
ap-southeast-1. Domain: mobile-shared (existing, owner
123456789012). The public swift external connection is NOT
available in ap-southeast-1 (list-external-connections does
not list it). Provide the recommendation (use a generic-format
repository and copy-package-versions from us-east-1 where
Swift is supported). CI role: mobile-ci. Account: 123456789012.
