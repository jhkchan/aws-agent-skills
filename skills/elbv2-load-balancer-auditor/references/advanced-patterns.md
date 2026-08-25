# ELBv2 Load Balancer Auditor — advanced patterns (load on demand)

Expert-knowledge deep dives, edge cases, and recent features, moved verbatim from SKILL.md.

## Step 0 — expert knowledge: non-obvious ELBv2 behaviors that change classification (moved verbatim from SKILL.md lines 85-171)


These behaviors are easy to misjudge without operational ELBv2 experience.
Each changes a verdict if ignored:

- **ALB cross-zone load balancing is ALWAYS ENABLED.** It cannot be disabled.
  Never flag an ALB for cross-zone being off — it is not a configurable
  attribute. Only NLB has the toggle (off by default).

- **ELBSecurityPolicy-2016-08 is the AWS default SslPolicy.** It includes TLS
  1.0 and 1.1, both deprecated by PCI-DSS (3.2.1+, effective 2018) and
  NIST SP 800-52r2. The default policy is insecure by modern standards — most
  production ALBs carry this finding without anyone knowing.

- **NLB TCP (non-TLS) listeners have no SslPolicy.** Traffic passes through
  unencrypted at L4. Do NOT flag a TCP listener for missing TLS — it is by
  design. Only TLS-protocol listeners have an SslPolicy to evaluate. If
  end-to-end encryption is required, the application must handle it.

- **HTTP listener with redirect-to-HTTPS is a SECURE pattern.** The standard
  ALB hardening pattern is HTTP:80 → redirect to HTTPS:443. Do NOT flag an
  HTTP listener that has a redirect action. Only flag an HTTP listener that
  forwards cleartext traffic with no HTTPS listener present.

- **Access logs silently fail if the S3 bucket policy is wrong.** The bucket
  must grant `elasticloadbalancing.amazonaws.com` the `s3:PutObject`
  permission with an `aws:SourceAccount` condition matching the LB owner
  account. AccessLogsEnabled may be `true` but logs never appear. This skill
  checks the `enabled` flag; the bucket-policy check is a live-account
  follow-up (not classifiable from the LB config alone).

- **NLB access logs have a 5-minute delivery granularity minimum.** ALB logs
  are emitted per-request; NLB logs are aggregated in 5-minute windows. A
  low-traffic NLB may produce very few log objects — do not confuse this with
  logs being disabled.

- **Deletion protection blocks delete-load-balancer.** When enabled,
  `aws elbv2 delete-load-balancer` returns
  `OperationNotPermittedException`. Operators who do not know this waste time
  debugging "permission denied" that is actually a safety feature. The
  remediation note must explain: disable deletion protection first, then
  delete.

- **ALB security group controls LB ingress, NOT target ingress.** The ALB SG
  governs client→LB traffic. Target SGs govern LB→target traffic. A common
  misconfiguration is opening the target SG to 0.0.0.0/0 "because the ALB
  handles security" — this exposes targets directly, bypassing the ALB.

- **WAF is ALB-only.** WAFv2 Web ACL association is available for ALB, not
  NLB (NLB is L4). Do not suggest WAF as remediation for an NLB finding.

- **Target group deregistration delay defaults to 300 seconds.** During
  deregistration, targets are in `draining` state — they receive in-flight
  requests but no new ones. An LB with all targets `draining` is effectively
  idle but not flagged as IDLE unless zero targets are `healthy` or
  `unhealthy` (i.e., `unused` or empty).

- **ALB attribute `routing.http.x_amzn_tls_version_and_cipher_suite.enabled`
  is OFF by default.** Without it, access logs show source IP, path, and
  status but NOT the negotiated TLS version or cipher suite. A successful
  downgrade attack (client forced to TLS 1.0) is invisible in the logs —
  the request line is indistinguishable from a TLS 1.3 request. This means
  NO_ACCESS_LOGS understates the forensic gap: even with logs enabled, you
  are TLS-blind unless this attribute is on. Treat a `false` value here as
  an amplifier on any INSECURE_LISTENER finding — without it, you cannot
  reconstruct which requests were downgraded, so the incident-response
  scope is unknowable.

- **NLB default health check is TCP-level, not application-level.**
  `HealthCheckConfig.Type` defaults to `TCP` for NLB target groups — a
  successful TCP handshake marks the target `healthy` even when the
  application is returning 500s or serving the wrong content. A target
  group flagged healthy may be a dead app at L7. This makes the IDLE
  verdict unreliable for NLB unless `health_check.type` is HTTP/HTTPS with
  a real `path`. Always inspect the health-check type before trusting a
  `healthy` status on an NLB target group; a TCP check on an HTTP target
  produces a false non-IDLE verdict (the LB has "healthy" targets that are
  actually broken, and users see 502/503 with no IDLE flag raised).

- **NLB `preserve_client_ip.enabled` defaults differ by listener protocol:
  enabled for TCP, disabled for TLS.** Behind a TLS-terminated NLB, targets
  see the NLB's private IP, not the client IP. IP-based rate limiting,
  geo-blocking, or source-IP audit logging on targets silently breaks when
  migrating a listener from TCP to TLS termination. The target SG must
  allow the NLB subnet CIDR for TLS listeners — not the original client
  CIDRs. A common SG-audit false positive is flagging the target SG for
  "only allowing the NLB subnet" when the fronting listener is TLS: that
  is the *correct* posture for TLS-terminated NLBs, not a permissive gap.

