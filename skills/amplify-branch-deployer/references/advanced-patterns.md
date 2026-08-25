# Advanced patterns - Amplify Branch Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.
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

A baseline model configures webhooks manually. The correct heuristic:
Amplify builds automatically on push to a connected branch — no webhook
configuration needed beyond the one-time Git provider OAuth.

```text
Amplify branch build flow:

  1. Push to branch "main" → Git provider fires webhook (auto-wired)
  2. Amplify reads amplify.yml (NOT buildspec.yml!) from repo root
       ├── Monorepo: reads from appRoot/amplify.yml
       └── No amplify.yml: uses console Build settings (buildSpec on app)
  3. Build runs on instance (small/medium/large) — install, build, test
  4. Artifacts → CDN; URL: https://<branch>.<app-id>.amplifyapp.com
       ├── Production branch → can map to custom domain
       └── PR branch → ephemeral preview URL
```

**Key implication:** the Git provider connection (one-time OAuth) is the
prerequisite. Without it, no builds trigger. The connection is
established in the Amplify console, NOT the CLI — the CLI can create
the app but the OAuth handshake requires console interaction.

A baseline model assumes PR preview is a staging URL. The correct
heuristic: each PR gets its own ephemeral environment with a unique URL
that rotates per build and is torn down on PR close.

```text
PR preview lifecycle:
  PR #42 opened (target: main)
    → env at https://pr-42.<app-id>.amplifyapp.com (rotates per build)
    → new commit → rebuild → content updates
    → PR closed/merged → environment torn down
```

**Key implication:** PR preview is for review, not staging. For a
stable staging URL, deploy a dedicated `staging` branch and map it to
`staging.example.com` via a domain association. PR preview URLs are
ephemeral and must not be shared as permanent links.

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

| Mode | How it works | Amplify support |
|---|---|---|
| SSG (Static Site Generation) | Build-time HTML; static files | Default; no special config |
| SSR (Server-Side Rendering) | Per-request HTML via Lambda functions | Auto-detected for Next.js; Lambda per branch |
| ISR (Incremental Static Regeneration) | Static + on-demand regeneration | Supported via Next.js build output |

**Next.js SSR:** Amplify auto-detects Next.js from the build output and
provisions Lambda serverless functions for SSR routes. No special
`amplify.yml` config needed — the `next build` output includes SSR
metadata that Amplify consumes.

**Key implication:** SSR deploys Lambda functions per branch. A repo
with 10 active branches = 10 sets of Lambda functions. Monitor Lambda
costs for high-traffic SSR apps.

```bash
# SNS topic + email subscription
aws sns create-topic --name amplify-build-notifications
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:amplify-build-notifications \
  --protocol email --notification-endpoint team@example.com

# EventBridge rule on build result
aws events put-rule --name amplify-build-result \
  --event-pattern '{"source":["aws.amplify"],"detail-type":["Amplify Build Result"],"detail":{"status":["SUCCEED","FAIL"]}}'

aws events put-targets --rule amplify-build-result \
  --targets '[{"Id":"notify-sns","Arn":"arn:aws:sns:us-east-1:123456789012:amplify-build-notifications"}]'
```

For Slack, use SNS → Lambda → Slack webhook, or AWS Chatbot to pipe SNS
to Slack directly.

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
