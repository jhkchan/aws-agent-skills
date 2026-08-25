# Advanced patterns - Amplify App Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.
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

- A Next.js SSR app needs the Amplify SSR compute role automatically
  created on first deploy — do not delete it.
- A custom domain on a third-party DNS (GoDaddy, Namecheap) needs the
  ACM validation CNAME copied manually; Route 53 does it automatically
  only if the hosted zone is in the same account.
- Amplify Gen 2 backend deploys in the build phase via
  `npx ampx pipeline-deploy --branch $AWS_BRANCH`. The role assumed by
  the Amplify build needs `iam:PassRole` + CDK bootstrapped in the
  account.

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

- **Amplify apps are public-internet by default.** There is no VPC
  attachment for Amplify build or SSR compute. If the backend (RDS,
  ElastiCache) is private, the Amplify build / SSR compute needs a
  NAT or VPC endpoint — typically via a Lambda in a VPC fronted by
  API Gateway.
- **CloudFront in front of Amplify** is supported but rare — Amplify
  already fronts the app with a managed CloudFront distribution. A
  second CloudFront in front is for custom WAF rules or origin
  selection.

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
