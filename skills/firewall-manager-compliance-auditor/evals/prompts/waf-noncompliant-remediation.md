# Eval prompt: waf-noncompliant-remediation

Audit the following AWS Firewall Manager policy for compliance posture. Emit
the standard VERDICT block (POLICY, POLICY_NAME, POLICY_TYPE, VERDICT, REASON,
FINDINGS, REMEDIATION).

Policy id: waf-noncompliant-remediation
Policy metadata:
  PolicyName: prod-edge-waf
  PolicyType: WAFV2
  PolicyState: READY
  RemediationEnabled: true
  DeleteUnusedFMSPolicies: false
  ResourceTypeLists:
    - AwsWafv2WebAcl
    - AwsApiGatewayStage
    - AwsElasticLoadBalancingV2LoadBalancer
    - CloudFrontDistribution
  ResourceTags: []
  IncludeMap:
    ORG_UNIT:
      - ou-abcd-12345678
  ExcludeMap: {}

Protection status:
  ProtectedResourceCount: 86
  NonCompliantResourceCount: 14
  PerAccountViolators:
    "111111111111": 4
    "222222222222": 8
    "333333333333": 2

FMS admin scope: Org root (delegated administrator configured).
