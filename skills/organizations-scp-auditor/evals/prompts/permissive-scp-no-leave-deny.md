# Eval prompt: permissive-scp-no-leave-deny

Audit the following Organizations SCP configuration for effective permission
exposure. Emit the standard VERDICT block (TARGET, VERDICT, REASON,
FINDINGS, REMEDIATION).

Organization structure for audit:

Root (r-permissive-scp-no-leave-deny):
  Attached SCPs:
    - FullAWSAccess (p-FULLAWSACCESS): {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"*","Resource":"*"}]}

OU "Production" (ou-prod-permissive-scp-no-leave-deny):
  Parent: Root
  Attached SCPs:
    - FullAWSAccess (p-FULLAWSACCESS): inherited from Root
    - DenyRootKeyCreation (p-permissive-scp-no-leave-deny-rootkeys):
      {"Version":"2012-10-17","Statement":[{"Sid":"DenyRootKeys","Effect":"Deny","Action":["iam:CreateAccessKey","iam:DeleteAccessKey"],"Resource":"arn:aws:iam::*:root"}]}

Account 111111111111 "permissive-scp-no-leave-deny-workload":
  Parent: OU "Production"
  Attached SCPs:
    - FullAWSAccess (p-FULLAWSACCESS): inherited

Effective SCP evaluation for account 111111111111:
  - FullAWSAccess (Allow * on *) — present at root, inherited
  - DenyRootKeyCreation (Deny iam:*AccessKey on root) — present at OU, inherited
  - organizations:LeaveOrganization: NOT denied anywhere in chain
  - guardduty:DeleteDetector / securityhub:DisableSecurityHub / config:DeleteConfigurationRecorder / cloudtrail:DeleteTrail: NOT denied anywhere

Target being audited: Account 111111111111 (permissive-scp-no-leave-deny-workload)
