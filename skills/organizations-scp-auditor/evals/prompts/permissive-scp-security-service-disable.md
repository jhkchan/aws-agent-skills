# Eval prompt: permissive-scp-security-service-disable

Audit the following Organizations SCP configuration for effective permission
exposure. Emit the standard VERDICT block (TARGET, VERDICT, REASON,
FINDINGS, REMEDIATION).

Organization structure for audit:

Root (r-permissive-scp-security-service-disable):
  Attached SCPs:
    - FullAWSAccess (p-FULLAWSACCESS): {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"*","Resource":"*"}]}
    - DenyLeaveOrg (p-permissive-scp-security-service-disable-leave):
      {"Version":"2012-10-17","Statement":[{"Sid":"DenyLeave","Effect":"Deny","Action":"organizations:LeaveOrganization","Resource":"*"}]}

OU "Logging" (ou-logs-permissive-scp-security-service-disable):
  Parent: Root
  Attached SCPs:
    - FullAWSAccess (p-FULLAWSACCESS): inherited from Root
    - DenyLeaveOrg: inherited from Root

Account 222222222222 "permissive-scp-security-service-disable-logs":
  Parent: OU "Logging"
  Attached SCPs:
    - FullAWSAccess (p-FULLAWSACCESS): inherited
    - DenyLeaveOrg: inherited

Effective SCP evaluation for account 222222222222:
  - FullAWSAccess (Allow * on *) — present, inherited
  - DenyLeaveOrg (Deny organizations:LeaveOrganization) — present, inherited
  - organizations:LeaveOrganization: DENIED
  - guardduty:DeleteDetector: NOT denied anywhere in chain
  - securityhub:DisableSecurityHub: NOT denied anywhere in chain
  - config:DeleteConfigurationRecorder: NOT denied anywhere in chain
  - cloudtrail:DeleteTrail: NOT denied anywhere in chain

Target being audited: Account 222222222222 (permissive-scp-security-service-disable-logs)
