# Eval prompt: inspector2-disabled-prod-ec2

Audit the Inspector2 coverage and finding posture for this account. Emit the
standard VERDICT block (RESOURCE, VERDICT, REASON, COVERAGE, FINDINGS,
REMEDIATION).

Account: 123456789012
Region: us-east-1

Inspector2 account status (batch-get-account-status):
  EC2: DISABLED
  ECR: ENABLED
  LAMBDA: ENABLED

Resource inventory:
  - i-prod-web-01 (EC2, t3.large, env=prod, critical=true)
  - i-prod-app-02 (EC2, t3.medium, env=prod)
  - ecr-prod-api (ECR, scanOnPush=true)

Coverage data (list-coverage):
  - ecr-prod-api: lastScannedAt=2026-08-01, status=ACTIVE, 0 open findings

Findings (list-findings, status=OPEN):
  (none — EC2 scanning disabled, no EC2 findings can exist)
