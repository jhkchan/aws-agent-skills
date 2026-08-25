# Error handling - Amplify Branch Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.
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
