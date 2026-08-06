# Eval prompt: ecr-scanonpush-clean

Audit the Inspector2 coverage and finding posture for this resource. Emit the
standard VERDICT block (RESOURCE, VERDICT, REASON, COVERAGE, FINDINGS,
REMEDIATION).

Resource: eci-prod-frontend (ECR, env=prod)
Region: us-east-1

Inspector2 account status:
  ECR: ENABLED

Coverage:
  - eci-prod-frontend: lastScannedAt=2026-08-04, status=SUCCESSFUL, scanOnPush=true
    (last push was 2 hours ago)

Findings (status=OPEN):
  (none)

Findings (status=SUPPRESSED):
  - 1 SUPPRESSED (package removed in latest image rebuild)

Network reachability: N/A.
