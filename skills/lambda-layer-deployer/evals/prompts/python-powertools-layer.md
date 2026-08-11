# Eval: python-powertools-layer

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — all checklist items verified, correct zip path (python/), compatible runtimes (python3.10-3.13), arm64 architecture, version ARN, function attachment

## Prompt

Create a Python Lambda Layer named "my-powertools-layer" in
us-east-1. Include aws-lambda-powertools, boto3, and requests.
Compatible with python3.10, python3.11, python3.12, and
python3.13. Architecture: arm64 only (Graviton). License: MIT.
Attach it to function "my-api-fn" which runs on python3.12 +
arm64. Account ID: 123456789012.
