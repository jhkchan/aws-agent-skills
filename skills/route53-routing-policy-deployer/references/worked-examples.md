# Worked Examples — Route 53 Routing Policy Deployer

Secondary worked example output moved verbatim from SKILL.md. Loaded on demand.

## Perfect example output — PREREQUISITES_MISSING

```text
RECORD_SET: api.example.com A (routing policy: weighted)
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Hosted zone confirmed: Z1DABCDEFGHIJ (example.com)
  [✓] Routing policy: weighted
  [✓] Target(s) resolved: primary 10.0.0.10 (w=90), canary 10.0.0.20 (w=10)
  [✗] Health check(s): no HC ID provided for canary target 10.0.0.20 — weighted without HC sends 10% of traffic to a possibly-dead target for the whole TTL window. Create HC before applying.
  [—] Change-batch: deferred until HC exists
  [OPTIONAL] Optional feature: none
  [✗] TTL applied: cannot set without HC confirmation (60s recommended for canary)
VERIFICATION_COMMANDS:
  aws route53 list-health-checks --query 'HealthChecks[?HealthCheckConfig.FullyQualifiedDomainName==`api.example.com`]'
```
