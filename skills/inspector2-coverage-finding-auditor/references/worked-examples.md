# Inspector2 Coverage + Finding Auditor — worked examples (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Worked example — ECR STALE_MODERATE coverage (from Step 2)

**Worked example:** an ECR repo last scanned 45 days ago is in the
30–90 day ECR range → STALE_MODERATE → MEDIUM for production. Do NOT
compare 45 days against the EC2 threshold of 30 days (that would
incorrectly classify it as STALE_SEVERE/HIGH). The thresholds are
per-resource-type because EC2 is continuously scanned (so 7+ days is
already stale) while ECR is push-time scanned (so 30+ days is the
expected interval for a monthly release cadence).

## Worked examples — MEDIUM / LOW / COVERED and account-level aggregation format

*MEDIUM (stale ECR scan + MEDIUM CVE):*
```text
AUDIT ID: ecr-prod-stale-scan
RESOURCE: ECR/ecr-prod-payments
VERDICT: MEDIUM
REASON: ECR scanOnPush=true but lastScannedAt 45 days ago (STALE_MODERATE,
30-90 day ECR range) on production/PCI repo → MEDIUM per coverage matrix.
One OPEN MEDIUM CVE (CVE-2024-3456, node 18.19.0, CVSS 5.3) — no escalation
(not internet-reachable, not in KEV). Worst of (MEDIUM coverage gap,
MEDIUM finding) = MEDIUM.
COVERAGE: STALE_MODERATE
FINDINGS: 1 OPEN (0 CRITICAL, 0 HIGH, 1 MEDIUM, 0 LOW, 0 INFORMATIONAL)
REMEDIATION: Rebuild image with patched node 18.20+ and push to trigger
scanOnPush. Enable ECR enhanced scanning for continuous CVE re-evaluation.
```

*LOW (active coverage, single LOW CVE):*
```text
AUDIT ID: ec2-low-cve-only
RESOURCE: EC2/i-dev-sandbox-03
VERDICT: LOW
REASON: Active coverage (lastScannedAt < 7 days, SSM Online). One OPEN LOW
CVE (CVE-2024-9999, curl 7.81.0, CVSS 2.7) — not internet-reachable, not
in KEV. No escalation.
COVERAGE: ACTIVE
FINDINGS: 1 OPEN (0 CRITICAL, 0 HIGH, 0 MEDIUM, 1 LOW, 0 INFORMATIONAL)
REMEDIATION: Track in vulnerability backlog. Include in next patching cycle.
```

*COVERED (active ECR, zero open findings):*
```text
AUDIT ID: ecr-scanonpush-clean
RESOURCE: ECR/eci-prod-frontend
VERDICT: COVERED
REASON: scanOnPush=true, lastScannedAt < 24 hours (ACTIVE). Zero OPEN
findings at or above LOW. One SUPPRESSED finding (excluded from count).
COVERAGE: ACTIVE
FINDINGS: 0 OPEN (0 CRITICAL, 0 HIGH, 0 MEDIUM, 0 LOW, 0 INFORMATIONAL)
REMEDIATION: None required — actively scanned, zero open findings.
```

**Account-level aggregation (different format — use when auditing an
entire account/region, not a single resource):**

```text
ACCOUNT: 123456789012 | REGION: us-east-1
VERDICT: CRITICAL
REASON: 3 of 15 resources CRITICAL. i-prod-web-01 has OPEN CRITICAL CVE
confirmed internet-reachable. i-prod-db-01 UNCOVERED (SSM offline, prod).
ecr-prod-api scanOnPush=false with 2 OPEN HIGH CVEs.

RESOURCE SUMMARY:
  i-prod-web-01 (EC2)       — CRITICAL  [internet-reachable critical CVE]
  i-prod-db-01 (EC2)        — HIGH      [SSM offline, production uncovered]
  ecr-prod-api (ECR)        — HIGH      [scanOnPush=false + 2 open HIGH CVEs]
  lambda-report-gen (Lambda)— MEDIUM   [code scanning disabled, standard only]
  i-dev-sandbox-03 (EC2)    — COVERED   [active scan, zero open findings]

REMEDIATION: Fix i-prod-web-01 immediately (incident-response). Re-enroll
i-prod-db-01 in SSM. Enable scanOnPush on ecr-prod-api.
```
