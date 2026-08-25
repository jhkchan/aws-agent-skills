# Advanced Patterns (load on demand) — CloudWatch Synthetics Troubleshooter

Expert-knowledge deep dives, edge-case catalogs, and recent-feature notes moved verbatim from SKILL.md. Load on demand.

---

## Mindset — three facts that make Synthetics diagnosis different (moved from SKILL.md)

Three facts make Synthetics canary diagnosis different from generic
uptime monitoring:

- **A canary failure is often a canary-side problem.** The canary
  script, credentials, execution role, artifact bucket, and Visual
  Monitoring baseline can each cause FAILED even when the target is
  healthy. Operators who treat every canary failure as "endpoint down"
  waste incident-response time on the wrong target.

- **Visual Monitoring failures are NOT functional failures.** A
  `VisualMonitoringBaselineMismatch` means the screenshot differs from
  the baseline beyond tolerance. This can be a real UI break, a
  legitimate CSS change, a dynamic banner, a cookie popup, or a
  timezone-dependent clock. Treat Visual Monitoring failures as a
  separate triage path.

- **Canary timeout is the most over-diagnosed failure type.** A canary
  hitting `TimeoutInSeconds` may be slow because the target is slow,
  the script waits for a removed selector, the VPC networking is
  constrained, or the run frequency causes overlapping runs. "Raise
  the timeout" is the wrong first instinct.

## Expert heuristic — non-obvious canary failure behaviours (moved from SKILL.md)

- **Shared execution role across canaries.** A misconfigured IAM policy
  on the canary role can cause ALL canaries using that role to fail
  simultaneously. If multiple canaries fail at once, suspect the shared
  role, not each target endpoint.

- **Visual Monitoring baselines do not auto-update.** After a UI
  deployment, the baseline must be explicitly updated. A post-deploy
  canary failure with Visual Monitoring is expected behaviour, not a
  production incident.

- **VPC canaries route through the VPC, not the public internet.** A
  VPC-based canary that cannot reach a public endpoint likely has a VPC
  networking issue (NAT gateway, route table, security group), not an
  endpoint issue.

- **Canary run frequency causes overlap failures.** A canary running
  every minute that takes 90 seconds will overlap runs and consume
  concurrent slots. The service may fail overlapping runs with no clear
  error.

- **`describe-canary` does NOT include last run error details.** Use
  `describe-canary-runs` or `get-canary-runs` to retrieve the run
  report with error messages. Operators who only check
  `describe-canary` miss the diagnostic detail.

- **Blue/green canary deployments use a separate artifact bucket.** A
  misconfigured bucket policy or IAM role causes the canary to pull
  stale or missing artifacts, appearing as a runtime exception or
  "module not found."

- **Node.js canaries can swallow exceptions via unhandled promise
  rejections.** An un-awaited async call produces a generic
  `RUNTIME_ERROR` without a clear stack trace. Check for missing
  `.catch()` handlers.

- **Broken-link checker failures include third-party links.** A failing
  footer link (social media, analytics pixel) causes FAILED even though
  the application is fully functional. Filter third-party domains.

- **Canary recording (2025) captures HAR and screenshots for every
  run.** Failed runs include downloadable artifacts — always check the
  S3 artifacts before debugging the script.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Canary recording (2025):** failed and successful runs capture a HAR
  file and per-step screenshots by default. Always download and inspect
  artifacts from the S3 bucket before debugging the script.

- **Visual Monitoring enhancements (2024-2025):** improved screenshot
  comparison with configurable tolerance (percentage-based), ignore
  regions, and per-step baseline management. Baselines can be updated
  from any run via console or CLI.

- **Python runtime canaries (2024 GA):** `synthetics-python` runtime
  supports all five canary types. The Python `synthetics` module may
  lag the Node.js version — check `describe-runtime-versions` before
  suspecting a script bug.

- **VPC canary improvements (2024):** canaries can use VPC endpoints
  for AWS service targets, bypassing NAT gateway. Reduces NAT costs
  and eliminates NAT-related timeout failures.

- **Runtime version lifecycle (2024-2025):** runtime versions now have
  explicit deprecation dates. Plan upgrades before deprecation to avoid
  forced upgrades that break canary scripts.

- **Blue/green canary deployments (2025):** canaries support blue/green
  artifact deployment with active and standby in separate S3 paths.
  Misconfigured bucket policy or IAM role causes wrong/missing
  artifact pulls.

