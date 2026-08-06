# Eval prompt: remediation-disabled-config-gap

Audit the following AWS Firewall Manager policy for compliance posture. Emit
the standard VERDICT block (POLICY, POLICY_NAME, POLICY_TYPE, VERDICT, REASON,
FINDINGS, REMEDIATION).

Policy id: remediation-disabled-config-gap
Policy metadata:
  PolicyName: sg-content-audit-steady
  PolicyType: SECURITY_GROUPS_CONTENT_AUDIT
  PolicyState: READY
  RemediationEnabled: false
  DeleteUnusedFMSPolicies: false
  ResourceTypeLists:
    - AwsEc2Instance
    - AwsEc2NetworkInterface
  ResourceTags: []
  IncludeMap:
    ORG_UNIT:
      - ou-abcd-12345678
  ExcludeMap: {}

Protection status:
  ProtectedResourceCount: 248
  NonCompliantResourceCount: 0

Context: This policy was created 95 days ago and has remained in detect-only
mode since onboarding. No transition to enforcement has been scheduled.

FMS admin scope: Org root (delegated administrator configured).
