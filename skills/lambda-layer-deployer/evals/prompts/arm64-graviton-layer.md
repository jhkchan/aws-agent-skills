# Eval: arm64-graviton-layer

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — provided.al2023 layer with Go binary for arm64, correct zip path (bin/), architecture-specific compiled code

## Prompt

Create a Lambda Layer named "go-utils-layer" in us-east-1 for
provided.al2023 runtime. It contains a Go binary compiled for
arm64 (Graviton) that provides a custom data-processing tool.
Architecture: arm64 only. The binary is at ./layer/bin/bootstrap.
License: MIT. Account ID: 123456789012.
