# Eval: semantic-version-update

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — update existing app, new version 1.1.0 (MINOR bump for backward-compatible feature), cannot overwrite 1.0.0

## Prompt

Update the existing SAR application
arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor
from version 1.0.0 to 1.1.0. The update adds a new optional
parameter MemorySize (backward-compatible). README updated.
Packaged template ready. Author: Jacky Chan. Region us-east-1.
