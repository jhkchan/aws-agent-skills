# Readiness Checks and Resource Sets — Route 53 ARC Deployer

Deep reference on resource set design (type mapping, cell scoping,
multi-resource patterns), readiness check evaluation (templates,
schedule, on-demand), and cross-cell readiness assessment. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Resource set fundamentals

### What a resource set is

A resource set groups resources of the SAME CloudFormation resource
type across cells. ARC uses the resource type to determine which
readiness template to apply. Each resource in the set is tagged with
its cell via `ReadinessScopes`.

```text
Resource Set: app-nlb-rs
  Type: AWS::ElasticLoadBalancingV2::LoadBalancer
  Resources:
    - arn:...:loadbalancer/net/app-nlb-a/...  Scope: Cell-A
    - arn:...:loadbalancer/net/app-nlb-b/...  Scope: Cell-B
```

ARC compares the readiness of Cell-A's NLB against Cell-B's NLB. If
Cell-B's NLB is missing, unhealthy, or misconfigured, the readiness
check reports Cell-B as NOT_READY.

### Supported resource types

| CloudFormation Type | Readiness Template |
|---|---|
| AWS::ElasticLoadBalancingV2::LoadBalancer | Listener count, target health, subnet mapping |
| AWS::AutoScaling::AutoScalingGroup | Desired capacity, min size, instance health |
| AWS::DynamoDB::Table | Table status (ACTIVE), provisioned throughput |
| AWS::RDS::DBCluster | Cluster status (available), writer instance |
| AWS::RDS::DBInstance | Instance status (available), storage |
| AWS::EC2::Instance | Instance state (running), health |
| AWS::EC2::NatGateway | State (available), ENI attachment |
| AWS::EC2::Volume | State (in-use), attachment |
| AWS::S3::Bucket | Bucket exists, versioning config |
| AWS::Lambda::Function | Function exists, runtime configured |
| AWS::SQS::Queue | Queue exists, visibility timeout |
| AWS::SNS::Topic | Topic exists, subscriptions |
| AWS::StepFunctions::StateMachine | State machine exists, status |

**Common mistake:** using a shortened or incorrect type string. The
type must be the full CloudFormation resource type (e.g.,
`AWS::ElasticLoadBalancingV2::LoadBalancer`, not `NLB` or
`LoadBalancer`).

### Creating resource sets

```bash
# NLB resource set
aws route53-recovery-readiness create-resource-set \
  --resource-set-name "app-nlb-rs" \
  --resource-set-type "AWS::ElasticLoadBalancingV2::LoadBalancer" \
  --resources \
    '[{"ResourceArn":"arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/app-nlb-a/50dc6c495c0c9188","ReadinessScopes":["Cell-A"]},{"ResourceArn":"arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/app-nlb-b/60dc6c495c0c9189","ReadinessScopes":["Cell-B"]}]'

# ASG resource set
aws route53-recovery-readiness create-resource-set \
  --resource-set-name "app-asg-rs" \
  --resource-set-type "AWS::AutoScaling::AutoScalingGroup" \
  --resources \
    '[{"ResourceArn":"arn:aws:autoscaling:us-east-1:123456789012:autoScalingGroup:...:asg-a","ReadinessScopes":["Cell-A"]},{"ResourceArn":"arn:aws:autoscaling:us-west-2:123456789012:autoScalingGroup:...:asg-b","ReadinessScopes":["Cell-B"]}]'

# DynamoDB resource set
aws route53-recovery-readiness create-resource-set \
  --resource-set-name "app-ddb-rs" \
  --resource-set-type "AWS::DynamoDB::Table" \
  --resources \
    '[{"ResourceArn":"arn:aws:dynamodb:us-east-1:123456789012:table/app-table","ReadinessScopes":["Cell-A"]},{"ResourceArn":"arn:aws:dynamodb:us-west-2:123456789012:table/app-table","ReadinessScopes":["Cell-B"]}]'
```

## Readiness check evaluation

### How readiness checks work

Each readiness check is bound to ONE resource set. ARC evaluates the
readiness of each resource in the set against the type-specific
template:

1. For each cell, ARC checks that the resource exists.
2. ARC checks resource-specific attributes (e.g., NLB target health,
   ASG desired capacity).
3. ARC compares results across cells.

```bash
# Create readiness check for NLB resource set
aws route53-recovery-readiness create-readiness-check \
  --readiness-check-name "app-nlb-check" \
  --resource-set-name "app-nlb-rs"

# Get readiness check status
aws route53-recovery-readiness get-readiness-check \
  --readiness-check-name "app-nlb-check"
```

### Readiness check schedule

Readiness checks run automatically every ~5 minutes. They can also
be triggered on demand:

```bash
# Trigger on-demand readiness check
aws route53-recovery-readiness get-cell-readiness \
  --cell-name "Cell-B"
```

**Before failover, always run on-demand readiness check.** The
scheduled check may be up to 5 minutes stale.

