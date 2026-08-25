# clb-to-alb-migration-operator — advanced patterns (moved from SKILL.md)

Progressive-disclosure reference. Content below was moved verbatim from SKILL.md; the agent loads it only when needed.

## Cost/time baselines (2026)

- ALB: $0.0225/hour + $0.008 per LCU-hour (dimensioned on connections,
  bytes, rule evaluations). CLB is a flat hourly — ALB usually cheaper
  for L7 workloads.
- ALB target groups: free. Route 53 weighted routing: $0.50/million
  queries (first billion free).
- ACM certificates: free if issued via ACM. Cross-zone: ALB always on
  and free; CLB was billable.
- WAF on ALB: $5/rule/month + $1/million requests. ALB Lambda target
  invocations: billed as Lambda (no extra ALB fee).

## Step 0: Expert knowledge — non-obvious CLB/ALB behaviors

These behaviors are easy to misjudge without migration experience. Each
changes a plan if ignored:

- **TCP/SSL listeners cannot move to ALB.** ALB supports HTTP and HTTPS
  only. A CLB with a `TCP:443` listener (SSL passthrough) must either
  terminate SSL at the ALB (requires the cert and accepting L7
  inspection) or migrate to an NLB. The skill flags this and routes the
  listener to NLB planning — do NOT silently drop the listener.

- **Sticky session semantics differ.** CLB `LBCookieStickinessPolicy`
  generates a load-balancer-generated cookie. ALB `stickiness.type=lb_
  cookie` does the same with `AWSELB` cookie. CLB `AppCookieStickiness
  Policy` honors an application cookie name. ALB `stickiness.type=app_
  cookie` does the same. The names look equivalent but the cookie
  lifetime semantics differ: CLB's app-cookie stickiness refreshed the
  expiration on every response; ALB's `app_cookie` does too, but the
  `duration_seconds` is a fallback only if the application does not set
  the cookie. Test stickiness post-cutover.

- **Health check semantics differ.** CLB health check `Target: HTTP:8080
  /healthz` used the `HTTP:` prefix and combined port + path. ALB
  separates them: `HealthCheckPort: 8080`, `HealthCheckPath: /healthz`,
  `HealthCheckProtocol: HTTP`. The matcher is also stricter on ALB —
  `Matcher.HttpCode: 200` matches only 200 by default; CLB matched 200
  by default. Mismatched matchers cause post-cutover unhealthy targets
  even though the application is fine.

- **Proxy Protocol is the silent killer.** If the backend application
  parses the Proxy Protocol binary frame (common for gaming, IoT, and
  legacy Go services using `ProxyProto` libraries), ALB will break it
  silently — ALB injects `X-Forwarded-*` headers but no Proxy Protocol
  frame. The first symptom is "all requests 400 Bad Request" or
  "connection reset" because the backend tries to parse HTTP as a Proxy
  Protocol frame. Always check the CLB's `ProxyProtocolPolicyType` and
  inspect the backend's listener configuration before cutover.

- **DNS cutover is not instant.** Clients cache the CLB DNS name's
  underlying IP for the TTL (default 60s). Weighted routing cutover
  (5%/25%/50%/100% over hours) is the safe path for high-traffic
  workloads. Direct swap is safe for low-traffic internal services.

- **The CLB stays alive during rollback.** Do NOT delete the CLB at
  cutover. Keep it provisioned for the rollback window (typically
  24-72 hours). Rollback = flip the Route 53 weighted record back to
  100/0 (CLB/ALB). Deleting the CLB prematurely is irreversible.

- **Cross-zone on ALB changes distribution.** A CLB with cross-zone off
  distributes per-AZ; ALB always cross-zone spreads evenly across all
  targets. If any target is sized for AZ-only load, it may be
  overwhelmed by ALB's even distribution.

## Expert heuristic — the top 5 non-obvious signals

A senior migration engineer checks these five things first when a plan
looks "too clean." Each flips a READY verdict to BLOCKED if missed:

1. **Proxy Protocol on the backend listener.** Check the CLB policy list
   for `ProxyProtocolPolicyType` AND inspect the backend application's
   listener config (nginx `proxy_protocol on;`, HAProxy `accept-proxy`,
   Go `ProxyProto` library). Either side enabling it without the other
   breaks 100% of requests. ALB has no Proxy Protocol emission —
   backends must read X-Forwarded-For.

2. **TCP/SSL listeners hiding in the policy list.** A CLB named "web"
   may still have a `TCP:4242` listener for an admin protocol. The
   listener list is the source of truth, not the name. Any TCP/SSL
   listener routes to NLB planning, not ALB.

3. **IAM-uploaded certificates (not ACM).** A cert ARN starting with
   `arn:aws:iam::` is IAM-uploaded; renewal is manual and there is no
   free managed rotation. Plan to re-issue via ACM before or during
   migration so the ALB gets free managed renewal. ACM certs are free
   and auto-renew.

4. **Deregistration delay mismatch.** The CLB's `ConnectionDraining`
   timeout maps to the ALB target group's
   `deregistration_delay.timeout_seconds`. Defaults are both 300s, but a
   CLB tuned to 60s will leave the ALB at 300s — targets drain slowly
   during rollback, leaving the operator confused. Always read the CLB
   attribute and set the ALB target group to match.

5. **Cross-zone off on CLB.** A CLB with cross-zone off distributes
   per-AZ. Targets in AZ-a only serve AZ-a traffic. ALB is always
   cross-zone, so post-cutover traffic spreads evenly. If any target is
   sized for AZ-only load (smaller instances in one AZ), it may be
   overwhelmed by ALB's even distribution. Pre-scale or rebalance
   targets before cutover.

## Recent AWS features (2024-2026)

- **ALB with Lambda targets (2024 GA):** ALB can invoke Lambda
  functions as targets, with multi-value headers and request/response
  mapping. Useful for replacing CLB-backed API endpoints with serverless
  functions without an API Gateway. No Proxy Protocol; the Lambda event
  includes the original HTTP request.

- **ALB with OIDC authentication (2024 GA):** ALB can authenticate users
  via Amazon Cognito user pools or any OIDC-compliant IdP before
  forwarding to the target. This was a common reason teams added API
  Gateway in front of CLB; ALB now does it natively. Configure via
  `authenticate-cognito` or `authenticate-oidc` action in a listener
  rule.

- **WAF on ALB (2024-2026 enhancements):** AWS WAF can be attached to
  an ALB with managed rule groups (SQLi, XSS, bot control, IP reputation,
  common RuleSet). CLB had no WAF attachment. Post-migration, enable WAF
  for defense-in-depth.

- **TLS 1.3 on ALB (`ELBSecurityPolicy-TLS13-1-2-2021-06`, 2024):** ALB
  supports TLS 1.3 with forward secrecy and 0-RTT. CLB's best was TLS
  1.2. Migrating unlocks modern TLS; do not carry over the CLB's older
  policy.

- **ALB HTTP/2 and gRPC (2024):** ALB supports HTTP/2 natively and gRPC
  routing via listener rules. CLB was HTTP/1.1 only. Migrating unlocks
  multiplexed connections and gRPC-aware routing.

- **ALB weight-based target group forwarding (2025):** A listener rule
  action can forward to multiple target groups with weights (e.g., 90%
  blue / 10% green) for native blue/green deployments without Route 53.
  CLB required Route 53 weighted for the same effect.

- **Cross-zone load balancing always on (ALB, 2024-2026):** Confirmed
  always-on and free on ALB. CLB was off by default and billable. Any
  CLB with cross-zone off will see different distribution post-migration.
