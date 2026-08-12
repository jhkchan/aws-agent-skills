---
name: amplify-branch-deployer
description: >-
  Configures AWS Amplify branch deployments with production defaults:
  app creation from a Git repository (GitHub/GitLab/Bitbucket),
  branch configuration (production/staging/dev with stage tags), build
  settings (amplify.yml — NOT buildspec.yml, environment variables,
  build instance type, cache configuration), custom headers, redirects
  (SPA rewrite vs SSR function routes), basic auth and password
  protection per branch, custom domain via Route 53 (domain association
  with sub-domain mapping), backend deployment via Amplify CLI (one
  backend per branch), CI/CD build frequency (continuous vs manual),
  notifications on build result (Slack/email), pull request preview
  (ephemeral environment per PR), monorepo app detection (amplify.yml
  in subdir + appRoot), SSR (Next.js Lambda serverless) vs SSG support,
  and Lambda serverless functions. Emits a READY_TO_DEPLOY checklist
  with verification commands. Use when creating an Amplify app,
  configuring a branch, setting up PR preview, wiring a custom domain,
  enabling basic auth, configuring SPA/SSR redirects, or detecting a
  monorepo app. Triggers: create amplify app, configure amplify branch,
  amplify pull request preview, amplify custom domain, amplify basic
  auth, amplify monorepo, amplify redirects spa ssr, amplify buildspec,
  amplify nextjs ssr, amplify serverless functions.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with amplify access
  and an existing Git provider connection (OAuth via console). Works
  with Terraform aws_amplify_app / aws_amplify_branch /
  aws_amplify_domain_association resources and CloudFormation
  AWS::Amplify::App / Branch / Domain templates.
keywords:
  - aws
  - amplify
  - branch
  - cloudops
  - deploy
  - devtools
  - git
  - build
  - pr preview
  - custom domain
  - basic auth
  - monorepo
  - redirects
  - ssr
  - nextjs
  - serverless functions
  - route 53
tags:
  - aws
  - amplify
  - amplify-branch
  - cloudops
  - deploy
  - devtools
  - cicd
  - ssr
  - monorepo
  - custom-domain
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: DevTools
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - amplify
    - amplify-branch
    - cloudops
    - deploy
    - devtools
    - cicd
    - ssr
    - monorepo
    - custom-domain
  dependencies:
    - aws-orchestrator
  keywords:
    - create amplify app
    - configure amplify branch
    - amplify pull request preview
    - amplify custom domain
    - amplify basic auth
    - amplify monorepo
    - amplify redirects spa ssr
    - amplify buildspec
    - amplify nextjs ssr
    - amplify serverless functions
  when_to_use: >-
    Invoke when the user wants to create an AWS Amplify app from a Git
    repository, configure a branch (production/staging/dev), enable pull
    request preview, wire a custom domain via Route 53, configure basic
    auth or password protection per branch, set up SPA or SSR redirects,
    detect a monoreto app via appRoot, or configure Next.js SSR with
    Lambda serverless functions. Do NOT invoke for Amplify Studio
    data modeling (use amplify-studio skills), AppSync API creation in
    isolation, or Cognito user pool configuration outside of an Amplify
    backend.
---

# Amplify Branch Deployer

