---
name: amplify-app-deployer
description: 'Provisions AWS Amplify applications with production defaults: Git-based deployments (CodeCommit, GitHub, GitLab, Bitbucket) with OAuth or service-role connection, build settings (amplify.yml buildspec with frontend and backend phases), custom headers, redirects (SPA rewrite for React Router / Next.js), environment variables (plaintext and AWS Secrets Manager references), custom domain via Route 53 CNAME or CloudFront, rendering mode (SSR vs SSG vs SPA), Amplify Backend (auth with Cognito, API with AppSync GraphQL or REST, storage with S3, functions with Lambda), CI/CD pipeline on every git push, branch-based environments, and the latest Amplify Gen 2 (TypeScript CDK-based defineBackend). Emits a READY_TO_DEPLOY checklist with prerequisites, build config, and verification commands. Use when creating an Amplify app, wiring a Git provider, configuring a custom domain, designing SSR/SSG, deploying Amplify Gen 2, or generating provisioning CLI / IaC templates.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with amplify, cloudfront, route53, iam, secretsmanager, cognito-idp, appsync, lambda, s3, and codeconnections access. Works with Terraform aws_amplify_app / aws_amplify_branch / aws_amplify_domain_association resources, CloudFormation AWS::Amplify::App templates, and the Amplify Gen 2 TypeScript CDK backend (amplify defineBackend).'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: DevTools
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, amplify, devtools, deploy, cicd, git, codecommit, github, frontend, serverless
  dependencies: aws-orchestrator
  keywords: aws, amplify, amplify gen 2, git-based deploy, codecommit, github, gitlab, bitbucket, buildspec, amplify.yml, custom headers, redirects, SPA rewrite, environment variables, custom domain, route 53, cloudfront, SSR, SSG, SPA, amplify backend, cognito auth, appsync api, lambda functions, s3 storage, cicd pipeline, branch environments, cloudops, deploy, devtools
  when_to_use: Invoke when the user wants to create a new Amplify application, wire a Git provider (CodeCommit, GitHub, GitLab, Bitbucket) for CI/CD, configure a custom domain via Route 53 / CloudFront, design SSR vs SSG vs SPA rendering, deploy an Amplify Gen 2 (TypeScript CDK-based) backend, wire Cognito auth / AppSync API / S3 storage / Lambda functions, configure buildspec.yml (amplify.yml), set custom headers / redirects (SPA rewrite), manage environment variables, or generate provisioning CLI commands / IaC templates. Do NOT invoke for self-managed Next.js on EC2 / ECS / Fargate, CloudFront static site without Amplify, or AppSync-only deployments without the Amplify build pipeline.
---

# Amplify App Deployer

An AWS CloudOps agent skill that provisions Amplify applications with
correct defaults across Git provider, rendering mode, build settings,
custom domain, backend, and CI/CD. The skill walks a 10-step
provisioning procedure, captures the operator's framework, Git, and
backend decisions, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## What this skill does

Provisions Amplify applications with production-grade defaults across
Git-based deployments (CodeCommit / GitHub / GitLab / Bitbucket),
rendering mode (SSR / SSG / SPA), build settings (amplify.yml), custom
headers and redirects, environment variables, custom domain (Route 53 /
CloudFront), Amplify Backend (auth, API, storage, functions), and CI/CD
pipeline on every git push. The output is a READY_TO_DEPLOY checklist
with verification commands.

## STRICT output contract

When this skill is invoked with an app-provisioning request (app name,
framework, Git provider, region, or a partial configuration), the agent
MUST respond with the READY_TO_DEPLOY checklist defined in §"Output
format" using the literal all-caps labels `APP:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines
of the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the literal
labels breaks automation silently.

## Mindset

**One-line takeaway:** Amplify is Git-driven infra — every push triggers
a build, every branch is an environment, and the buildspec is the source
of truth for build, env vars, and redirects. Get the buildspec right at
creation; retrofitting it later causes silent deploy failures.

Three behaviours separate a senior Amplify engineer from a generalist:

- **The buildspec (amplify.yml) is the source of truth.** Build phases,
  environment variables, custom headers, and redirects all live in
  `amplify.yml` committed to the repo. Operators who configure these in
  the Console produce uncommitted, untracked config that vanishes on
  repo re-clone. Commit `amplify.yml` from day one.

