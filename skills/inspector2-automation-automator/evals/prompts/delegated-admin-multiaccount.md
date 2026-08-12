# Eval prompt: delegated-admin-multiaccount

Design an Inspector v2 automation workflow for the following
multi-account finding. Emit the standard FINDING block (SEVERITY,
DETECTION, RESPONSE, SSM_RUNBOOK, VERIFICATION, MULTI_ACCOUNT,
VERDICT, TEMPLATE).

Design reference: delegated-admin-multiaccount
Account: 111111111111 (management account of org o-abc123def)
Region: us-east-1

Finding: CVE-2026-2211 on amazon-linux base (CVSS 8.2)
Severity: HIGH
Resource: AWS_ECR_CONTAINER_IMAGE across 15 member accounts
Member accounts: 222222222222 ... 363636363636
Delegated admin: NOT configured for inspector2.amazonaws.com
  (aws organizations list-delegated-administrators returns empty)
Inspector enabled in member accounts individually, but no
  aggregated view exists.
