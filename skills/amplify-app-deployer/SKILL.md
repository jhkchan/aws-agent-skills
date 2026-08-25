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

Senior-engineer behaviours (buildspec as source of truth; rendering mode;
DNS validation before cert issue): [references/advanced-patterns.md](references/advanced-patterns.md).

## Philosophy

Provisioning philosophy (Gen 2 over Gen 1; branch environments; Secrets
Manager env vars; committed headers): [references/advanced-patterns.md](references/advanced-patterns.md).

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
Full catalog (SSR compute role, third-party DNS validation, ampx IAM
+ CDK bootstrap): [references/advanced-patterns.md](references/advanced-patterns.md).

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

Full customHeaders + redirects YAML (HSTS, CSP, 301s, SPA rewrite):
[references/build-and-domain-reference.md](references/build-and-domain-reference.md).

**Common mistake:** Console-configuring headers and redirects. They are
overwritten on the next push that includes `amplify.yml`. Always commit.

### Step 6 — Custom domain (Route 53 / CloudFront)

A custom domain uses an ACM certificate with DNS validation.

ACM cert request + domain-association commands:
[references/build-and-domain-reference.md](references/build-and-domain-reference.md).

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

Gen 2 backend resource catalog (auth/data/storage/functions) + build-phase
pipeline-deploy contract: [references/backend-gen2-reference.md](references/backend-gen2-reference.md).

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

Gen 2 feature detail (CDK backend, branch backends, build image, SSR
roles, Secrets Manager, Studio): [references/advanced-patterns.md](references/advanced-patterns.md).

### Step 10 — Transit / networking edge cases

Transit/networking edge cases (no VPC attachment, NAT for private
backends, second CloudFront): [references/advanced-patterns.md](references/advanced-patterns.md).

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

Further worked examples (React SPA static site; PREREQUISITES_MISSING with
no Git provider / no amplify.yml): [references/worked-examples.md](references/worked-examples.md).


## Error handling

Error-to-cause-to-fix table (repo access, ampx missing, SSR role, cert
timeout, CDK bootstrap, 404s): [references/error-handling.md](references/error-handling.md).

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026) — Gen 2, branch backends, Secrets
Manager, Node 20, Studio, CodeConnections: [references/advanced-patterns.md](references/advanced-patterns.md).

## References (load on demand)

- [Worked examples](references/worked-examples.md) - further checklists: React SPA static site; PREREQUISITES_MISSING (no Git provider / no amplify.yml)
- [Error handling](references/error-handling.md) - error-to-cause-to-fix table: repo access, ampx missing, SSR role, cert validation, CDK bootstrap, branch-scoped env vars, 404s
- [Advanced patterns](references/advanced-patterns.md) - senior-engineer behaviours, philosophy tenets, cross-dependency gotchas, Gen 2 features, networking edge cases, recent AWS features
- [Build and domain reference](references/build-and-domain-reference.md) - deep buildspec + domain detail: custom headers/redirects YAML, ACM cert request + domain association commands
- [Gen 2 backend reference](references/backend-gen2-reference.md) - Gen 2 backend patterns: resource catalog, pipeline-deploy build-phase contract

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
