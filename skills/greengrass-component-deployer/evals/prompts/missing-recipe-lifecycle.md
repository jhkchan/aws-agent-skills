# Eval: missing-recipe-lifecycle

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — recipe has metadata and artifacts but no lifecycle section (no install, startup, or shutdown); component is a no-op without lifecycle hooks

## Prompt

Create a Greengrass v2 component com.example.BrokenComponent
version 1.0.0. The recipe has metadata and artifacts but no
lifecycle section (no install, startup, or shutdown hooks).
Deploy to thing group TestDevices (1 device) in us-east-1.
Artifact at s3://gg-artifacts/broken/1.0.0/app.py.