## Deep reference — ELBv2 TLS security policy catalog (moved verbatim from SKILL.md lines 589-658)


### How SslPolicy negotiation works

When a TLS client connects to an ALB or NLB TLS listener, the LB selects the
highest mutually supported protocol version and cipher suite from the
SslPolicy. If the policy includes TLS 1.0, a client that only supports TLS 1.0
will negotiate TLS 1.0 — the server cannot force an upgrade. This is why
including TLS 1.0/1.1 in the policy is dangerous even if modern clients use
1.2+: an attacker performing a downgrade attack can force the weaker protocol.

### ELBSecurityPolicy naming convention

- `FS` prefix: Forward Secrecy (all cipher suites provide PFS via ECDHE/DHE).
- `TLS13` prefix: includes TLS 1.3 cipher suites.
- `TLS-1-2` / `TLS-1-0`: indicates the minimum TLS version.
- `Res` suffix: resizable cipher suite (for FIPS 140-2 compliance).
- `Ext` suffix: extended compatibility (includes broader cipher set).

### ALB vs NLB TLS termination

- **ALB HTTPS listener:** Terminates TLS at the ALB. The SslPolicy controls
  client→ALB negotiation. Backend traffic (ALB→target) uses the target group
  protocol (HTTP or HTTPS) — a separate encryption decision.
- **NLB TLS listener:** Terminates TLS at the NLB. Same SslPolicy model as
  ALB. Backend traffic can be re-encrypted (TLS to target) or plaintext.
- **NLB TCP listener:** No TLS termination. Traffic passes through at L4.
  No SslPolicy to evaluate. The application must handle encryption.

### Operational edge cases (deep reference)

These are production-experience insights that affect remediation ordering and
post-remediation validation, but do not change the verdict classification:

- **SslPolicy modification only affects NEW TLS handshakes.** Existing
  connections keep their negotiated parameters until closed. After updating a
  TLS 1.0 policy, an attacker with an active TLS 1.0 session retains it until
  TCP close or idle timeout. Incident-response for INSECURE_LISTENER must
  include force-closing existing connections (temporarily lower the idle
  timeout or cycle the listener), not just updating the policy.

- **TLS 1.3 cipher suites are protocol-fixed, not SslPolicy-controlled.**
  When an ELBSecurityPolicy-TLS13-* policy is used, TLS 1.3 cipher negotiation
  follows RFC 8446 — the policy cipher list applies only to TLS 1.2 and below.
  A TLS 1.3-capable client always gets a strong cipher regardless of the
  policy's TLS 1.2 cipher ordering. But a TLS 1.2-only client falls back to
  the policy's 1.2 cipher list — so weak 1.2 ciphers in a TLS13 policy are
  still a finding.

- **ALB idle timeout (60s default) cascades to backend connections.** The
  timeout applies to BOTH frontend (client→ALB) and backend (ALB→target)
  connections. If the target's keep-alive exceeds 60s, the ALB sends a TCP
  RST — the application sees a connection error, not a clean close.
  Long-polling or WebSocket workloads need the timeout raised to match the
  target's keep-alive.

- **Health-check interval vs deregistration delay timing.** If
  `health_check.interval_seconds * unhealthy_threshold_count` exceeds the
  deregistration delay, a failing target may be deregistered before the health
  check marks it unhealthy. The LB continues sending traffic to the failing
  target during the gap. Always verify the timing relationship.

- **Multiple ALBs sharing the same S3 access-log prefix produce interleaved
  logs.** The S3 path includes the LB ARN hash, but the user-controlled prefix
  is the primary organizational key. Each ALB should have a unique prefix
  (e.g., `prod-web`, `prod-api`) to avoid log collision.

- **NLB static IPs vs ALB dynamic IPs.** NLB provides one static IP per AZ
  that never changes for the LB's lifetime. ALB IPs can change when the ALB
  scales. NLB is the only choice when static IPs are required — but migrating
  ALB→NLB loses WAF, content-based routing, and HTTP-level features.

## Recent AWS features (2024-2026) (moved verbatim from SKILL.md lines 661-665)


- **TLS 1.3 support on ALB (2024):** ALB now supports TLS 1.3 for listener connections. Auditors should verify that the security policy is updated to include TLS 1.3 while maintaining a minimum of TLS 1.2.
- **mTLS on NLB (2024-2025):** NLB now supports mutual TLS (mTLS) for TCP listeners. Auditors should verify that mTLS is enabled on NLBs fronting internal APIs and that certificate revocation checking is configured.
- **ALB routing enhancements (2024):** Weighted routing, hostname-based routing, and query-string-based routing improvements. No new audit-surface fields, but auditors should verify that routing rules do not inadvertently bypass WAF rules on specific paths.
- **Capacity reservations integration:** ALB integration with Capacity Reservations for more predictable scaling. No direct audit-surface change.
