# Eval: oracle-vcpu-tracking

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Oracle vCPU counting, Tenancy=Shared, HonorVcpuOptimization=true, hard limit, cross-Org sharing, delegated administrator, EventBridge alerting

## Prompt

Create a License Manager configuration for Oracle Database Standard
Edition. 200 vCPU entitlement. Shared tenancy, honor vCPU
optimization. Hard limit enforcement. Associate with EC2 launch
template lt-aaa111222333 in us-east-1. Share across the Organization
(all-features, OU ou-app-abcdef). Delegated administrator account
999999999999. Alert violations via SNS topic
arn:aws:sns:us-east-1:123456789012:license-alerts. Tags:
Vendor=Oracle, Environment=production.
