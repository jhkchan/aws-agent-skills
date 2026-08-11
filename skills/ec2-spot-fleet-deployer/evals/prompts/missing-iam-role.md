# Eval: missing-iam-role

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — AWSServiceRoleForEC2SpotFleet does not exist; fleet request will fail

## Prompt

Create a maintain Spot Fleet in us-east-1 for web servers.
priceCapacityOptimized. Target capacity 10 vcpu. Instance
types: m5.large, m5a.large. The IAM role
AWSServiceRoleForEC2SpotFleet has NOT been created yet.
Launch template lt-web-001 (version 1). Account: 123456789012.
