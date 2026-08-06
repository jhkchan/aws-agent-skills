# Eval prompt: ecr-prod-stale-scan

Audit the Inspector2 coverage and finding posture for this resource. This case
exercises the stale-scan edge: the ECR repo was scanned 45 days ago and ECR
only scans at push time. Emit the standard VERDICT block (RESOURCE, VERDICT,
REASON, COVERAGE, FINDINGS, REMEDIATION).

Resource: ecr-prod-payments (ECR, env=prod, compliance=pci)
Region: us-east-1

Inspector2 account status:
  ECR: ENABLED

Coverage:
  - ecr-prod-payments: lastScannedAt=2026-06-15, status=SUCCESSFUL, scanOnPush=true
    (last image push was 45 days ago; ECR scans only at push time)

Findings (status=OPEN):
  - findingId: arn:aws:inspector2:us-east-1:123456789012:finding/ghi-012
    type: PACKAGE_VULNERABILITY
    severity: MEDIUM
    cve: CVE-2024-3456
    affectedPackage: node
    affectedVersion: 18.19.0
    cvssScore: 5.3
    description: Node.js HTTP request smuggling vulnerability.

Network reachability: N/A (ECR image, not a running instance).
KEV catalog: CVE-2024-3456 is NOT in the CISA KEV catalog.
