# Eval: monorepo-subdir-detection

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — appRoot=packages/web-app set on create-app, amplify.yml in subdir, monorepo detection surfaced

## Prompt

Create an Amplify app for my monorepo at
https://github.com/org/my-monorepo. The web app lives at
packages/web-app and has its own amplify.yml there. Production
branch "main", auto-build enabled. The repo root is a Turborepo
workspace — do NOT build from the root. Region us-east-1.
