---
description: Audit Route 53 record sets for missing health checks on failover/weighted/latency routing, dangling ALIAS targets, DNSSEC gaps on public zones, private-IP exposure, and TTL inconsistency.
nl_triggers:
  - "audit these Route 53 records"
  - "check DNS failover health"
  - "dangling Route 53 record"
  - "missing health check failover"
  - "DNSSEC not enabled"
  - "public hosted zone exposure"
  - "Route 53 TTL inconsistency"
  - "subdomain takeover DNS"
  - "weighted record no health check"
  - "failover PRIMARY no health check"
  - "DNS record audit"
  - "Route 53 misconfiguration"
  - "hardening DNS configuration"
routes_to: route53-record-auditor
---

# /aws:audit-route53-records

Activate the `route53-record-auditor` skill and audit one or more Route 53
record sets for DNS security, reliability, and configuration exposure.

## What it does

Reads a Route 53 record set (`list-resource-record-sets`) plus optional
zone-level metadata (`get-dnssec`, `get-hosted-zone`) and applies the
ordered classification logic:

1. Pre-flight zone metadata gate — short-circuit private hosted zones
   (no DNSSEC/exposure audit), validate record-set structure.
2. Dangling ALIAS detection — ALIAS to deleted S3 website / API Gateway
   is DANGLING/CRITICAL (takeover risk); ALIAS to deleted ELB /
   CloudFront / VPC endpoint is DANGLING/HIGH (NXDOMAIN outage).
3. Health-check coverage — failover PRIMARY without HealthCheckId is
   NO_HEALTH_CHECK/CRITICAL; weighted/latency without HealthCheckId is
   NO_HEALTH_CHECK/HIGH. Weight-0 and failover SECONDARY are NOT flagged.
4. DNSSEC gap — public zone without DNSSEC signing is DNSSEC_GAP/HIGH;
   signed but no DS at parent is DNSSEC_GAP/MEDIUM.
5. Public-zone exposure — RFC 1918 private IP in a public zone is
   CONFIG_GAP/HIGH (topology disclosure).
6. TTL consistency — TTL variance > 2x within a routing group is
   CONFIG_GAP/MEDIUM. ALIAS TTL is ignored (uses target's TTL).
7. Aggregation — worst finding wins (DANGLING > NO_HEALTH_CHECK >
   DNSSEC_GAP > CONFIG_GAP > OK).

Emits a deterministic VERDICT per record:

```text
RECORD: <name> (<type>, <routing-policy>)
VERDICT: NO_HEALTH_CHECK | DNSSEC_GAP | DANGLING | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
RISK: CRITICAL | HIGH | MEDIUM | LOW | OK
FINDINGS:
  - [CRITICAL] <finding description (Step Na)>
  - [HIGH] <finding description (Step Nb)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Route 53 record set and ask any of:

- "audit these Route 53 records"
- "is my DNS failover configured correctly?"
- "is this record dangling?"
- "do I need health checks on weighted records?"
- "is DNSSEC enabled on my zone?"
- "is my private IP exposed in a public zone?"
- "are my TTLs consistent?"

A bare hosted-zone-id or record name + any audit verb ("audit this
zone", "check DNS failover") also routes here via the orchestrator.

## Inputs

- One or more Route 53 record sets (`list-resource-record-sets` JSON),
  pasted inline or referenced by file path.
- Hosted-zone metadata: `Config.PrivateZone`, `DnssecSigning` status,
  `KeySigningKeys` array. These attributes drive the DNSSEC and exposure
  dimensions.
- For dangling detection: the target resource's existence status
  (confirmed via `describe-load-balancers`, `list-distributions`, etc.).
- For health-check validation: `HealthCheckId` presence on routing-policy
  records. Optionally, the health-check type (TCP vs HTTPS) for
  failure-semantics assessment.

## Outputs

- One VERDICT block per record (multiple findings aggregate to the worst
  severity).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation CLI per finding: `create-health-check`,
  `change-resource-record-sets`, `enable-hosted-zone-dnssec`,
  `create-key-signing-key`, plus verification commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Route 53 DNS security and reliability).
- `/aws:audit-kms-key-policy` for the KMS side of DNSSEC key-signing-key
  audits — the KMS key backing a Route 53 KSK needs both the DNSSEC
  signing AND the key policy to be sound.
- `/aws:audit-ecs-task-definition` or `/aws:audit-autoscaling-group` for
  the application-side health of endpoints that Route 53 health checks
  monitor.