- **SSR vs SSG vs SPA is decided at framework + Amplify config level.**
  Next.js on Amplify supports SSR (via Amplify's SSR compute), SSG
  (static export), and SPA (single-page with rewrites). The choice
  affects cost, cold-start, and the redirect rule. A common mistake:
  deploying a Next.js SSR app as SPA, then wondering why
  `getServerSideProps` returns 404. The framework directive
  (`output: 'export'`, `ssr`) tells Amplify how to host.

- **Custom domain needs DNS verification before the cert issues.** An
  Amplify custom domain uses an ACM certificate with DNS validation.
  The Route 53 / third-party DNS must have the CNAME validation record
  in place before the cert goes to ISSUED. Operators who add the domain
  but skip DNS validation wait hours for a cert that never issues.

## Philosophy

- **Amplify Gen 2 (TypeScript CDK) replaces Gen 1's CLI-driven backend.**
  Gen 2 uses `defineBackend` in `amplify/backend.ts` — fully CDK-based,
  no `amplify init` / `amplify push` ceremony. The backend is IaC,
  deployable via `npx ampx pipeline-deploy` in the Amplify build phase.
  Gen 1's `amplify add auth` mutation model is legacy; new apps should
  use Gen 2.

- **Branch environments are first-class.** Every git branch gets its
  own Amplify URL (`https://branch.dXXXX.amplifyapp.com`). A `main`
  branch is production; a `staging` branch is the staging URL; a PR
  branch is a preview. The CI/CD pipeline is per-branch. Operators who
  run one big `main` branch and manually promote lose the preview-URL
  workflow that is Amplify's superpower.

- **Environment variables are branch-scoped.** An env var set on
  `main` does NOT appear on `staging` unless explicitly added. Secrets
  (API keys, DB credentials) should be AWS Secrets Manager references,
  not plaintext env vars — Amplify reads the secret at build time and
  never logs the value.

- **Custom headers and redirects are committed, not Console-configured.**
  `amplify.yml`'s `customHeaders` and `redirects` sections are the IaC
  surface. Console-configured headers and redirects are overwritten on
  the next push that includes `amplify.yml`. Always commit.

## Quick navigation

| Section | When to read |
|---|---|
| §"Prerequisites" | Always — verify before provisioning |
| §"Step 1 — Git provider" | CodeCommit / GitHub / GitLab / Bitbucket |
| §"Step 2 — Framework + rendering mode" | SSR vs SSG vs SPA |
| §"Step 3 — Build settings (amplify.yml)" | buildspec, phases, cache |
| §"Step 4 — Environment variables" | plaintext + Secrets Manager |
| §"Step 5 — Custom headers + redirects" | SPA rewrite, security headers |
| §"Step 6 — Custom domain" | Route 53 / CloudFront / ACM cert |
| §"Step 7 — Amplify Backend (Gen 2)" | auth, API, storage, functions |
| §"Step 8 — CI/CD pipeline" | branch builds, preview URLs |
| §"Step 9 — Amplify Gen 2 latest features" | TypeScript CDK backend |
| §"NEVER do these things" | Review before signing off |
| §"Output format" | The literal checklist template |
| references/build-and-domain-reference.md | Deep buildspec + domain |
| references/backend-gen2-reference.md | Gen 2 backend patterns |

## Reasoning framework (why provisioning order matters)

Amplify configurations have **dependency and Git-binding semantics**
that make the provisioning order non-trivial:

1. **Git provider BEFORE the app** — Amplify needs a repo connected to
   trigger builds. The connection (OAuth for GitHub, service role for
   CodeCommit) must exist before `create-app`.
2. **Framework BEFORE build settings** — Next.js SSR needs
   `amplify.yml`'s SSR-aware build phase; a static SPA needs a plain
   `npm run build` and rewrite rule.
3. **Build settings BEFORE the first push** — `amplify.yml` committed
   to the repo is read on the first build. A missing buildspec defaults
   to Amplify's framework auto-detection, which often misses custom
   phases.
4. **Backend BEFORE frontend env vars** — the frontend needs to know
   the API URL, Cognito user pool ID, etc. These come from the backend
   stack (Gen 2 `defineBackend` outputs).
5. **Custom domain AFTER the first successful build** — Amplify issues
   the domain cert after the app is live on the default
   `*.amplifyapp.com` URL. Adding the domain before the first build
   produces a cert for a non-functional app.

## Amplify configuration dependency graph (novel heuristic)

| Configuration | Binding | Effect of wrong order |
|---|---|
| Git provider connection | OAuth / service role | `create-app` fails without `--repository` and a valid token |
| Framework detection | `amplify.yml` buildSpec | Wrong framework = wrong build command = silent 500 on the URL |
| Rendering mode (SSR/SSG/SPA) | `next.config.js` + Amplify | SSR-as-SPA = 404 on dynamic routes; SSG-as-SSR = wasted compute |
| Environment variables | Per-branch | A var on `main` does NOT appear on `staging`; secrets should be Secrets Manager refs |
| Custom headers + redirects | `amplify.yml` (committed) | Console-config set is overwritten on next push |
| Custom domain | ACM cert + DNS validation | Cert stuck in PENDING if DNS CNAME missing |
| Backend (Gen 2) | `amplify/backend.ts` (CDK) | Backend deploy must run in the build phase via `ampx pipeline-deploy` |
| Branch environments | Per-branch URL | PR previews only if branch detection is on |

**Cross-dependency gotchas:**
- A Next.js SSR app needs the Amplify SSR compute role automatically
  created on first deploy — do not delete it.
- A custom domain on a third-party DNS (GoDaddy, Namecheap) needs the
  ACM validation CNAME copied manually; Route 53 does it automatically
  only if the hosted zone is in the same account.
- Amplify Gen 2 backend deploys in the build phase via
  `npx ampx pipeline-deploy --branch $AWS_BRANCH`. The role assumed by
  the Amplify build needs `iam:PassRole` + CDK bootstrapped in the
  account.

## Expert heuristic: rendering mode cost and latency

The rendering mode decides cost, cold-start, and SEO behavior. Pick by
the actual workload, not by framework default.

| Mode | When to use | Cost | Cold start | SEO |
|---|---|---|---|---|
| **SSG** (static export) | Marketing site, docs, blog — content known at build | Build-time only | None (CDN) | Excellent |
| **SSR** (server-side render at request) | Personalized dashboards, auth-gated apps, A/B tests | Per-request compute | 50-200ms (managed) | Good (rendered HTML) |
| **SPA** (client-side render) | Internal tools, SaaS dashboards behind login | Build-time only | None (CDN) | Poor (JS-rendered) |
| **ISR** (incremental static regen) | E-commerce catalog, news with periodic rebuild | Build + periodic | None for cached | Excellent |

**Common mistake:** defaulting to SSR for a marketing site. SSR
compute is billed per-request; a static marketing site pays for compute
it does not need. Use SSG (`output: 'export'` in Next.js) for content
sites. Use SSR only when the HTML differs per user / per request.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with Amplify access | Can't provision without it | `aws sts get-caller-identity` |
| Region selected | Amplify apps are region-scoped | `aws configure get region` |
| Git repo (CodeCommit / GitHub / GitLab / Bitbucket) with `amplify.yml` | Amplify builds from a connected repo | `git remote -v`; check `amplify.yml` exists at repo root |
| Git provider connection (OAuth token or CodeConnections service role) | Amplify needs read access to the repo | For GitHub: PAT with `repo` scope; for CodeCommit: `aws codeconnections list-connections` |
| ACM certificate in us-east-1 (for custom domain) | Amplify custom domains use ACM | `aws acm list-certificates --region us-east-1` |
| Route 53 hosted zone (for Route 53-managed domain) | Custom domain DNS | `aws route53 list-hosted-zones` |
| Backend stack artifacts (for Gen 2: `amplify/backend.ts`; CDK bootstrap) | Backend deploy runs in the build phase | Check `amplify/backend.ts` exists; `aws cloudformation describe-stacks --stack-name CDKToolkit` |
| Framework directive decided (SSR / SSG / SPA) | Drives buildspec + redirect rules | Captured in the prompt or follow-up |
| Service role for Amplify (auto-created or existing) | Amplify assumes a role to access CodeCommit / Secrets Manager | `aws iam get-role --role-name AWSAmplifyServiceRole` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 10-step provisioning procedure

### Step 1 — Git provider (binding decision — BEFORE create-app)

Amplify supports CodeCommit, GitHub, GitLab, and Bitbucket. The
provider determines the connection method.

**Decision tree:**

```text
Is the repo in AWS CodeCommit?
├── YES → CodeCommit  (service role via CodeConnections)
└── NO → Which provider?
    ├── GitHub → GitHub  (OAuth PAT or GitHub App; CodeConnections)
    ├── GitLab → GitLab  (access token; CodeConnections)
    └── Bitbucket → Bitbucket  (app password; CodeConnections)
```

**Connection setup (GitHub example):**

```bash
# Create a CodeConnections connection (formerly CodeStar connection)
aws codeconnections create-connection \
  --provider-type GitHub \
  --connection-name github-amplify \
  --output json
# Then complete the OAuth handshake in the Console to set the connection
# status to AVAILABLE.
```

**Common mistake:** trying to use a personal access token (PAT) without
the `repo` scope. The Amplify build fails on `git clone` with a 401.
Use a CodeConnections connection for GitHub / GitLab / Bitbucket; the
connection re-auths automatically.

### Step 2 — Framework + rendering mode (drives buildspec)

The framework directive determines the build phase, the output directory,
and the redirect rules.

| Framework | SSR support | Build command | Output dir |
|---|---|---|---|
| Next.js (SSR) | YES (Amplify SSR compute) | `npm run build` | `.next` (Amplify auto-detects SSR) |
| Next.js (SSG) | `output: 'export'` in next.config | `npm run build` | `out` |
| React (Vite) | SPA | `npm run build` | `dist` |
| React (CRA) | SPA | `npm run build` | `build` |
| Vue / Nuxt | SSR (Nuxt) or SPA (Vue) | `npm run build` | `.output` (Nuxt) or `dist` (Vue) |
| Angular | SPA | `npm run build` | `dist/<project>` |
| Svelte / SvelteKit | SSR / SPA | `npm run build` | `build` |

**Common mistake:** declaring SSR in `next.config.js` but deploying as
SPA. The framework directive must match the Amplify framework setting.
For Next.js SSR, Amplify auto-provisions the SSR compute role on first
deploy — do not delete it.

### Step 3 — Build settings (amplify.yml buildspec)

The `amplify.yml` file at repo root is the buildspec. It defines
frontend and backend phases, cache, env vars, and output artifacts.

**Canonical `amplify.yml` (Next.js + Gen 2 backend):**

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npx ampx pipeline-deploy --branch $AWS_BRANCH --app-id $AWS_APP_ID
        - npm run build
  artifacts:
    baseDirectory: .next
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
  customHeaders:
    - pattern: '**/*'
      headers:
        - key: Strict-Transport-Security
          value: 'max-age=31536000; includeSubDomains'
        - key: X-Content-Type-Options
          value: 'nosniff'
        - key: X-Frame-Options
          value: 'DENY'
  redirects:
    - source: '/<*>'
      target: '/index.html'
      status: 200
      condition: null
```

**SPA rewrite rule:** the `redirects` section with `status: 200` rewrites
all paths to `/index.html` for client-side routing (React Router, Vue
Router). Without this, refreshing `/users/123` returns 404.

**Cache:** `node_modules` caching speeds up builds. Pin the lockfile
(`npm ci` not `npm install`) for reproducible builds.

### Step 4 — Environment variables

Env vars are branch-scoped. Set them via the Console, CLI, or
`amplify.yml` `env:`.

```bash
# Plaintext env var on a specific branch
aws amplify update-app \
  --app-id dXXXX \
  --environment-variables platform=web,apiUrl=https://api.example.com \
  --output json

# Secrets Manager reference (for API keys, DB credentials)
aws amplify update-app \
  --app-id dXXXX \
  --custom-rules source=SECRET_API_KEY,target=arn:aws:secretsmanager:us-east-1:111:secret:api-key-XXX \
  --output json
```

**Common mistake:** setting a secret as a plaintext env var. Plaintext
env vars are visible in the Console and in `amplify.yml` if committed.
Use Secrets Manager references for anything sensitive — Amplify reads
the secret value at build time, never logs it.

### Step 5 — Custom headers + redirects

Custom headers (security headers, CORS) and redirects (SPA rewrite,
legacy URL redirects) live in `amplify.yml`.

```yaml
customHeaders:
  - pattern: '**/*'
    headers:
      - key: Strict-Transport-Security
        value: 'max-age=31536000; includeSubDomains'
      - key: Content-Security-Policy
        value: "default-src 'self'; script-src 'self'"
redirects:
  - source: '/old-path'
    target: '/new-path'
    status: '301'
  - source: '/<*>'
    target: '/index.html'
    status: '200'
```

**Common mistake:** Console-configuring headers and redirects. They are
overwritten on the next push that includes `amplify.yml`. Always commit.

### Step 6 — Custom domain (Route 53 / CloudFront)

A custom domain uses an ACM certificate with DNS validation.

```bash
# Request an ACM cert in us-east-1 (Amplify requires us-east-1)
aws acm request-certificate \
  --domain-name app.example.com \
  --validation-method DNS \
  --region us-east-1 \
  --output json
# Add the validation CNAME to Route 53 / third-party DNS

# Associate the domain with the Amplify app
aws amplify create-domain-association \
  --app-id dXXXX \
  --domain-name example.com \
  --sub-domain-settings '[{"prefix":"app","branchName":"main"}]' \
  --output json
```

**Route 53 automatic validation:** if the hosted zone for
`example.com` is in the same account, ACM auto-writes the validation
CNAME. For third-party DNS (GoDaddy, Namecheap), copy the CNAME
manually.

**Common mistake:** requesting the cert in a region other than
`us-east-1`. Amplify custom domains require the cert in us-east-1
regardless of where the app is deployed.

### Step 7 — Amplify Backend (Gen 2 TypeScript CDK)

Amplify Gen 2 uses `amplify/backend.ts` with `defineBackend` — fully
CDK-based, no `amplify init` / `amplify push`.

```typescript
// amplify/backend.ts
import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource';
import { data } from './data/resource';
import { storage } from './storage/resource';

export const backend = defineBackend({
  auth,
  data,
  storage,
});
```

**Backend resources (Gen 2 patterns):**
- **Auth:** Amazon Cognito user pool + identity pool.
  `npx ampx add auth` generates the `auth/resource.ts`.
- **Data (API):** AppSync GraphQL API with TypeScript schema.
  `npx ampx add data`.
- **Storage:** S3 bucket with per-user prefixes.
  `npx ampx add storage`.
- **Functions:** Lambda functions wired to API or storage triggers.
  `npx ampx add function`.

**Backend deploy in build phase:**

```bash
npx ampx pipeline-deploy --branch $AWS_BRANCH --app-id $AWS_APP_ID
```

This runs in the `build` phase of `amplify.yml` and deploys the CDK
stack for the branch. The build role needs `iam:PassRole` and the
CDK bootstrap (`CDKToolkit`) must exist in the account.

**Common mistake:** running `ampx push` (sandbox mode) in CI instead of
`ampx pipeline-deploy`. Sandbox mode is for local dev; CI uses
`pipeline-deploy` which reads the branch and app ID from Amplify env
vars.

### Step 8 — CI/CD pipeline (branch builds, preview URLs)

Amplify builds on every git push. Each branch gets its own URL.

```bash
# Enable PR previews (builds every PR branch)
aws amplify update-branch \
  --app-id dXXXX \
  --branch-name main \
  --pull-request-environment-name main \
  --output json

# Set up a staging branch environment
aws amplify create-branch \
  --app-id dXXXX \
  --branch-name staging \
  --stage PRODUCTION \
  --output json
```

**Branch environments:**
- `main` → production URL (`app.example.com`)
- `staging` → staging URL (`staging.example.com` or
  `staging.dXXXX.amplifyapp.com`)
- PR branches → preview URL (`pr123.dXXXX.amplifyapp.com`)

### Step 9 — Amplify Gen 2 latest features (2024-2026)

- **Amplify Gen 2 TypeScript CDK backend (2024-2025):** Replaces Gen 1's
  CLI mutation model. `amplify/backend.ts` with `defineBackend` is
  fully CDK; deployable via `npx ampx pipeline-deploy`. Backend is
  IaC, branch-aware, and composable with any CDK construct.
- **Branch-based backend environments (2024-2025):** Each git branch
  gets its own backend stack (Cognito, AppSync, S3) via
  `pipeline-deploy --branch`. PR previews include a full sandbox
  backend.
- **Amplify Build Image updates (2024-2025):** Node 20, Python 3.12,
  newer bundlers. Specify `amplifyBuildSpec: buildImage: amplify:nodejs-20`
  to pin.
- **Custom IAM roles for Amplify SSR compute (2024-2025):** Next.js SSR
  apps can pin a custom role for the SSR compute (instead of the
  auto-generated one) for least-privilege.
- **Secrets Manager integration (2024-2025):** Amplify reads Secrets
  Manager secrets at build time via the app's service role. No more
  plaintext env vars for secrets.
- **Amplify Studio for Gen 2 (2024-2025):** Visual UI builder for
  Gen 2 backends; generates `ui-components/` from Figma.

### Step 10 — Transit / networking edge cases

- **Amplify apps are public-internet by default.** There is no VPC
  attachment for Amplify build or SSR compute. If the backend (RDS,
  ElastiCache) is private, the Amplify build / SSR compute needs a
  NAT or VPC endpoint — typically via a Lambda in a VPC fronted by
  API Gateway.
- **CloudFront in front of Amplify** is supported but rare — Amplify
  already fronts the app with a managed CloudFront distribution. A
  second CloudFront in front is for custom WAF rules or origin
  selection.

## NEVER do these things (top 5)

1. **NEVER configure custom headers, redirects, or env vars only in
   the Console.** Console-configured values are overwritten on the
   next push that includes `amplify.yml`. Always commit `amplify.yml`
   with customHeaders, redirects, and env-var references.

2. **NEVER request the ACM certificate for a custom domain in a region
   other than us-east-1.** Amplify custom domains require the cert in
   us-east-1 regardless of where the app is deployed. A cert in
   us-east-2 cannot be attached.

3. **NEVER use `ampx push` (sandbox) in the CI build phase.** Sandbox
   mode is for local dev with hot reload. CI uses
   `npx ampx pipeline-deploy --branch $AWS_BRANCH` which deploys the
   branch-specific backend stack.

4. **NEVER deploy a Next.js SSR app as a SPA without the rewrite rule.**
   SSR-as-SPA produces 404 on dynamic routes (`/users/[id]`). Either
   use SSR (Amplify auto-detects) or SSG (`output: 'export'`) with a
   `/<*> -> /index.html status 200` rewrite.

5. **NEVER store secrets as plaintext environment variables.** Plaintext
   env vars are visible in the Console and in `amplify.yml` if
   committed. Use Secrets Manager references — Amplify reads the secret
   at build time via the service role.

**Additional critical mistakes:** never run one big `main` branch (use
branch previews); never assume env vars propagate across branches (they
are branch-scoped); never delete the auto-created SSR compute role for
Next.js SSR apps; never skip CDK bootstrap before the first Gen 2
backend deploy; never forget to validate the domain DNS CNAME before
the cert issues; never use `npm install` in CI (use `npm ci` for
reproducibility); never configure a second CloudFront in front of
Amplify without a documented reason (Amplify already fronts the app).

## Output format

```text
APP: <app-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Git provider: <CodeCommit | GitHub | GitLab | Bitbucket> (connection: <OAuth | service role>)
  [✓|✗] Repository: <repo-url> (amplify.yml committed: YES | NO)
  [✓|✗] Framework: <Next.js | React | Vue | Angular | Svelte> (version)
  [✓|✗] Rendering mode: <SSR | SSG | SPA | ISR>
  [✓|✗] Build settings: <amplify.yml phases: preBuild, build, postBuild>
  [✓|✗] Environment variables: <N plaintext, M Secrets Manager refs>
  [✓|✗] Custom headers: <HSTS, CSP, X-Frame-Options, ...>
  [✓|✗] Redirects: <SPA rewrite /<*> -> /index.html status 200; legacy 301s>
  [✓|✗] Custom domain: <domain> (ACM cert <arn> in us-east-1; DNS validated: YES | NO)
  [✓|✗] Backend (Gen 2): <auth Cognito, data AppSync, storage S3, functions Lambda>
  [✓|✗] CI/CD: <branch builds on every push; preview URLs on PRs>
  [✓|✗] Branch environments: <main=prod, staging=staging, PR=preview>
VERIFICATION_COMMANDS:
  aws amplify get-app --app-id <id>
  aws amplify list-branches --app-id <id>
  aws amplify get-domain-association --app-id <id> --domain-name <domain>
  aws acm describe-certificate --certificate-arn <arn> --region us-east-1
```

### Worked example — Next.js SSR with Gen 2 backend

```text
APP: prod-web
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Git provider: GitHub (connection: CodeConnections github-amplify, AVAILABLE)
  [✓] Repository: github.com/example/prod-web (amplify.yml committed: YES)
  [✓] Framework: Next.js 14
  [✓] Rendering mode: SSR (Amplify auto-provisions SSR compute role)
  [✓] Build settings: amplify.yml (preBuild: npm ci; build: ampx pipeline-deploy + npm run build)
  [✓] Environment variables: 3 plaintext (API_URL, NODE_ENV, NEXT_PUBLIC_API_URL), 1 Secrets Manager ref (STRIPE_SECRET_KEY)
  [✓] Custom headers: HSTS, X-Content-Type-Options nosniff, X-Frame-Options DENY, CSP default-src 'self'
  [✓] Redirects: /<*> -> /index.html status 200 (SPA fallback for static routes)
  [✓] Custom domain: app.example.com (ACM cert arn:aws:acm:us-east-1:111:certificate/abc in us-east-1; DNS validated: YES via Route 53)
  [✓] Backend (Gen 2): auth Cognito (user pool + identity pool), data AppSync GraphQL, storage S3 (per-user prefixes)
  [✓] CI/CD: branch builds on every push; preview URLs on PRs
  [✓] Branch environments: main=app.example.com, staging=staging.example.com, PR=pr<N>.dXXXX.amplifyapp.com
VERIFICATION_COMMANDS:
  aws amplify get-app --app-id dXXXX
  aws amplify list-branches --app-id dXXXX
  aws amplify get-domain-association --app-id dXXXX --domain-name example.com
  aws acm describe-certificate --certificate-arn arn:aws:acm:us-east-1:111:certificate/abc --region us-east-1
```

### Worked example — React SPA with S3 + CloudFront-equivalent

```text
APP: marketing-site
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Git provider: CodeCommit (connection: service role AWSAmplifyServiceRole)
  [✓] Repository: codecommit::us-east-1://marketing-site (amplify.yml committed: YES)
  [✓] Framework: React 18 (Vite)
  [✓] Rendering mode: SPA (client-side render, CDN-served)
  [✓] Build settings: amplify.yml (preBuild: npm ci; build: npm run build; artifacts: dist/**/*)
  [✓] Environment variables: 2 plaintext (VITE_API_URL, NODE_ENV)
  [✓] Custom headers: HSTS, X-Content-Type-Options nosniff
  [✓] Redirects: /<*> -> /index.html status 200 (SPA rewrite for React Router)
  [✓] Custom domain: marketing.example.com (ACM cert in us-east-1; DNS validated via Route 53)
  [✓] Backend (Gen 2): N/A (static SPA, no backend)
  [✓] CI/CD: branch builds on every push; main = production
  [✓] Branch environments: main=marketing.example.com, PR=pr<N>.dXXXX.amplifyapp.com
VERIFICATION_COMMANDS:
  aws amplify get-app --app-id dXXXX
  aws amplify list-branches --app-id dXXXX
  aws amplify get-domain-association --app-id dXXXX --domain-name example.com
```

### Worked example — PREREQUISITES_MISSING (no Git provider, no amplify.yml)

```text
APP: new-app
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✗] Git provider: NOT specified — need CodeCommit / GitHub / GitLab / Bitbucket + connection
  [✗] Repository: NOT specified — need repo URL with amplify.yml committed
  [✗] Framework: NOT specified — need Next.js / React / Vue / Angular / Svelte
  [✗] Rendering mode: NOT specified — need SSR / SSG / SPA / ISR
  [✗] ACM certificate: NOT specified — custom domain needs a cert in us-east-1
