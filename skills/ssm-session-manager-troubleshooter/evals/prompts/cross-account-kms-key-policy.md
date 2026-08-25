# Eval prompt: cross-account-kms-key-policy

Diagnose the following cross-account SSM Session Manager failure.
Emit the standard DIAGNOSIS block.

Diagnosis reference: cross-account-kms-key-policy
Source account: 111111111111
Target account: 222222222222
Region: us-east-1
Instance-id: i-0ddd444eee555fff6 (in target account)
KMS key: arn:aws:kms:us-east-1:222222222222:key/abc123def456
Symptom: LatestFeature (cross-account session)

Recent diagnostic output:
- aws ssm start-session from source account returned:
  "AccessDeniedException: User arn:aws:sts::222222222222:assumed-role/CrossAcctSessionRole/jacky
  is not authorized to perform: kms:GenerateDataKey on
  arn:aws:kms:us-east-1:222222222222:key/abc123def456"
- simulate-principal-policy in target account on
  arn:aws:sts::222222222222:assumed-role/CrossAcctSessionRole/jacky:
  ssm:StartSession allowed, ssmmessages:* allowed.
- aws kms describe-key: KeyState=Enabled, MultiRegion=false.
- aws kms get-key-policy: Statement Principal =
  {"AWS":"arn:aws:iam::222222222222:root"} only (no source
  account principal).

Emit the standard DIAGNOSIS block.
