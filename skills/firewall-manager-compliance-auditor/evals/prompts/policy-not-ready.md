# Eval prompt: policy-not-ready

Audit the following AWS Firewall Manager policy for compliance posture. Emit
the standard VERDICT block (POLICY, POLICY_NAME, POLICY_TYPE, VERDICT, REASON,
FINDINGS, REMEDIATION).

Policy id: policy-not-ready
Policy metadata:
  PolicyName: edge-waf-staging
  PolicyType: WAFV2
  PolicyState: NOT_READY
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
  ProtectedResourceCount: 0
  NonCompliantResourceCount: 0

FMS admin scope: Org root (delegated administrator configured).
