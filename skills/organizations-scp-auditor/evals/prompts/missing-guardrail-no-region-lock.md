# Eval prompt: missing-guardrail-no-region-lock

Audit the following Organizations SCP configuration for effective permission
exposure. Emit the standard VERDICT block (TARGET, VERDICT, REASON,
FINDINGS, REMEDIATION).

Organization structure for audit:

Root (r-missing-guardrail-no-region-lock):
  Attached SCPs:
    - FullAWSAccess (p-FULLAWSACCESS): {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"*","Resource":"*"}]}
    - GuardrailDeny (p-missing-guardrail-no-region-lock-guardrails):
      {"Version":"2012-10-17","Statement":[{"Sid":"DenyLeave","Effect":"Deny","Action":"organizations:LeaveOrganization","Resource":"*"},{"Sid":"DenySecSvc","Effect":"Deny","Action":["guardduty:DeleteDetector","securityhub:DisableSecurityHub","config:DeleteConfigurationRecorder","cloudtrail:DeleteTrail"],"Resource":"*"},{"Sid":"DenyRootKeys","Effect":"Deny","Action":["iam:CreateAccessKey","iam:DeleteAccessKey"],"Resource":"arn:aws:iam::*:root"}]}

OU "Finance" (ou-fin-missing-guardrail-no-region-lock):
  Parent: Root
  Attached SCPs:
    - FullAWSAccess (p-FULLAWSACCESS): inherited
    - GuardrailDeny: inherited

Account 333333333333 "missing-guardrail-no-region-lock-prod":
  Parent: OU "Finance"
  Attached SCPs:
    - FullAWSAccess (p-FULLAWSACCESS): inherited
    - GuardrailDeny: inherited

Effective SCP evaluation for account 333333333333:
  - FullAWSAccess (Allow * on *) — present, inherited
  - GuardrailDeny — present, inherited
    - organizations:LeaveOrganization: DENIED
    - guardduty:DeleteDetector / securityhub:DisableSecurityHub / config:DeleteConfigurationRecorder / cloudtrail:DeleteTrail: DENIED
    - iam:CreateAccessKey / iam:DeleteAccessKey on root: DENIED
  - aws:RequestedRegion region-restriction SCP: NOT present anywhere in chain
  - No aws:ResourceTag tag-based access control SCP in chain
  - OU "Finance" handles regulated financial data (in-scope for MISSING_GUARDRAIL region check)

Target being audited: Account 333333333333 (missing-guardrail-no-region-lock-prod)
