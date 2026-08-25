# Worked Examples — Backup Compliance Automator

## Key details — NIST worked example
**Key details in this example:**

- **3 non-compliant resources** identified by resource ARN with last
  backup date for each.
- **Vault Lock GOVERNANCE vs LOCK_MODE** is the critical finding — NIST
  requires immutability that GOVERNANCE mode does not provide.
- **Restore drill overdue** by 28 days (118 days since last drill vs
  90-day policy). This is a separate finding from the stale backups.
- **FINDINGS severity** drives remediation priority: CRITICAL before
  HIGH, with specific CLI commands for each.

## Worked example — AUTOMATED (all gates passing)

```text
VAULT: soc2-production-vault (us-east-1)
VERDICT: AUTOMATED
CHECKLIST:
  [PASS] Compliance framework: SOC2 — 5 controls mapped, last evaluation 2026-08-11 02:00 UTC
  [PASS] Backup frequency audit: all 62 resources have last backup age <= 24h
  [PASS] Encryption verification: 62/62 recovery points encrypted
  [PASS] Retention compliance: Vault Lock LOCK_MODE, min 7d max 365d
  [PASS] Cross-region replication: configured, destination us-west-2
  [PASS] Legal hold: tested 2026-07-15 (create + release cycle documented)
  [PASS] Restore drill: last 2026-07-20, RTO 35min for EBS 1TB (within 90-day window)
  [PASS] Reporting: compliance report 2026-08-11 (within 24h SLA), coverage + job summary weekly
  [PASS] Cost allocation tags: active (Project, Environment, Compliance)
FINDINGS:
  - [INFO] Cross-region copy adds ~12% to per-job cost
  - [WARN] One member account (333333333333) missing cost tag: Project
REMEDIATION:
  1. Add Project tag to backup jobs in account 333333333333
```
