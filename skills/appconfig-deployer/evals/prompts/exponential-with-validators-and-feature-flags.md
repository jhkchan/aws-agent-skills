# Eval: exponential-with-validators-and-feature-flags

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — exponential deployment strategy, feature flag schema, Lambda validator, JSON schema validation

## Prompt

Create an AppConfig application named feature-flag-platform in
us-east-1. Environment: staging. Configuration profile:
feature-flag-store with feature flag schema. Deployment
strategy: exponential, 2% growth factor, 10-minute bake time.
Attach a Lambda validator (flag-validator function). Enable JSON
schema validation for flag structure. Tags: Environment=staging,
Application=feature-platform.
