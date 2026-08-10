# Eval prompt: failed-s3-access-denied

Diagnose the following SSM association failure. Emit the standard
DIAGNOSIS block (SYMPTOM, ROOT_CAUSE, EVIDENCE, LAYER_CHECK, FIX,
VERIFICATION, VERDICT, NEXT_STEP, ESCALATION_PATH).

Diagnosis reference: failed-s3-access-denied
Account: 111111111111
Region: us-east-1
Association-id: 0123456789abcdef0123456789abcdef0123456789abcdef0
Association name: prod-inventory-collect
Instance-id: i-0abc123def456789a
Symptom: Failed

Recent diagnostic output:
- describe-association-executions Status=Failed,
  StatusMessage="AccessDenied on s3:PutObject for arn:aws:s3:::ssm-output-prod/..."
- describe-instance-information: PingStatus=Active,
  LastPingDateTime=2026-08-10T10:00:00Z, AgentVersion=3.2.1555.0,
  IsLatestVersion=true, PlatformType=Linux
- simulate-principal-policy on the instance role: Denied for
  s3:PutObject on arn:aws:s3:::ssm-output-prod/*

Emit the standard DIAGNOSIS block.
