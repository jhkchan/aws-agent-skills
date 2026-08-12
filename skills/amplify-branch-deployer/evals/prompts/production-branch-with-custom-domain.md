# Eval: production-branch-with-custom-domain

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — production branch (main) mapped to example.com via Route 53, amplify.yml build spec, SPA rewrite, security headers, PR preview with fixed environment

## Prompt

Set up an AWS Amplify app named my-web-app in us-east-1 from
https://github.com/org/my-web-app. Production branch "main" with
auto-build enabled, stage PRODUCTION. Build settings via
amplify.yml at repo root (Next.js build to .next/). Map custom
domain example.com to main, and staging.example.com to a staging
branch. Route 53 hosted zone Z1DXXXXXXXXXX. Security headers:
HSTS, X-Frame-Options, X-Content-Type-Options. SPA rewrite
catch-all. Enable PR preview on main with a fixed environment
name "pr-preview". Build instance medium.
