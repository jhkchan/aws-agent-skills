# Eval prompt: no-policy-at-all

Workload ID: no-policy-at-all
Account context:
  Region: us-east-1
  EBS volumes tagged "Environment:production": 50 volumes
  aws dlm get-lifecycle-policies response: []

Audit the DLM EBS snapshot lifecycle coverage for workload
"no-policy-at-all". Emit the standard VERDICT block (POLICY, VERDICT,
REASON, FINDINGS, REMEDIATION).
