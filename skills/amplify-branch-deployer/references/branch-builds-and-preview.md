# Branch Builds and PR Preview — Amplify Branch Deployer

Deep reference on Amplify branch builds (auto-build on git push, manual
trigger via start-job, build instance types, build frequency), pull
request preview (ephemeral environment per PR, URL rotation, fixed
environment name for cost control), backend deployment via Amplify CLI
(one backend per branch), and CI/CD patterns. Loaded on demand by the
skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Branch build fundamentals

### Auto-build on git push

When `enableAutoBuild=true` (the default), Amplify triggers a build
automatically when a push lands on the connected branch. The Git
provider sends a webhook event to Amplify; no manual webhook
configuration is needed beyond the one-time OAuth.

```bash
# Create a branch with auto-build (default)
aws amplify create-branch \
  --app-id d2y0lrmp1qq2tu \
  --branch-name main \
  --stage PRODUCTION \
  --enable-auto-build

# Verify auto-build is enabled
aws amplify get-branch \
  --app-id d2y0lrmp1qq2tu \
  --branch-name main \
  --query 'branch.enableAutoBuild'
# true
```

### Manual trigger (disable auto-build)

For cost-sensitive or compliance-driven workflows, disable auto-build
and trigger manually:

```bash
# Disable auto-build
aws amplify update-branch \
  --app-id d2y0lrmp1qq2tu \
  --branch-name experiment \
  --no-enable-auto-build

# Trigger a build manually
aws amplify start-job \
  --app-id d2y0lrmp1qq2tu \
  --branch-name experiment \
  --job-type RELEASE
```

### Build instance types

| Type | RAM | When to use | Cost |
|---|---|---|---|
| `small` (default) | 4 GB | Simple static sites, small repos | Lowest |
| `medium` | 8 GB | Medium Next.js apps, moderate deps | Medium |
| `large` | 16 GB | Large monorepos, heavy SSR builds | Highest |

Larger instances speed up builds but cost more per build minute. For
frequent builds, the time savings can outweigh the per-minute cost
increase.

### Build frequency and quotas

Amplify has a monthly build-minute quota (free tier: 1000 build-minutes/
month). Each build consumes minutes proportional to (build duration x
instance multiplier). PR preview builds also consume minutes.

Monitor usage in the console: Amplify → Settings → Usage.

## Pull request preview

### How PR preview works

When `enablePullRequestPreview=true` on a branch, each PR targeting that
branch gets an ephemeral environment with a URL like
`https://pr-<n>.<app-id>.amplifyapp.com`.

```text
PR preview lifecycle:

  PR #42 opened (target: main)
    │
    ▼
  Amplify provisions ephemeral env at pr-42.<app-id>.amplifyapp.com
    │
    ├── New commit pushed to PR #42 → rebuild → content updates
    ├── PR #42 closed → environment torn down
    └── PR #42 reopened → new environment provisioned
```

**Key: the URL is ephemeral.** It rotates per build (content changes)
and is destroyed on PR close. It is NOT a stable staging URL. For
stable staging, use a dedicated `staging` branch.

### Enabling PR preview

```bash
aws amplify update-branch \
  --app-id d2y0lrmp1qq2tu \
  --branch-name main \
  --enable-pull-request-preview \
  --pull-request-environment-name pr-preview
```

### Cost control: fixed environment name

Without `pullRequestEnvironmentName`, each PR gets its OWN environment
— multiple PRs build in parallel, consuming many build-minutes. Set a
fixed name to reuse a single environment (only one PR builds at a time):

```bash
# Fixed environment: one PR builds at a time, lower cost
--pull-request-environment-name pr-preview

# No fixed name: each PR gets its own env, parallel builds, higher cost
# (omit --pull-request-environment-name)
```

**Trade-off:** fixed name = lower cost but PRs queue (one at a time).
No fixed name = parallel builds but higher cost. For teams with many
concurrent PRs, the parallel option may be worth the cost; for small
teams, the fixed name is more economical.

### PR preview with basic auth

PR preview environments can be protected with basic auth so only
authorized reviewers can access them:

```bash
aws amplify update-branch \
  --app-id d2y0lrmp1qq2tu \
  --branch-name main \
  --enable-pull-request-preview \
  --pull-request-environment-name pr-preview \
  --enable-basic-auth \
  --basic-auth-credentials "reviewer:s3cr3t"
```

## Backend deployment (Amplify CLI)

### One backend per branch

Amplify CLI provisions backend resources (AppSync, Cognito, DynamoDB,
S3, Lambda) per branch. Each branch = one isolated backend environment.

```text
Branch → Backend mapping:

  main     → prod backend (AppSync API prod-xxx, Cognito user pool prod-xxx)
  staging  → staging backend (separate resources)
  dev      → dev backend (separate resources)
  pr-42    → ephemeral backend (torn down with PR)
```

This isolation is a feature: each branch's backend is independent. A
deploy to `staging` does not affect `main`'s backend.

### IAM service role

Backend deploys need an IAM service role that Amplify assumes to
provision resources on your behalf:

```bash
aws amplify create-app \
  --name my-app \
  --repository https://github.com/org/my-repo \
  --iam-service-role-arn arn:aws:iam::123456789012:role/amplify-service-role
```

The service role needs permissions for CloudFormation, AppSync, Cognito,
DynamoDB, Lambda, S3, and IAM (for creating per-environment roles).

### Backend in amplify.yml

The `backend` section in `amplify.yml` runs the Amplify CLI to deploy
the backend:

```yaml
version: 1
backend:
  phases:
    build:
      - amplifyPush --simple
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

## CI/CD patterns

### Trunk-based with PR preview

```text
Feature branch → PR → main
                 │
                 ├── PR preview environment (ephemeral)
                 │
                 └── Merge to main → auto-build → production URL
```

### Git-flow with staging

```text
Feature → PR → develop → PR → main
                │              │
                ▼              ▼
          staging env     production env
```

### Multi-environment promotion

```text
main (PRODUCTION) → auto-build to production URL
  ├── release/1.0 → auto-build to a release env
  └── hotfix/*     → auto-build to hotfix envs
```

## Common pitfalls

### Pitfall 1: branch name typo

The branch name must match a real Git branch exactly. A typo silently
never builds.

**Fix:** verify the branch exists in the repo:

```bash
git ls-remote --heads https://github.com/org/my-repo
```

### Pitfall 2: auto-build disabled by mistake

If `enableAutoBuild=false`, no builds trigger on push. Verify:

```bash
aws amplify get-branch --app-id d2y0lrmp1qq2tu --branch-name main \
  --query 'branch.enableAutoBuild'
```

### Pitfall 3: PR preview consuming too many build minutes

Each PR without a fixed `pullRequestEnvironmentName` gets its own
environment. For repos with many concurrent PRs, this exhausts the
quota fast.

**Fix:** set a fixed environment name to reuse one environment.

### Pitfall 4: backend deploy fails due to missing service role

Without `iamServiceRoleArn` on the app, the `backend` phase cannot
provision resources.

**Fix:** attach a service role with the necessary permissions:

```bash
aws amplify update-app \
  --app-id d2y0lrmp1qq2tu \
  --iam-service-role-arn arn:aws:iam::123456789012:role/amplify-service-role
```