An AWS CloudOps agent skill that configures AWS Amplify branch
deployments with correct defaults: branch auto-build on git push, PR
preview (ephemeral environment per PR), monorepo detection via appRoot,
custom domain via Route 53, basic auth per branch, SPA vs SSR redirects,
Next.js SSR via Lambda serverless functions, and the critical
distinction between `amplify.yml` (the Amplify build spec) and
`buildspec.yml` (CodeBuild's spec, which Amplify IGNORES). Emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create Amplify app, configure Amplify branch, Amplify PR preview,
Amplify custom domain, Amplify basic auth, Amplify monorepo, Amplify
redirects SPA SSR, Amplify build settings, Amplify Next.js SSR, Amplify
serverless functions.

## STRICT output contract

When this skill is invoked with an Amplify branch deployment request
(create an app, configure a branch, set up PR preview, wire a custom
domain, configure redirects, detect a monorepo, or enable basic auth),
the agent MUST respond with the READY_TO_DEPLOY checklist defined in the
"Output format" section using the literal all-caps labels `AMPLIFY:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface
with prose, headings, or disclaimers — emit the block as the first lines
of the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the literal
labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Steps 1-3 | App creation, branch config, build settings (amplify.yml) |
| Steps 4-6 | Redirects, custom headers, basic auth |
| Steps 7-9 | Custom domain, PR preview, monorepo |
| Steps 10-12 | SSR vs SSG, serverless functions, notifications |
| Step 13 | Recent features |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/branch-builds-and-preview.md | Branch + PR preview detail |
| references/domains-redirects-and-auth.md | Domain + redirect + auth detail |

## Mindset

**One-line takeaway:** Amplify builds on git push to a connected branch.
PR preview creates an ephemeral environment per PR. Monorepo detection
works via `amplify.yml` in a subdir plus the `appRoot` setting. The
build config file is `amplify.yml`, NOT `buildspec.yml`.

Three misconceptions dominate Amplify misdesign at provisioning time:

- **"Amplify uses buildspec.yml."** It does NOT. Amplify uses
  `amplify.yml` as its build spec. A `buildspec.yml` in the repo root is
  IGNORED. Operators familiar with CodeBuild assume `buildspec.yml` and
  are confused when their build commands don't run. The file must be
  `amplify.yml` at the repo root (or in the `appRoot` subdir for
  monorepos), OR configured inline in the console under "Build settings"
  (which the API stores as `customRules` + `buildSpec` on the app).

- **"PR preview is a stable staging URL."** It is NOT. PR preview
  creates an ephemeral environment per PR. The URL rotates per build.
  When the PR is closed or merged, the preview environment is torn down.
  It is NOT a permanent staging URL — use a dedicated `staging` branch
  for that.

- **"Monorepo support is automatic."** It is NOT automatic. Amplify
  looks for `amplify.yml` at the repo root by default. For a monorepo,
  you must either place `amplify.yml` in the app's subdir AND set
  `appRoot` on the Amplify app (via `create-app --app-root` or
  `update-app`), OR use the `enableAutoBranchCreation` pattern. Without
  `appRoot`, Amplify builds from the repo root and the subdir's app is
  invisible.

## Configuration dependency graph (novel heuristic)

Amplify configurations are NOT independent. A branch cannot be created
until the app exists and is connected to a Git repo. A custom domain
cannot be associated until at least one branch is deployed. PR preview
cannot fire until the branch is connected and auto-build is enabled.

| Configuration | Hard dependencies | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Amplify app | Git provider connection (OAuth via console); repo URL | IAM service role (optional) for backend deploys | Branches, domain |
| Git provider connection | One-time OAuth in console (GitHub/GitLab/Bitbucket) | Cannot be fully automated via CLI — must use console for first connection | App creation from repo |
| Branch | App exists; branch name matches a real Git branch | `enableAutoBuild=true` (default) triggers on push; `false` = manual only | Build, preview, domain mapping |
| Build settings (amplify.yml) | File at repo root OR `appRoot/amplify.yml` OR inline `buildSpec` on app | `buildspec.yml` is IGNORED — must be `amplify.yml` | Build phases, env vars, cache |
| Environment variables | Set on app (global) or branch (per-branch) | Branch-level overrides app-level; secrets are masked in logs | Build-time + runtime config |
| Custom domain | At least one branch deployed; DNS verification via Route 53 CNAME | DNS verification can take 15-45 min; SSL is auto-provisioned | Production URL mapping |
| Domain association | Domain verified; sub-domain maps to a branch | One branch per sub-domain; apex can map to one branch | `app.example.com → main`, `staging.example.com → staging` |
| PR preview | Auto-build enabled on the branch; `enablePullRequestPreview=true` | Preview URL rotates per build; torn down on PR close | Ephemeral environment per PR |
| Basic auth | Set per branch via `update-branch --basic-auth-credentials` | Applied at CDN edge; covers all paths under the branch domain | Password protection per branch |
| Redirects | `customRules` on app OR `amplify.yml` redirects section | SPA rewrite: `/<*>` to `/index.html` 200; SSR: function routes differ | Client-side routing, SSR routing |
| Monorepo (appRoot) | `appRoot` set on app; `amplify.yml` in appRoot subdir | Without appRoot, Amplify builds from repo root and misses the app | Sub-dir app detection |
| SSR (Next.js) | Framework detected; Lambda serverless functions provisioned | SSR requires `ssr` support; SSG is static hosting only | Server-rendered pages via Lambda |
| Serverless functions | `amplify.yml` functions section; Lambda provisioned per branch | One set of functions per branch/environment | API routes, SSR compute |

**The amplify.yml-vs-buildspec.yml row is the one a baseline model
misses.** Amplify ignores `buildspec.yml` entirely. The build spec must
be `amplify.yml` at the repo root (or `appRoot/amplify.yml` for
monorepos). This is the #1 cause of "my build commands don't run"
tickets.

**Cross-dependency gotchas:**
- A branch build will not trigger until the Git provider connection is
  established AND the branch name matches a real Git branch. A
  mis-typed branch name silently never builds.
- Custom domain association requires DNS verification. Route 53 CNAME
  records propagate quickly; third-party DNS can take 15-45 minutes.
- PR preview environments consume build minutes. High PR volume can
  exhaust the free tier or rack up costs — set `pullRequestEnvironmentName`
  to reuse a single environment if cost is a concern.
- SSR (Next.js) deploys Lambda functions per branch. Each branch = one
  set of Lambda functions. A repo with 10 active branches = 10 sets of
  Lambda functions.

## Expert heuristic: branch auto-builds on git push

A baseline model configures webhooks manually. The correct heuristic:
Amplify builds automatically on push to a connected branch — no webhook
configuration needed beyond the one-time Git provider OAuth.

```text
Amplify branch build flow:

  1. Developer pushes to branch "main" on GitHub
       │
       ▼
  2. Amplify receives push event via Git provider webhook (auto-wired)
       │
       ▼
  3. Amplify reads amplify.yml (NOT buildspec.yml!) from repo root
       ├── If monorepo: reads from appRoot/amplify.yml
       └── If no amplify.yml: uses console Build settings (buildSpec on app)
       │
       ▼
  4. Build runs on build instance (small/medium/large)
       ├── install phase (npm install / pip install)
       ├── build phase (npm run build / next build)
       └── post-build (test, deploy backend via Amplify CLI)
       │
       ▼
  5. Artifacts deployed to CDN; URL: https://<branch>.<app-id>.amplifyapp.com
       ├── Production branch → can map to custom domain
       └── PR branch → ephemeral preview URL
```

**Key implication:** the Git provider connection (one-time OAuth) is the
prerequisite. Without it, no builds trigger. The connection is
established in the Amplify console, NOT the CLI — the CLI can create
the app but the OAuth handshake requires console interaction.

## Expert heuristic: PR preview creates ephemeral environment

A baseline model assumes PR preview is a staging URL. The correct
heuristic: each PR gets its own ephemeral environment with a unique URL
that rotates per build and is torn down on PR close.

```text
PR preview lifecycle:

  PR #42 opened (target: main)
       │
       ▼
  Amplify provisions ephemeral environment
  URL: https://pr-42.<app-id>.amplifyapp.com  (rotates per build)
       │
       ├── New commit pushed to PR #42 → rebuild → new URL content
       ├── PR #42 closed/merged → environment torn down
       └── PR #42 reopened → new environment provisioned
```

**Key implication:** PR preview is for review, not staging. For a
stable staging URL, deploy a dedicated `staging` branch and map it to
`staging.example.com` via a domain association. PR preview URLs are
ephemeral and must not be shared as permanent links.

## Expert heuristic: monorepo detection via appRoot

A baseline model assumes Amplify finds the app automatically. The
correct heuristic: monorepo detection requires `appRoot` set on the app
PLUS `amplify.yml` in that subdir.

```text
Monorepo structure:

  my-monorepo/
  ├── packages/
  │   ├── web-app/           ← the Amplify app lives here
  │   │   ├── amplify.yml    ← build spec for this app
  │   │   ├── package.json
  │   │   └── src/
  │   ├── api/
  │   └── shared/
  ├── package.json           ← workspace root
  └── turbo.json
```

Without `appRoot=packages/web-app`, Amplify builds from the repo root,
finds no `amplify.yml` there, and fails or uses defaults. Set
`appRoot` at app creation:

```bash
aws amplify create-app \
  --name my-web-app \
  --repository https://github.com/org/my-monorepo \
  --app-root packages/web-app \
  --platform WEB
```

## Prerequisites (verify before provisioning)

If any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Git provider connection | Amplify needs OAuth access to the repo | Console → Amplify → App settings → Repository |
| Repository URL | App creation requires the Git clone URL | Confirm `https://github.com/<org>/<repo>` |
| Branch exists in Git | Branch name must match a real Git branch | `git ls-remote --heads <repo>` |
| `amplify.yml` or inline buildSpec | Build commands won't run without it | Check repo root (or `appRoot/`) for `amplify.yml` |
| IAM service role (for backend) | Backend deploys need a role for Amplify CLI | `aws iam get-role --role-name amplify-service-role` |
| Route 53 hosted zone (for custom domain) | Domain verification needs DNS control | `aws route53 list-hosted-zones` |
| Build instance type chosen | Affects build speed and cost | Choose `small` (default), `medium`, or `large` |
| Account build quota | Amplify has a monthly build-minute quota | Console → Amplify → Settings → Usage |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — App creation from Git repo

```bash
aws amplify create-app \
  --name my-app \
  --repository https://github.com/org/my-repo \
  --platform WEB \
  --iam-service-role-arn arn:aws:iam::123456789012:role/amplify-service-role \
  --build-spec "version: 1\nfrontend:\n  phases:\n    preBuild:\n      - npm install\n    build:\n      - npm run build\n  artifacts:\n    baseDirectory: .next\n    files:\n      - '**/*'\n  cache:\n    paths:\n      - node_modules/**/*"
```

**For a monorepo**, add `--app-root packages/web-app`.

The Git provider connection is established in the console (one-time
OAuth). The CLI creates the app but cannot perform the OAuth handshake.

## Step 2 — Branch configuration (production/staging/dev)

```bash
aws amplify create-branch \
  --app-id d2y0lrmp1qq2tu \
  --branch-name main \
  --stage PRODUCTION \
  --enable-auto-build \
  --environment-variables REACT_APP_API_URL=https://api.example.com,NODE_ENV=production
```

| Stage | Purpose | Auto-build | Typical domain |
|---|---|---|---|
| PRODUCTION | Live production | true | `app.example.com` (custom domain) |
| BETA | Pre-prod staging | true | `staging.example.com` (custom domain) |
| DEVELOPMENT | Dev integration | true | `dev.<app-id>.amplifyapp.com` |
| PULL_REQUEST | PR preview | true | `pr-<n>.<app-id>.amplifyapp.com` (ephemeral) |
| EXPERIMENTAL | Experiments | false (manual) | `exp.<app-id>.amplifyapp.com` |

**Common mistake:** typo in branch name. The branch name must match a
real Git branch exactly. A mis-typed name silently never builds.

## Step 3 — Build settings (amplify.yml, NOT buildspec.yml)

The canonical `amplify.yml` at repo root (or `appRoot/`):

```yaml
version: 1
frontend:
  phases:
    preBuild:
      - npm install
    build:
      - npm run build
  artifacts:
    baseDirectory: .next
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
```

**Critical:** this file is `amplify.yml`, NOT `buildspec.yml`. A
`buildspec.yml` in the same directory is IGNORED. If no `amplify.yml`
exists, Amplify uses the inline `buildSpec` on the app (settable via
console or `create-app --build-spec`).

Environment variables can be set on the app (global) or per-branch:

```bash
# App-level (all branches)
aws amplify update-app \
  --app-id d2y0lrmp1qq2tu \
  --environment-variables GLOBAL_VAR=value

# Branch-level (overrides app-level for that branch)
aws amplify create-branch \
  --app-id d2y0lrmp1qq2tu \
  --branch-name main \
  --environment-variables API_URL=https://api.prod.example.com
```

Build instance type: `small` (default, 4GB RAM), `medium` (8GB), `large`
(16GB). Larger instances speed up builds at higher cost.

## Step 4 — Redirects (SPA vs SSR)

Redirects and rewrites are configured via `customRules` on the app or in
`amplify.yml`. The pattern differs between SPA and SSR.

**SPA (React/Vue/Angular) — catch-all rewrite to index.html:**

```yaml
customRules:
  - source: /<*>
    target: /index.html
    status: 200
```

The `status: 200` (rewrite, not redirect) is critical: it serves
`index.html` for all paths so client-side routing handles them. A `301`
would redirect to the literal path `/index.html`.

**SSR (Next.js) — function routes:**

```yaml
customRules:
  - source: /api/<*>
    target: /api/[...path]
    status: 200
```

SSR routes are handled by Lambda serverless functions; the redirect
rules must not shadow the function routes. Amplify auto-detects Next.js
SSR routes from the build output.

**Common redirect patterns:**

```yaml
customRules:
  # Domain redirect (old → new)
  - source: old.example.com
    target: https://new.example.com
    status: 301
  # Path redirect
  - source: /old-path
    target: /new-path
    status: 302
  # SPA rewrite (catch-all)
  - source: /<*>
    target: /index.html
    status: 200
```

## Step 5 — Custom headers

Custom headers are set in `amplify.yml` under the `customHeaders` key
or per-route via `customRules`:

```yaml
customHeaders:
  - pattern: '**/*'
    headers:
      - key: Strict-Transport-Security
        value: 'max-age=31536000; includeSubDomains'
      - key: X-Frame-Options
        value: SAMEORIGIN
      - key: X-Content-Type-Options
        value: nosniff
  - pattern: '/static/*'
    headers:
      - key: Cache-Control
        value: 'public, max-age=31536000, immutable'
```

Security headers (HSTS, X-Frame-Options, CSP) should always be set for
production apps. Cache headers on static assets (`/static/*`) with
content hashing should use immutable caching.

## Step 6 — Basic auth per branch

Basic auth protects a branch with HTTP Basic Authentication at the CDN
edge. Useful for staging/preview environments that should not be public.

```bash
aws amplify update-branch \
  --app-id d2y0lrmp1qq2tu \
  --branch-name staging \
  --enable-basic-auth \
  --basic-auth-credentials base64-encoded-credentials
```

**Format:** the credentials are `username:password` (the API accepts the
raw string; the SDK base64-encodes). Anyone visiting the branch URL sees
a browser auth prompt. Basic auth applies to all paths under the branch
domain.

**Common use cases:**
- Staging branch behind auth during pre-launch
- Preview branches for internal review
- Compliance: preventing public access to non-production environments

## Step 7 — Custom domain via Route 53

```bash
aws amplify create-domain-association \
  --app-id d2y0lrmp1qq2tu \
  --domain-name example.com \
  --sub-domains \
    subDomainSetting=PRIMARY,branchName=main,prefix="" \
    subDomainSetting=PROD,branchName=staging,prefix="staging"
```

This maps:
- `example.com` (apex) → `main` branch (production)
- `staging.example.com` → `staging` branch

Amplify returns DNS records (CNAME for verification + A/AAAA alias) that
must be added to Route 53 (or third-party DNS):

```bash
# Get the DNS records Amplify needs
aws amplify get-domain-association \
  --app-id d2y0lrmp1qq2tu \
  --domain-name example.com \
  --query 'domainAssociation.subDomains[*].dnsRecord'
```

**Route 53 hosted zone:**

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1DXXXXXXXXXX \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "_amplify.example.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "<verification-value>.amplify.app"}]
      }
    }]
  }'
