# Eval prompt: shield-tag-scope-incomplete

Audit the following AWS Firewall Manager policy for compliance posture. Emit
the standard VERDICT block (POLICY, POLICY_NAME, POLICY_TYPE, VERDICT, REASON,
FINDINGS, REMEDIATION).

Policy id: shield-tag-scope-incomplete
Policy metadata:
  PolicyName: prod-shield-advanced
  PolicyType: SHIELD_ADVANCED
  PolicyState: READY
  RemediationEnabled: true
  DeleteUnusedFMSPolicies: false
  ResourceTypeLists: []
  ResourceTags:
    - Key: env
      Value: prod
  IncludeMap:
    ACCOUNT:
      - "111111111111"
      - "222222222222"
  ExcludeMap: {}

Protection status:
  ProtectedResourceCount: 4
  NonCompliantResourceCount: 0

Context: A separate AWS Config inventory shows the two in-scope accounts
collectively own 12 in-scope Shield-Advanced-eligible resources (Elastic IPs,
ALBs, CloudFront distributions); only 4 carry the env=prod tag and are
therefore reachable by this policy.

FMS admin scope: Org root (delegated administrator configured).
