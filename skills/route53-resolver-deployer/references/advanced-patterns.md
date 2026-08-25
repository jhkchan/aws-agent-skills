# Advanced Patterns — Route 53 Resolver Deployer

Step 0 expert knowledge and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

## Step 0: Expert knowledge — non-obvious Resolver behaviors

These behaviors are easy to misjudge without operational Resolver
experience. Each changes a plan if ignored:

- **Inbound endpoint IPs are the IPs on-prem forwards to.** The on-prem
  DNS server's forwarder config must point at the inbound endpoint IPs,
  not at the VPC CIDR. These IPs are assigned from the subnet CIDR and
  are visible in `get-resolver-endpoint` after creation.

- **Outbound endpoint IPs are the source IPs the on-prem DNS server
  sees.** The on-prem firewall ACL must allow UDP/TCP 53 from the
  outbound endpoint IPs (visible in `get-resolver-endpoint`). Mismatched
  firewall rules are the #1 cause of "forwarding rule works from a test
  EC2 instance but not from Resolver."

- **Forwarding rules match by longest suffix.** A rule for
  `corp.example.local.` matches `api.corp.example.local.` but NOT
  `corp.example.com.`. The trailing dot is significant.

- **Forwarding rules are SYSTEM or FORWARD.** `SYSTEM` (default AWS
  rule) resolves internet domains via Route 53. `FORWARD` sends to
  `TargetIps`. You cannot delete the SYSTEM rule; only associate or
  disassociate per VPC.

- **Rule associations are per-VPC.** Cross-account associations require
  sharing via RAM (`share-resolver-rule`) first — the #2 cause of "rule
  exists but my VPC does not use it" tickets.

- **DNS Firewall evaluates rule groups in priority order.** Priority 1
  is evaluated first; an ALLOW in priority 2 overrides a BLOCK in
  priority 1 for the same domain. Plan ordering before associating.

- **Firewall domain lists support wildcards.** `*.malware.example.`
  matches subdomains; bare `malware.example.` matches apex only.

- **BLOCK actions have a response.** `BlockResponse` is `NXDOMAIN`,
  `NODATA`, or `OVERRIDE` (custom DNS record — requires
  `BlockOverrideDnsType`, `BlockOverrideDnsValue`, `BlockOverrideTtl`).

- **Query logging has one association per VPC.** Switching destinations
  requires disassociating the old config first. Destinations need a
  resource policy granting `route53resolver.amazonaws.com` write access.

- **Resolver cache (2024-2026).** Configurable cache TTL on forwarding
  rules via `ResolverConfig`. Lower TTL = fresher data but more traffic.

## Recent AWS features (2024-2026)

- **Route 53 Resolver DNS Firewall (GA, enhanced 2024-2026):** managed
  domain lists for malware, botnet, and command-and-control domains,
  auto-updated by AWS. Custom domain lists support wildcard matching and
  bulk import. Rule group associations support `MutationProtection` to
  prevent accidental deletion.
- **Resolver cache (2024-2025):** configurable cache TTL on forwarding
  rules via `ResolverConfig`. Reduces forwarding traffic to on-prem DNS
  at the cost of stale-on-failover. Default remains uncached.
- **DNS Firewall ALERT action with CloudWatch metrics (2024-2025):**
  ALERT actions now emit CloudWatch metrics per rule group, enabling
  dashboards and alarms on DNS policy violations without blocking.
- **Query logging to Kinesis Data Firehose (2024-2025):** Firehose
  destinations now support direct delivery to OpenSearch, S3, and
  third-party SIEMs for long-term DNS query retention.
- **Cross-account rule sharing via RAM (enhanced 2024-2025):** forwarding
  rules can now be shared with OUs (not just individual accounts) via
  AWS RAM, simplifying multi-account Resolver topologies.
- **DNS Firewall OVERRIDE block response (2024-2025):** BLOCK actions can
  return a custom DNS record (e.g., a walled-garden IP) instead of
  NXDOMAIN/NODATA — useful for redirecting blocked domains to a
  remediation portal.
- **Resolver endpoint health checks via CloudWatch (2025-2026):**
  per-endpoint health metrics (query count, error rate, latency) for
  proactive monitoring and alarm automation.