```

SSL is auto-provisioned once DNS verifies. Propagation: Route 53 ~2-5
min; third-party DNS 15-45 min.

## Step 8 — Pull request preview

```bash
aws amplify update-branch \
  --app-id d2y0lrmp1qq2tu \
  --branch-name main \
  --enable-pull-request-preview \
  --pull-request-environment-name pr-preview
```

Each PR targeting `main` gets an ephemeral environment at
`https://pr-<n>.<app-id>.amplifyapp.com`. The URL rotates per build
(a new push to the PR triggers a rebuild with new content). On PR close
or merge, the environment is torn down.

**Cost control:** set `pullRequestEnvironmentName` to a fixed name to
reuse a single environment across PRs (only one PR builds at a time).
Without a fixed name, each PR gets its own environment (parallel builds,
more build minutes).

## Step 9 — Monorepo app detection

For monorepos, set `appRoot` at app creation:

```bash
aws amplify create-app \
  --name my-web-app \
  --repository https://github.com/org/my-monorepo \
  --app-root packages/web-app \
  --platform WEB
```

Amplify then reads `packages/web-app/amplify.yml` for build settings.
Without `appRoot`, Amplify looks at the repo root and misses the app.

**Detect existing appRoot:**

```bash
aws amplify get-app \
  --app-id d2y0lrmp1qq2tu \
  --query 'app.appRoot'
```

