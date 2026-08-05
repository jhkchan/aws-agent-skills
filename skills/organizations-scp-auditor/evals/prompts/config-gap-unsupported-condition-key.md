# Eval prompt: config-gap-unsupported-condition-key

Audit the following Organizations SCP configuration for effective permission
exposure. Emit the standard VERDICT block (TARGET, VERDICT, REASON,
FINDINGS, REMEDIATION).

Organization structure for audit:

Root (r-config-gap-unsupported-condition-key):
  Attached SCPs:
    - FullAWSAccess (p-FULLAWSACCESS): {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"*","Resource":"*"}]}
    - GuardrailDeny (p-config-gap-unsupported-condition-key-grd):
      {"Version":"2012-10-17","Statement":[{"Sid":"DenyLeave","Effect":"Deny","Action":"organizations:LeaveOrganization","Resource":"*"},{"Sid":"DenySecSvc","Effect":"Deny","Action":["guardduty:DeleteDetector","securityhub:DisableSecurityHub","config:DeleteConfigurationRecorder","cloudtrail:DeleteTrail"],"Resource":"*"}]}
    - DenyKmsOutsideLambda (p-config-gap-unsupported-condition-key-kms):
      {"Version":"2012-10-17","Statement":[{"Sid":"DenyKmsNonLambda","Effect":"Deny","Action":["kms:Decrypt","kms:GenerateDataKey*"],"Resource":"*","Condition":{"StringEquals":{"kms:ViaService":"lambda.us-east-1.amazonaws.com"}}}]}

OU "Data" (ou-data-config-gap-unsupported-condition-key):
  Parent: Root
  Attached SCPs:
    - FullAWSAccess: inherited
    - GuardrailDeny: inherited
    - DenyKmsOutsideLambda: inherited

Account 555555555555 "config-gap-unsupported-condition-key-store":
  Parent: OU "Data"
  Attached SCPs:
    - FullAWSAccess: inherited
    - GuardrailDeny: inherited
    - DenyKmsOutsideLambda: inherited

Effective SCP evaluation for account 555555555555:
  - FullAWSAccess (Allow * on *) — present, inherited
  - GuardrailDeny — present, inherited
    - organizations:LeaveOrganization: DENIED
    - guardduty:DeleteDetector / securityhub:DisableSecurityHub / config:DeleteConfigurationRecorder / cloudtrail:DeleteTrail: DENIED
  - DenyKmsOutsideLambda — present, inherited
    - Deny kms:Decrypt + kms:GenerateDataKey* WHERE kms:ViaService StringEquals lambda.us-east-1.amazonaws.com
    - NOTE: kms:ViaService is a KMS SERVICE-SPECIFIC condition key, NOT supported in SCPs
    - The condition silently never evaluates -> StringEquals on absent key is always FALSE -> Deny never applies

Target being audited: Account 555555555555 (config-gap-unsupported-condition-key-store)
