# Error handling - Amplify App Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.
| Error | Cause | Fix |
|---|---|---|
| `Repository access denied` | PAT missing `repo` scope or connection PENDING | Re-auth the CodeConnections connection in the Console |
| `Build failed: command not found: ampx` | `npx ampx` not installed | Add `npm install -g @aws-amplify/backend-cli` to preBuild |
| `Next.js SSR compute role missing` | Role was deleted | Re-deploy the branch; Amplify recreates the role automatically |
| `Certificate validation timed out` | DNS CNAME missing | Add the ACM validation CNAME to Route 53 / third-party DNS |
| `CDK bootstrap not found` | `CDKToolkit` stack missing | `npx cdk bootstrap aws://<account>/<region>` before first Gen 2 deploy |
| `Environment variable not found on staging` | Var set only on `main` | Amplify env vars are branch-scoped; set on each branch |
| `404 on dynamic routes` | SSR deployed as SPA | Switch to SSR (auto-detected) or SSG with rewrite rule |