**Update appRoot** (requires app update):

```bash
aws amplify update-app \
  --app-id d2y0lrmp1qq2tu \
  --app-root packages/web-app
```

## Step 10 — SSR (Next.js) vs SSG support

| Mode | How it works | Amplify support |
|---|---|---|
| SSG (Static Site Generation) | Build-time HTML; served as static files | Default; no special config |
| SSR (Server-Side Rendering) | Per-request HTML via Lambda serverless functions | Auto-detected for Next.js; Lambda provisioned per branch |
| ISR (Incremental Static Regeneration) | Static + on-demand regeneration | Supported via Next.js build output |

**Next.js SSR:** Amplify auto-detects Next.js from the build output and
provisions Lambda serverless functions for SSR routes. No special
`amplify.yml` config needed — the `next build` output includes SSR
metadata that Amplify consumes.

```yaml
# amplify.yml for Next.js SSR (standard — detection is automatic)
version: 1
frontend:
  phases:
    preBuild:
      - npm install
    build:
      - npm run build
  artifacts:
    baseDirectory: .next
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
```

**Key implication:** SSR deploys Lambda functions per branch. A repo
with 10 active branches = 10 sets of Lambda functions. Monitor Lambda
costs for high-traffic SSR apps.

## Step 11 — Lambda serverless functions

