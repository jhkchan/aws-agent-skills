# Eval prompt: ok-deny-list-strategy

Audit the following Organizations SCP configuration for effective permission
exposure. Emit the standard VERDICT block (TARGET, VERDICT, REASON,
FINDINGS, REMEDIATION).

Organization structure for audit:

Root (r-ok-deny-list-strategy):
  Attached SCPs:
    - FullAWSAccess (p-FULLAWSACCESS): {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"*","Resource":"*"}]}
    - GuardrailDeny (p-ok-deny-list-strategy-guard):
      {"Version":"2012-10-17","Statement":[{"Sid":"DenyLeave","Effect":"Deny","Action":"organizations:LeaveOrganization","Resource":"*"},{"Sid":"DenySecSvc","Effect":"Deny","Action":["guardduty:DeleteDetector","securityhub:DisableSecurityHub","config:DeleteConfigurationRecorder","cloudtrail:DeleteTrail"],"Resource":"*"},{"Sid":"DenyRootKeys","Effect":"Deny","Action":["iam:CreateAccessKey","iam:DeleteAccessKey"],"Resource":"arn:aws:iam::*:root"}]}
    - RegionLock (p-ok-deny-list-strategy-region):
      {"Version":"2012-10-17","Statement":[{"Sid":"DenyNonApprovedRegions","Effect":"Deny","NotAction":["iam:*","organizations:*","route53:*","cloudfront:*","waf:*","support:*"],"Resource":"*","Condition":{"StringNotEquals":{"aws:RequestedRegion":["us-east-1","us-west-2"]}}}]}

OU "Finance" (ou-fin-ok-deny-list-strategy):
  Parent: Root
  Attached SCPs:
    - FullAWSAccess: inherited
    - GuardrailDeny: inherited
    - RegionLock: inherited

Account 666666666666 "ok-deny-list-strategy-finance":
  Parent: OU "Finance"
  Attached SCPs:
    - FullAWSAccess: inherited
    - GuardrailDeny: inherited
    - RegionLock: inherited

Effective SCP evaluation for account 666666666666:
  - FullAWSAccess (Allow * on *) — present, inherited
  - GuardrailDeny — present, inherited
    - organizations:LeaveOrganization: DENIED
    - guardduty:DeleteDetector / securityhub:DisableSecurityHub / config:DeleteConfigurationRecorder / cloudtrail:DeleteTrail: DENIED
    - iam:CreateAccessKey / iam:DeleteAccessKey on root: DENIED
  - RegionLock — present, inherited
    - aws:RequestedRegion restriction to us-east-1, us-west-2: ACTIVE
    - Global services excluded via NotAction (iam, organizations, route53, cloudfront, waf, support)

Target being audited: Account 666666666666 (ok-deny-list-strategy-finance)
