# Execution Role and Target Collection — SSM Automation Deployer

Deep reference on the SSM Automation execution role (assume role),
trust policy, permissions, target collection via resource groups and
tags, and rate control configuration. Loaded on demand by the skill.

## Automation execution role

The automation execution role (assume role) is assumed by the SSM
service (`ssm.amazonaws.com`) to execute API calls within the runbook
steps. This is NOT the same as the EC2 instance role (instance
profile).

### Trust policy

The role MUST have a trust policy allowing `ssm.amazonaws.com`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ssm.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### Permissions policy

The role's permissions MUST cover every API call made in every step.
A missing permission causes the step to fail with `AccessDenied`.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:StopInstances",
        "ec2:StartInstances",
        "ec2:RunInstances",
        "lambda:InvokeFunction",
        "iam:PassRole",
        "ssm:DescribeInstancePatches",
        "ssm:GetCommandInvocation"
      ],
      "Resource": "*"
    }
  ]
}
```

### The iam:PassRole requirement

If any step passes a role to a service (e.g., `aws:runInstances` with
an instance profile), the execution role MUST have `iam:PassRole`.
Missing this permission is the #1 cause of step failures.

```json
{
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": "arn:aws:iam::123456789012:role/EC2-SSM-Profile"
}
```

### Role creation

```bash
# Create role with SSM trust
aws iam create-role --role-name SSMAutomationRole \
  --assume-role-policy-document file://trust-policy.json

# Attach inline permissions policy
aws iam put-role-policy --role-name SSMAutomationRole \
  --policy-name SSMAutomationPermissions \
  --policy-document file://permissions-policy.json
```

### Passing the role at execution time

The role ARN is passed at execution time, NOT at document creation:

```bash
aws ssm start-automation-execution \
  --document-name "MyRunbook" \
  --automation-assume-role "arn:aws:iam::123456789012:role/SSMAutomationRole" \
  --parameters "InstanceId=i-aaa11122"
```

## Target collection

Targets enable the runbook to operate on a dynamic set of resources.
Targets are evaluated at execution time, not creation time.

### Explicit resource IDs

Fixed set of resource IDs:

```bash
aws ssm start-automation-execution \
  --document-name "RemediateEC2" \
  --parameters "InstanceId=i-aaa11122" \
  --automation-assume-role "arn:aws:iam::123456789012:role/SSMAutomationRole"
```

### Resource group targets

Dynamic collection via AWS Resource Groups:

```bash
aws ssm start-automation-execution \
  --document-name "RemediateEC2" \
  --targets '[{"Key":"ResourceGroup","Values":["rg-prod-ec2"]}]' \
  --target-parameter-name "InstanceId" \
  --automation-assume-role "arn:aws:iam::123456789012:role/SSMAutomationRole"
```

**`--target-parameter-name`** specifies which document parameter
receives each target resource ID. The runbook must have a parameter
with this name.

**Verify resource group before execution:**

```bash
# Check resource group exists and has members
aws resource-groups get-group --group-name rg-prod-ec2
aws resource-groups get-group-query-results --group-name rg-prod-ec2
```

### Tag-based targets

Dynamic collection via tag queries:

```bash
aws ssm start-automation-execution \
  --document-name "RemediateEC2" \
  --targets '[{"Key":"tag:Environment","Values":["production"]},{"Key":"tag:AutoRemediate","Values":["true"]}]' \
  --target-parameter-name "InstanceId" \
  --automation-assume-role "arn:aws:iam::123456789012:role/SSMAutomationRole"
```

Multiple targets are AND'd together — resources must match ALL target
criteria.

**Verify tags before execution:**

```bash
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Environment,Values=production Key=AutoRemediate,Values=true \
  --query 'ResourceTagMappingList[*].ResourceARN' --output table
```

### Combining targets with Resource Groups

```bash
aws ssm start-automation-execution \
  --document-name "RemediateEC2" \
  --targets '[{"Key":"ResourceGroup","Values":["rg-prod-ec2"]},{"Key":"tag:AutoRemediate","Values":["true"]}]' \
  --target-parameter-name "InstanceId" \
  --automation-assume-role "arn:aws:iam::123456789012:role/SSMAutomationRole"
```

## Rate control

Rate control governs how the automation executes across multiple
targets.

### MaxConcurrency

Maximum number of targets executing simultaneously.

```text
MaxConcurrency: "10"   → max 10 targets in parallel
MaxConcurrency: "50%"  → max 50% of total targets in parallel
MaxConcurrency: "1"    → sequential (one at a time)
```

**Default soft quota: 10.** For higher concurrency, request a quota
increase via Service Quotas.

### MaxErrors

Stops execution when the error count exceeds the threshold.

```text
MaxErrors: "3"   → stop after 3 errors
MaxErrors: "1%"  → stop when 1% of targets have errored
MaxErrors: "0"   → never stop (run on all targets regardless of errors)
```

**Recommended for production:** MaxErrors of 1-3 to limit blast
radius. A higher threshold risks cascading failures across the fleet.

### Combined rate control example

```bash
aws ssm start-automation-execution \
  --document-name "PatchProduction" \
  --targets '[{"Key":"tag:Environment","Values":["production"]}]' \
  --target-parameter-name "InstanceId" \
  --max-concurrency "10" \
  --max-errors "3" \
  --automation-assume-role "arn:aws:iam::123456789012:role/SSMAutomationRole"
```

This runs the patching runbook on all production instances, max 10
at a time, stopping if 3 errors occur.

## EventBridge role for scheduled automations

EventBridge needs its own role to start SSM Automation executions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ssm:StartAutomationExecution",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::123456789012:role/SSMAutomationRole"
    }
  ]
}
```

Trust policy for the EventBridge role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "events.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## Expert heuristic: target collection via resource groups (moved from SKILL.md)

```text
Target collection modes:

  1. Explicit resource IDs:
       Targets: [{Key: "InstanceIds", Values: ["i-aaa", "i-bbb"]}]
       → Fixed set.

  2. Resource group query:
       Targets: [{Key: "ResourceGroup", Values: ["rg-prod-ec2"]}]
       → Dynamic. Evaluated at execution time.

  3. Tag-based query:
       Targets: [{Key: "tag:Environment", Values: ["production"]}]
       → Dynamic. All resources matching the tag.

Rate control on dynamic targets:
  MaxConcurrency: "10" or "10%"  → max parallel executions
  MaxErrors: "3" or "1%"         → stop when exceeded
```

**Key implication:** dynamic targets enable fleet-wide operations
(patch all production instances, remediate all non-compliant
resources). Rate control prevents runaway execution.