### Readiness states explained

| State | Meaning | Action |
|---|---|---|
| READY | All resources exist and pass checks | Safe to fail over |
| NOT_READY | At least one resource missing or unhealthy | Fix resource before failover |
| UNKNOWN | Not yet evaluated or insufficient data | Wait and re-check |
| NOT_AUTHORIZED | IAM permission missing for resource | Grant IAM permissions |

### Diagnosing NOT_READY

```bash
# Get detailed readiness breakdown for a cell
aws route53-recovery-readiness get-cell-readiness \
  --cell-name "Cell-B" \
  --output json | jq '.ReadinessChecks'

# Example output showing which resource failed:
# {
#   "Readiness": "NOT_READY",
#   "ReadinessChecks": [
#     {
#       "Resource": "arn:...:loadbalancer/net/app-nlb-b/...",
#       "Readiness": "NOT_READY",
#       "Messages": [{"Message": "No healthy targets in target group"}]
#     }
#   ]
# }
```

## Recovery groups (cross-cell readiness)

A recovery group aggregates multiple readiness checks into a single
readiness view:

```bash
# Create recovery group
aws route53-recovery-readiness create-recovery-group \
  --recovery-group-name "app-recovery-group" \
  --cells Cell-A Cell-B

# Get aggregate readiness
aws route53-recovery-readiness get-recovery-group-readiness-summary \
  --recovery-group-name "app-recovery-group"
```

The recovery group readiness is READY only when ALL cells are READY.
This is the pre-failover gate.

## Common readiness pitfalls

### Pitfall 1: Wrong resource type

```text
WRONG:  --resource-set-type "NLB"
WRONG:  --resource-set-type "LoadBalancer"
RIGHT:  --resource-set-type "AWS::ElasticLoadBalancingV2::LoadBalancer"
```

The type must be the full CloudFormation resource type. Shortened
names cause the readiness check to fail silently.

### Pitfall 2: Missing ReadinessScopes

Without `ReadinessScopes`, ARC does not know which cell a resource
belongs to. The cross-cell comparison fails.

```bash
# WRONG — no ReadinessScopes
--resources '[{"ResourceArn":"arn:...:loadbalancer/net/app-nlb-a/..."}]'

# RIGHT — with ReadinessScopes
--resources '[{"ResourceArn":"arn:...:loadbalancer/net/app-nlb-a/...","ReadinessScopes":["Cell-A"]}]'
```

### Pitfall 3: Cross-account IAM

If resources are in different AWS accounts, ARC needs cross-account
read permissions. The `route53-recovery-readiness` service-linked
role must exist in each account.

```bash
# Create the service-linked role in each account
aws iam create-service-linked-role \
  --aws-service-name route53-recovery-readiness.amazonaws.com
```

## Terraform examples

```hcl
# Resource set for NLB
resource "aws_route53recoveryreadiness_resource_set" "nlb" {
  resource_set_name = "app-nlb-rs"
  resource_set_type = "AWS::ElasticLoadBalancingV2::LoadBalancer"

  resources {
    resource_arn     = aws_lb.cell_a_nlb.arn
    readiness_scopes = ["Cell-A"]
  }

  resources {
    resource_arn     = aws_lb.cell_b_nlb.arn
    readiness_scopes = ["Cell-B"]
  }
}

# Readiness check
resource "aws_route53recoveryreadiness_readiness_check" "nlb" {
  readiness_check_name = "app-nlb-check"
  resource_set_name    = aws_route53recoveryreadiness_resource_set.nlb.resource_set_name
}

# Recovery group
resource "aws_route53recoveryreadiness_recovery_group" "app" {
  recovery_group_name = "app-recovery-group"
  cells               = ["Cell-A", "Cell-B"]
}
```

## Cell and resource set layout (from Step 2)

```text
Cell-A (us-east-1):
  NLB: arn:aws:elasticloadbalancing:us-east-1:...:loadbalancer/net/app-nlb-a/...
  ASG: arn:aws:autoscaling:us-east-1:...:autoScalingGroup:...
  DynamoDB: arn:aws:dynamodb:us-east-1:...:table/app-table

Cell-B (us-west-2):
  NLB: arn:aws:elasticloadbalancing:us-west-2:...:loadbalancer/net/app-nlb-b/...
  ASG: arn:aws:autoscaling:us-west-2:...:autoScalingGroup:...
  DynamoDB: arn:aws:dynamodb:us-west-2:...:table/app-table

Resource Set 1 (NLB):
  Type: AWS::ElasticLoadBalancingV2::LoadBalancer
  Resources: [Cell-A NLB, Cell-B NLB]

Resource Set 2 (ASG):
  Type: AWS::AutoScaling::AutoScalingGroup
  Resources: [Cell-A ASG, Cell-B ASG]

Resource Set 3 (DynamoDB):
  Type: AWS::DynamoDB::Table
  Resources: [Cell-A table, Cell-B table]
```
