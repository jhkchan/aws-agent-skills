---
description: Provision an AWS Amplify application (Next.js, React, Vue, Angular, Svelte) with production-grade defaults — Git-based deploy (CodeCommit/GitHub/GitLab/Bitbucket), SSR/SSG/SPA rendering mode, amplify.yml buildspec, custom headers, redirects, environment variables (plaintext + Secrets Manager), custom domain (Route 53/CloudFront), Amplify Gen 2 (TypeScript CDK) backend, CI/CD pipeline. Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create amplify app"
  - "provision amplify"
  - "deploy amplify"
  - "amplify gen 2"
  - "amplify github"
  - "amplify codecommit"
  - "amplify gitlab"
  - "amplify bitbucket"
  - "amplify custom domain"
  - "amplify ssr"
  - "amplify ssg"
  - "amplify spa"
  - "amplify backend"
  - "amplify cognito"
  - "amplify appsync"
  - "amplify buildspec"
  - "amplify.yml"
  - "amplify redirects"
  - "amplify cicd"
  - "amplify environment variables"
  - "ampx pipeline-deploy"
  - "defineBackend"
routes_to: amplify-app-deployer
---

# /aws:deploy-amplify-app

Activate the `amplify-app-deployer` skill and provision an AWS Amplify
application with production-grade defaults.

## What it does

The skill walks a 10-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Git provider (CodeCommit / GitHub / GitLab / Bitbucket + CodeConnections)
2. Framework + rendering mode (Next.js SSR, React SPA, Vue SSR, Angular SPA)
3. Build settings (`amplify.yml` buildspec, phases, cache, artifacts)
4. Environment variables (plaintext + Secrets Manager references)
5. Custom headers + redirects (SPA rewrite, security headers, legacy 301s)
6. Custom domain (ACM cert in us-east-1, Route 53 / third-party DNS)
7. Amplify Backend Gen 2 (Cognito auth, AppSync GraphQL, S3, Lambda)
8. CI/CD pipeline (branch builds on every push, preview URLs)
9. Amplify Gen 2 latest features (TypeScript CDK, branch-based backends)
10. Networking edge cases (VPC, CloudFront-in-front-of-Amplify)

## When to use

- You need to create a new Amplify app with production defaults.
- You are wiring a Git provider (CodeCommit, GitHub, GitLab, Bitbucket).
- You need to decide SSR vs SSG vs SPA for a workload.
- You need to configure a custom domain via Route 53 / CloudFront.
- You are deploying an Amplify Gen 2 (TypeScript CDK) backend.
- You need to wire Cognito auth / AppSync API / S3 storage / Lambda.
- You want to validate that an Amplify design meets production baseline.
- You need copy-pasteable provisioning commands or IaC templates.

## How to invoke

### Slash command

```
/aws:deploy-amplify-app
```

Then provide: app name, region, framework (Next.js, React, Vue,
Angular, Svelte), rendering mode (SSR, SSG, SPA), Git provider and
repo URL, build settings (amplify.yml), environment variables (plaintext
vs Secrets Manager refs), custom domain (Route 53 / CloudFront /
third-party DNS), backend (Gen 2 with Cognito/AppSync/S3/Lambda), and
any optional features (CI/CD previews, branch environments).

### Natural language

Any of these routes to the same skill:

- "create a production Amplify Next.js app"
- "deploy a React SPA to Amplify"
- "set up Amplify Gen 2 backend with Cognito and AppSync"
- "configure a custom domain on my Amplify app"
- "wire Amplify with GitHub CodeConnections"

### CLI routing

```bash
node cli/bin/cli.js route "create an amplify app"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or harden
Amplify applications. The output checklist feeds into verification
pipelines and audit skills.

## Example

```
You: /aws:deploy-amplify-app

     Provision a production Amplify app "prod-web" in us-east-1.
     Next.js 14 SSR with Gen 2 backend (Cognito auth, AppSync GraphQL,
     S3 storage). GitHub repo example/prod-web with CodeConnections.
     Custom domain app.example.com via Route 53 Z111. ACM cert
     arn:aws:acm:us-east-1:111:certificate/abc ISSUED. Secrets Manager
     for STRIPE_SECRET_KEY. Security headers: HSTS, CSP, X-Frame-Options
     DENY. SPA rewrite. CI/CD on every push; main=prod, staging,
     PR previews. Account: 123456789012.

Skill:
  APP: prod-web
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Git provider: GitHub (CodeConnections AVAILABLE)
    [✓] Repository: github.com/example/prod-web (amplify.yml committed)
    [✓] Framework: Next.js 14 (SSR)
    [✓] Build settings: ampx pipeline-deploy + npm run build
    [✓] Environment variables: 3 plaintext, 1 Secrets Manager ref
    [✓] Custom headers: HSTS, CSP, X-Frame-Options DENY
    [✓] Redirects: /<*> -> /index.html status 200
    [✓] Custom domain: app.example.com (ACM ISSUED, Route 53)
    [✓] Backend (Gen 2): Cognito auth, AppSync GraphQL, S3
    [✓] CI/CD: branch builds; main=prod, staging, PR=preview
  VERIFICATION_COMMANDS:
    aws amplify get-app --app-id dXXXX
    aws amplify list-branches --app-id dXXXX
    aws amplify get-domain-association --app-id dXXXX --domain-name example.com
    aws acm describe-certificate --certificate-arn <arn> --region us-east-1
```

## References

- Skill definition: `skills/amplify-app-deployer/SKILL.md`
- Build and domain guide: `skills/amplify-app-deployer/references/build-and-domain-reference.md`
- Gen 2 backend guide: `skills/amplify-app-deployer/references/backend-gen2-reference.md`
- Eval suite: `skills/amplify-app-deployer/evals/evals.json`