Amplify deploys Lambda serverless functions from the build output. These
power SSR pages, API routes, and custom compute.

```yaml
# amplify.yml — additional functions section for serverless functions
version: 1
frontend:
  phases:
    preBuild:
      - npm install
    build:
      - npm run build
  artifacts:
    baseDirectory: .next
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
functions:
  - src: api/hello
    name: hello-function
    runtime: nodejs18.x
    handler: handler.main
```

Functions are deployed per branch — each branch has its own set. They
are invoked via the branch URL under `/api/<function-name>`.

## Step 12 — Notifications on build result

```bash
# Create an SNS topic for build notifications
aws sns create-topic --name amplify-build-notifications

# Subscribe an email endpoint
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:amplify-build-notifications \
  --protocol email \
  --notification-endpoint team@example.com

# Wire Amplify to notify on build success/failure (via EventBridge)
aws events put-rule \
  --name amplify-build-result \
  --event-pattern '{
    "source": ["aws.amplify"],
    "detail-type": ["Amplify Build Result"],
    "detail": {"status": ["SUCCEED", "FAIL"]}
  }'

aws events put-targets \
  --rule amplify-build-result \
  --targets '[{"Id":"notify-sns","Arn":"arn:aws:sns:us-east-1:123456789012:amplify-build-notifications"}]'
```

