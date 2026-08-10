# Eval prompt: hybrid-activation-expired

Diagnose the following SSM managed-instance gap for a hybrid
on-prem instance. Emit the standard DIAGNOSIS block.

Diagnosis reference: hybrid-activation-expired
Account: 111111111111
Region: us-east-1
Instance-id: mi-0abc123def456789a (hybrid)
Symptom: NotManaged (instance not appearing in SSM)

Recent diagnostic output:
- describe-instance-information for mi-0abc123def456789a:
  returns empty (instance not in SSM)
- describe-activations: shows activation
  aabbccdd-1111-2222-3333-aabbccddeeff with IamRole
  AmazonSSMManagedInstanceCore-Role, Expired=true,
  ExpiryDate=2026-06-01
- No recent CloudTrail events for the mi-* instance.

Emit the standard DIAGNOSIS block. Determine the appropriate
VERDICT (ROOT_CAUSE_FOUND, NEED_MORE_INFO, or ESCALATE).
