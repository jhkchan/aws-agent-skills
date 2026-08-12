---
description: Operate ACM certificate monitoring with production-grade defaults (DaysToExpiry tiered alarms, multi-region inventory, renewal status tracking, CAA conflict detection, multi-account audit via Organizations, certificate-to-LB mapping, PCA private cert monitoring). Emits an OPERATION_COMPLETED report with verification commands.
nl_triggers:
  - "acm certificate monitoring"
  - "certificate expiry alarm"
  - "days to expiry"
  - "certificate renewal status"
  - "caa record conflict"
  - "multi-account certificate audit"
  - "certificate load balancer mapping"
  - "acm pca monitoring"
  - "certificate inventory"
  - "certificate monitoring"
  - "acm audit"
  - "certificate caa check"
routes_to: acm-certificate-monitor-operator
---

# /aws:operate-acm-certificates

Activate the `acm-certificate-monitor-operator` skill and operate ACM
certificate monitoring with production-grade defaults.

## What it does

The skill walks the monitoring procedure and emits an
OPERATION_COMPLETED (or REVIEW_REQUIRED) report:

1. DaysToExpiry metric fundamentals (primary monitoring signal)
2. Certificate expiry alarm tiers (warning <30d, critical <7d)
3. Multi-region certificate inventory
4. Certificate renewal status tracking
5. DNS validation record verification
6. CAA record conflict detection (silent renewal blocker)
7. Certificate-to-load-balancer mapping
8. Multi-account audit via Organizations
9. Automated renewal failure detection
10. SNS notification on expiry alarm
11. Wildcard vs SAN coverage audit
12. Private certificate (ACM PCA) monitoring
13. Recent features (multi-region certs, EventBridge renewal events)

## When to use

- You need to audit ACM certificate expiry across regions or accounts.
- You want to set up DaysToExpiry CloudWatch alarms.
- You are investigating a certificate renewal failure.
- You suspect a CAA record conflict blocking renewal.
- You need a multi-account certificate inventory via Organizations.
- You need to map certificates to load balancers / CloudFront / API Gateway.
- You need to monitor private certificates via ACM PCA.

## When NOT to use

- **Issuing/provisioning new ACM certificates** — use ACM provisioning
  skills.
- **IAM server certificates** — not ACM managed.
- **Third-party CA certificate management** — not ACM.
- **S3 bucket TLS configuration** — use S3 skills.

## How to invoke

### Slash command

```
/aws:operate-acm-certificates
```

Then provide: account ID, region(s), certificate ARNs (or "all"),
warning and critical SNS topic ARNs, and whether multi-account audit
or PCA monitoring is needed.

### Natural language

Any of these routes to the same skill:

- "set up certificate expiry monitoring for my ACM certs"
- "check renewal status for all my certificates"
- "detect CAA record conflicts blocking renewal"
- "audit certificates across my organization"
- "map certificates to my load balancers"

### CLI routing

```bash
node cli/bin/cli.js route "acm certificate monitoring"
```

## Pipeline integration

This skill operates in **Phase 2 (Operate)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to monitor, audit,
or operate ACM certificates. The output report feeds into alerting
pipelines and downstream security audit skills.

## Example

```
You: /aws:operate-acm-certificates

     Set up expiry monitoring for my 5 ACM certs in us-east-1.
     Warning alarm at 30 days, critical at 7 days.
     SNS cert-warning-notifications and cert-critical-escalation.
     Check renewal status and CAA records.

Skill:
  ACM_MONITORING: 123456789012 (us-east-1) — 5 certificates
  VERDICT: OPERATION_COMPLETED
  FINDINGS:
    [info] All 5 certs have tiered DaysToExpiry alarms
    [info] No CAA conflicts, no renewal failures
  CHECKLIST:
    [✓] DaysToExpiry alarms: warning + critical for 5 certs
    [✓] Renewal status: 3 ELIGIBLE, 2 INELIGIBLE, 0 FAILED
    [✓] CAA records: 5 OK, 0 conflicts
    [✓] DNS validation: 5 verified
  VERIFICATION_COMMANDS:
    aws acm list-certificates --certificate-statuses ISSUED --region us-east-1
    aws cloudwatch describe-alarms --alarm-name-prefix acm-cert- --region us-east-1
```

## References

- Skill definition: `skills/acm-certificate-monitor-operator/SKILL.md`
- DNS and CAA validation guide: `skills/acm-certificate-monitor-operator/references/dns-and-caa-validation.md`
- Multi-account and PCA guide: `skills/acm-certificate-monitor-operator/references/multi-account-and-pca.md`
- Eval suite: `skills/acm-certificate-monitor-operator/evals/evals.json`