VERIFICATION_COMMANDS:
  aws codeconnections list-connections
  aws acm list-certificates --region us-east-1
  aws route53 list-hosted-zones
```

## Error handling

| Error | Cause | Fix |
|---|---|---|
| `Repository access denied` | PAT missing `repo` scope or connection PENDING | Re-auth the CodeConnections connection in the Console |
| `Build failed: command not found: ampx` | `npx ampx` not installed | Add `npm install -g @aws-amplify/backend-cli` to preBuild |
| `Next.js SSR compute role missing` | Role was deleted | Re-deploy the branch; Amplify recreates the role automatically |
| `Certificate validation timed out` | DNS CNAME missing | Add the ACM validation CNAME to Route 53 / third-party DNS |
| `CDK bootstrap not found` | `CDKToolkit` stack missing | `npx cdk bootstrap aws://<account>/<region>` before first Gen 2 deploy |
| `Environment variable not found on staging` | Var set only on `main` | Amplify env vars are branch-scoped; set on each branch |
| `404 on dynamic routes` | SSR deployed as SPA | Switch to SSR (auto-detected) or SSG with rewrite rule |

## Recent AWS features (2024-2026)

- **Amplify Gen 2 (2024-2025):** TypeScript CDK-based backend with
  `defineBackend`. Replaces Gen 1's `amplify init` / `amplify push`
  mutation model. Deploy via `npx ampx pipeline-deploy` in the build
  phase. Fully IaC, branch-aware, composable with any CDK construct.