For Slack notifications, use an SNS → Lambda → Slack webhook pattern, or
use AWS Chatbot to pipe SNS to Slack directly.

## Step 13 — Recent features

**Recent AWS features (2023-2026):**

- **SSR improvements for Next.js (2023-2024):** Amplify enhanced
  Next.js SSR support including App Router, Server Components, and
  Route Handlers. Lambda serverless functions provisioned automatically.
- **Monorepo `appRoot` GA (2023-2024):** `appRoot` graduated to a
  first-class setting on `create-app` / `update-app`, simplifying
  Turborepo and Nx monorepo detection.
- **Build instance type selection (2023-2024):** `small` (default),
  `medium`, `large` build instances for cost-vs-speed tradeoff.
- **Enhanced cache configuration (2024-2025):** build-time cache
  (npm/.m2) and CDN cache (`cacheConfig`) improvements for faster
  builds and better runtime performance.
- **CI/CD manual trigger (2024-2025):** `enableAutoBuild=false` lets
  teams trigger builds manually via `start-job`, useful for
  cost-sensitive or compliance-driven workflows.
- **Pull request preview cost control (2024-2025):** fixed
  `pullRequestEnvironmentName` to reuse a single environment across PRs
  (only one PR builds at a time), cutting build-minute consumption.

## NEVER do these things

