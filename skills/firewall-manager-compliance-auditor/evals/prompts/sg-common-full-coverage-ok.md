# Eval prompt: sg-common-full-coverage-ok

Audit the following AWS Firewall Manager policy for compliance posture. Emit
the standard VERDICT block (POLICY, POLICY_NAME, POLICY_TYPE, VERDICT, REASON,
FINDINGS, REMEDIATION).

Policy id: sg-common-full-coverage-ok
Policy metadata:
  PolicyName: ec2-baseline-sg
  PolicyType: SECURITY_GROUPS_COMMON
  PolicyState: READY
  RemediationEnabled: true
  DeleteUnusedFMSPolicies: true
  ResourceTypeLists:
    - AwsEc2Instance
    - AwsEc2NetworkInterface
    - AwsElasticLoadBalancingV2LoadBalancer
    - AwsElasticLoadBalancingLoadBalancer
  ResourceTags: []
  IncludeMap:
    ORG_UNIT:
      - ou-root-orgwide
  ExcludeMap: {}
  ManagedApplicationRules:
    - baseline-sg-prod

Protection status:
  ProtectedResourceCount: 612
  NonCompliantResourceCount: 0

FMS admin scope: Org root (delegated administrator configured).
Notification channel: SNS topic configured (fms-alerts).