- **Branch-based backend environments (2024-2025):** Each git branch
  gets its own backend stack (Cognito, AppSync, S3) via
  `pipeline-deploy --branch`. PR previews include a full sandbox
  backend, not just a frontend preview.
- **Secrets Manager integration (2024-2025):** Amplify reads Secrets
  Manager secrets at build time via the app's service role. Eliminates
  plaintext env vars for secrets. Configure via `customRules` in
  `update-app`.
- **Custom IAM roles for Amplify SSR compute (2024-2025):** Next.js SSR
  apps can pin a custom role for the SSR compute (instead of the
  auto-generated one) for least-privilege.
- **Amplify Build Image Node 20 (2024-2025):** Updated build image with
  Node 20, Python 3.12, newer bundlers. Pin via
  `buildImage: amplify:nodejs-20` in the app settings.
- **Amplify Studio for Gen 2 (2024-2025):** Visual UI builder for
  Gen 2 backends; generates `ui-components/` from Figma designs.
- **CodeConnections GA (2024-2025):** CodeConnections (formerly
  CodeStar connections) GA for GitHub, GitLab, Bitbucket. Replaces
  PAT-based auth for long-lived CI connections.

## Domain

AWS CloudOps / Amplify Application Provisioning, Git-Based CI/CD,
Frontend Hosting, and Serverless Backend Design.

## AWS documentation

- **AWS Amplify Hosting User Guide** — https://docs.aws.amazon.com/amplify/latest/userguide/welcome.html
- **Amplify Gen 2 Documentation** — https://docs.amplify.aws/gen2/
- **Amplify custom domains** — https://docs.aws.amazon.com/amplify/latest/userguide/custom-domains.html
- **Amplify buildspec (amplify.yml)** — https://docs.aws.amazon.com/amplify/latest/userguide/build-settings.html
- **Amplify redirects** — https://docs.aws.amazon.com/amplify/latest/userguide/redirects.html
- **CodeConnections** — https://docs.aws.amazon.com/codeconnections/latest/userguide/welcome.html
- **AWS CLI Amplify reference** — https://docs.aws.amazon.com/cli/latest/reference/amplify/
- **Amplify SSR for Next.js** — https://docs.amplify.aws/gen2/deploy-and-host/fullstack-branching-deployments/nextjs-app-router/