1. **NEVER use `buildspec.yml` as the Amplify build spec.** Amplify uses
   `amplify.yml`. A `buildspec.yml` in the repo is IGNORED. This is the
   #1 cause of "my build commands don't run" tickets.

2. **NEVER assume PR preview is a stable staging URL.** PR preview
   environments are ephemeral — the URL rotates per build and the
   environment is torn down on PR close. Use a dedicated `staging`
   branch for a stable URL.

3. **NEVER assume monorepo detection is automatic.** Set `appRoot` on
   the app and place `amplify.yml` in the appRoot subdir. Without
   `appRoot`, Amplify builds from the repo root and misses the app.

4. **NEVER use status 301 for SPA client-side routing.** Use `status:
   200` (rewrite) for the catch-all `/<*>` → `/index.html` rule. A 301
   redirects to the literal path `/index.html`, breaking client-side
   routing.

5. **NEVER set a mis-typed branch name.** The branch name must match a
   real Git branch exactly. A typo silently never builds.

6. **NEVER assume the Git provider connection works via CLI alone.**
   The one-time OAuth handshake requires console interaction. The CLI
   can create the app but cannot perform OAuth.

7. **NEVER forget DNS verification for custom domains.** Domain
   association requires a CNAME record in Route 53 (or third-party
   DNS). Without verification, SSL is not provisioned and the domain
   stays in `CREATING` status.

8. **NEVER use one PR environment per PR for high-volume repos.** Each
   PR environment consumes build minutes. Set
   `pullRequestEnvironmentName` to a fixed name to reuse one
   environment (one PR builds at a time, lower cost).

9. **NEVER ignore SSR Lambda costs for multi-branch repos.** SSR deploys
   Lambda functions per branch. 10 active branches = 10 sets of Lambda
   functions. Monitor costs for high-traffic SSR apps.

10. **NEVER omit security headers in production.** Set HSTS,
    X-Frame-Options, X-Content-Type-Options, and CSP via `customHeaders`
    in `amplify.yml`. Production apps without security headers are
    vulnerable to clickjacking and MIME-sniffing attacks.

## Output format

```text
AMPLIFY: <app-name> (<app-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Git provider connection: <provider> (OAuth via console)
  [✓|✗] Repository: <repo-url>
  [✓|✗] App created: <app-id> (appRoot: <root-or-subdir>)
  [✓|✗] Build spec: amplify.yml at <location> | inline buildSpec on app
  [✓|✗] Branch: <branch-name> (stage: PRODUCTION|BETA|DEVELOPMENT, auto-build: true|false)
  [✓|✗] Build instance: small|medium|large
  [✓|✗] Environment variables: <app-level + branch-level list>
  [✓|✗] Redirects: SPA rewrite (/<*> → /index.html 200) | SSR function routes | custom
  [✓|✗] Custom headers: <security-header list>
  [✓|✗] Basic auth: enabled on <branch> | disabled
  [✓|✗] Custom domain: <domain> → <branch> (DNS verified | pending)
  [✓|✗] PR preview: enabled (environment: <name>) | disabled
  [✓|✗] Monorepo: appRoot=<subdir> | not a monorepo
  [✓|✗] SSR/SSG: SSR (Next.js, Lambda functions) | SSG (static)
  [✓|✗] Serverless functions: <count> (per branch)
  [✓|✗] Notifications: SNS/Slack on build result | none
VERIFICATION_COMMANDS:
  aws amplify get-app --app-id <app-id>
  aws amplify list-branches --app-id <app-id>
  aws amplify get-domain-association --app-id <app-id> --domain-name <domain>
```

### Worked example — production branch with custom domain and PR preview

