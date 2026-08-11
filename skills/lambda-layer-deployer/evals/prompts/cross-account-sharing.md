# Eval: cross-account-sharing

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — layer shared with account 123456789012 via resource-based policy (add-permission) with consumer IAM noted

## Prompt

Create a Python Lambda Layer named "shared-utils-layer" in
us-east-1 with numpy and pandas for python3.12. Architecture:
x86_64. Share this layer with account 123456789012 so they can
attach it to their Lambda functions. License: BSD-3-Clause.
Account ID: 123456789012.
