# Eval prompt: session-start-iam-gap

Diagnose the following SSM Session Manager failure. Emit the
standard DIAGNOSIS block (SYMPTOM, ROOT_CAUSE, EVIDENCE,
LAYER_CHECK, FIX, VERIFICATION, VERDICT, NEXT_STEP,
ESCALATION_PATH).

Diagnosis reference: session-start-iam-gap
Account: 111111111111
Region: us-east-1
Instance-id: i-0abc123def456789a
Symptom: SessionFailsToStart (AccessDeniedException)

Recent diagnostic output:
- aws ssm start-session --target i-0abc123def456789a returned:
  "AccessDeniedException: User arn:aws:sts::111111111111:assumed-role/DevOpsRole/jacky
  is not authorized to perform: ssm:StartSession"
- session-manager-plugin --version: 1.2.612.0
- describe-instance-information: PingStatus=Active,
  LastPingDateTime=2026-08-10T10:00:00Z, AgentVersion=3.3.131.0,
  IsLatestVersion=true
- simulate-principal-policy on arn:aws:sts::111111111111:assumed-role/DevOpsRole/jacky:
  Denied for ssm:StartSession on
  arn:aws:ssm:us-east-1:111111111111:document/SSM-SessionManagerRunShell
- ec2 describe-vpc-endpoints: ssm, ssmmesages, ec2messages all present
  with PrivateDnsEnabled=true

Emit the standard DIAGNOSIS block.
