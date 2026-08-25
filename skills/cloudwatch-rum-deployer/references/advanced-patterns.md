# Advanced Patterns (load on demand) — CloudWatch RUM Deployer

Edge-case catalog, config-choice heuristics, and recent AWS features moved verbatim from SKILL.md. The provisioning steps, contract, and NEVER list remain in SKILL.md.


---

## Edge-case handling (moved from SKILL.md)

- **Sessions not appearing in dashboard:** the domain in
  `AllowedOrigins` is missing scheme or port. RUM matches scheme +
  host + port exactly; `https://checkout.example.com` differs from
  `checkout.example.com`. Always include `https://`.
- **Browser console `AccessDenied` on `PutRumEvents`:** the guest
  role lacks the permission, or the resource ARN in the policy
  does not match the app monitor ARN. Check `iam get-role-policy`.
- **X-Ray traces not correlating:** server-side sampling rule is
  0%, or the server's X-Ray SDK is not propagating the
  `X-Amzn-Trace-Id` header. Inspect server-side X-Ray SDK config.
- **Custom events rejected:** event `type` contains a hyphen or
  special character. Use snake_case (`checkout_complete`, not
  `checkout-complete`).
- **Cookie domain rejected:** the cookie domain does not match the
  page URL host. The browser ignores the cookie and session
  stitching breaks. Verify the domain with `document.cookie` in
  DevTools.
- **Ad blockers suppressing telemetry:** uBlock Origin and
  similar block the RUM CDN script. RUM cannot bypass this;
  expect 5-15% session under-count in adblock-heavy audiences.
  Document the limitation; do not attempt to evade adblockers.
- **Application Signals correlation empty:** the server workload
  is not enabled for Application Signals, or the RUM domain does
  not match the server's `AWS_SERVICE_NAME`-derived endpoint.
- **Multi-Region apps:** RUM does not merge across Regions. Plan
  per-Region app monitors and per-Region dashboards.

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **RUM Application Signals correlation (2025):** the
  `AWS/ApplicationSignalsClient` namespace auto-populates when both
  Application Signals (server) and RUM (client) cover the same
  service endpoint. Surfaced as a client node in the service map.

- **RUM custom metrics (2024-2025):** `put-metrics-destination` on
  the app monitor emits CloudWatch custom metrics from custom
  event data. Up to 100 metric definitions per app monitor.

- **Web Vitals INP (Interaction to Next Paint) GA (2024-2025):**
  RUM captures INP as the successor to FID. The dashboard surfaces
  both during the transition period.

- **Extended SDK versioning (2024-2025):** the SDK is versioned
  independently of the service. Pin the version in the CDN script
  tag (`aws-rum-web@1.18.0`) — auto-upgrades can break event
  schemas.

- **RUM with Application Signals SLOs (2025):** Application
  Signals SLOs can reference client-side metrics (Latency,
  Availability) sourced from RUM via the
  `AWS/ApplicationSignalsClient` namespace. Client-side SLOs are
  now first-class.

- **Cookie domain strict validation (2024-2025):** cookie domains
  must match the page URL host exactly or be a parent domain.
  Invalid cookie domains are silently dropped (no error in the
  SDK; sessions just don't persist across navigation).

- **Session event batching (2024-2025):** the SDK batches events
  up to 3 MB before calling `PutRumEvents`. Tunable via
  `batchLimitMB`. Lower for low-bandwidth mobile; raise for high-
  bandwidth desktop.

- **CORS strict origin matching (2024-2025):** the allow-list
  matches scheme + host + port exactly. Wildcards are not
  supported; explicit subdomain entries are required.

---

## Expert heuristic — enabling RUM and choosing config (moved from SKILL.md)

- **Sample rate vs. cost.** RUM charges per `PutRumEvents` call.
  At 100% sample rate and 1M daily sessions, expect ~$300/month
  per app monitor. Drop to 10% for high-traffic sites; raise to
  100% for low-traffic beta deploys.
- **Cookie domain defaults to the current host.** This is correct
  for single-subdomain apps; multi-subdomain apps must set the
  parent domain explicitly. When in doubt, omit and observe
  session continuity.
- **Telemetries: declare all three at init.** errors, performance,
  http. Adding telemetry later requires a code change. Removing
  one (e.g., `http` for privacy) is a deliberate choice.
- **Custom event types: snake_case only.** Hyphens and special
  characters are rejected silently. Establish a naming convention
  (`<domain>_<action>`, e.g., `checkout_complete`).
- **Guest role ARN resource lock.** Scope `rum:PutRumEvents` to
  the specific app monitor ARN. Wildcard policies let any
  malicious script write events to any app monitor in the
  account.
- **X-Ray correlation needs server-side header propagation.**
  Confirm the server reads `X-Amzn-Trace-Id` and joins the trace.
  Without propagation, RUM captures client-side traces only.
- **Ad blockers cannot be bypassed.** Expect 5-15% under-count in
  adblock-heavy audiences. Document the limitation; do not
  attempt to evade.
