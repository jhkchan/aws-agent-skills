# Eval prompt: waf-legacy-policy-type

Audit the following AWS Firewall Manager policy for compliance posture. Emit
the standard VERDICT block (POLICY, POLICY_NAME, POLICY_TYPE, VERDICT, REASON,
FINDINGS, REMEDIATION).

Policy id: waf-legacy-policy-type
Policy metadata:
  PolicyName: classic-edge-waf
  PolicyType: WAF
  PolicyState: READY
  RemediationEnabled: true
  DeleteUnusedFMSPolicies: false
  ResourceTypeLists:
    - AwsWafRuleGroup
    - AwsWafWebAcl
  ResourceTags: []
  IncludeMap:
    ACCOUNT:
      - "111111111111"
  ExcludeMap: {}

Protection status:
  ProtectedResourceCount: 18
  NonCompliantResourceCount: 0

FMS admin scope: Org root (delegated administrator configured).
