# Eval: missing-parent-domain

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — parent domain required

## Prompt

Provision a CodeArtifact pip repository named payments-pip in
us-east-1. Domain: payments-team (does NOT exist in the
account; describe-domain returns ResourceNotFoundException).
Associate public:pypi external connection. CI role: payments-ci.
Release role: payments-release. Account: 123456789012.