```text
AMPLIFY: my-web-app (d2y0lrmp1qq2tu)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Git provider connection: GitHub (OAuth via console)
  [✓] Repository: https://github.com/org/my-web-app
  [✓] App created: d2y0lrmp1qq2tu (appRoot: packages/web-app — monorepo)
  [✓] Build spec: amplify.yml at packages/web-app/amplify.yml
  [✓] Branch: main (stage: PRODUCTION, auto-build: true)
  [✓] Build instance: medium
  [✓] Environment variables: NEXT_PUBLIC_API_URL (app), NODE_ENV=production (branch)
  [✓] Redirects: SPA rewrite (/<*> → /index.html 200)
  [✓] Custom headers: HSTS, X-Frame-Options, X-Content-Type-Options
  [✓] Basic auth: disabled on main; enabled on staging
  [✓] Custom domain: example.com → main (DNS verified, SSL active)
  [✓] PR preview: enabled (environment: pr-preview, reuses single env)
  [✓] Monorepo: appRoot=packages/web-app
  [✓] SSR/SSG: SSR (Next.js 14, Lambda functions auto-provisioned)
  [✓] Serverless functions: 3 (per branch)
  [✓] Notifications: SNS → Slack on build result
VERIFICATION_COMMANDS:
  aws amplify get-app --app-id d2y0lrmp1qq2tu
  aws amplify list-branches --app-id d2y0lrmp1qq2tu
  aws amplify get-domain-association --app-id d2y0lrmp1qq2tu --domain-name example.com
```

## Error handling

### Build commands don't run
- The build spec file is `amplify.yml`, NOT `buildspec.yml`. Check that
  `amplify.yml` exists at the repo root (or `appRoot/` for monorepos).
  If using inline spec, verify `buildSpec` on the app.

### Branch never builds
- The branch name doesn't match a real Git branch. Verify the exact
  branch name in the repo. Also check that auto-build is enabled
  (`enableAutoBuild=true`, the default).

### Custom domain stuck in CREATING
- DNS verification not complete. Check that the CNAME record Amplify
  returned is in Route 53 (or third-party DNS). Route 53 propagates in
  ~2-5 min; third-party DNS can take 15-45 min.

### PR preview not creating environments
- PR preview requires `enablePullRequestPreview=true` on the target
  branch AND auto-build enabled. Verify both. Also confirm the PR
  targets the configured branch (e.g., `main`).

### SPA routes return 404 on refresh
- Missing catch-all rewrite. Add a custom rule: `/<*>` → `/index.html`
  with `status: 200` (rewrite, not redirect). Without this, client-side
  routes break on direct URL access or refresh.

### Monorepo app not detected
- `appRoot` not set on the app. Set it via `update-app --app-root
  <subdir>`. Also verify `amplify.yml` exists in that subdir.

### Next.js SSR routes not working
- Amplify didn't auto-detect SSR. Ensure the build output (`.next/`)
  includes SSR metadata. If using a custom build command, make sure
  `next build` runs. For non-Next.js SSR, manual Lambda function
  configuration is required.

## Domain

AWS CloudOps / AWS Amplify Branch Deployment & Git-Driven CI/CD.

## AWS documentation

- **Amplify Hosting overview** — https://docs.aws.amazon.com/amplify/latest/userguide/welcome.html
- **Getting started (console)** — https://docs.aws.amazon.com/amplify/latest/userguide/getting-started.html
- **Branch deployments** — https://docs.aws.amazon.com/amplify/latest/userguide/branch.html
- **PR previews** — https://docs.aws.amazon.com/amplify/latest/userguide/pr-previews.html
- **Custom domains** — https://docs.aws.amazon.com/amplify/latest/userguide/custom-domains.html
- **Redirects** — https://docs.aws.amazon.com/amplify/latest/userguide/redirects.html
- **Build settings (amplify.yml)** — https://docs.aws.amazon.com/amplify/latest/userguide/build-settings.html
- **Monorepo support** — https://docs.aws.amazon.com/amplify/latest/userguide/monorepo.html
- **SSR (Next.js)** — https://docs.aws.amazon.com/amplify/latest/userguide/server-side-rendering-amplify.html
