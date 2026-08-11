# Guardrails and Landing Zone Baseline — AWS Control Tower Account Factory Deployer

Deep reference on Control Tower Guardrails (preventive SCPs, detective
Config rules, proactive controls), landing zone baseline propagation
(StackSets), OU registration, and compliance verification. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Guardrail types

### Preventive Guardrails (SCPs)

Preventive Guardrails are implemented as Service Control Policies
(SCPs) in AWS Organizations. They block disallowed actions before they
execute.

**Common preventive Guardrails:**

| Guardrail | What it prevents | SCP effect |
|---|---|---|
| Disallow Leaving Organization | `organizations:LeaveOrganization` | Explicit Deny |
| Disallow Policy Changes | Modifying Control Tower-managed SCPs | Explicit Deny |
| Enable CloudTrail | Disabling CloudTrail in enrolled accounts | Explicit Deny |
| Disallow Root Access Keys | Creating root account access keys | Explicit Deny |
| Restrict Regions | Creating resources in unapproved regions | Explicit Deny for non-approved regions |

**SCP attachment hierarchy:**

```text
Root
  ├── SCP: Org-wide controls (applied to root)
  │     DenyLeavingOrg, RequireMFA
  └── OU: "Production" (registered with Control Tower)
        ├── SCP: OU-specific controls (applied to OU)
        │     RestrictRegions (us-east-1, us-west-2, eu-west-1)
        │     RequireEncryption
        └── Account: prod-app-001
              → Effective SCPs = Root SCPs ∩ OU SCPs
              → All deny statements from every level apply
```

**Key rule:** SCPs are additive. An account inherits ALL SCPs from
every level above it (root, parent OUs). The effective permission set
is the intersection of all applicable SCPs. An explicit Deny at any
level overrides any Allow.

### Detective Guardrails (Config + Security Hub)

Detective Guardrails use AWS Config rules and Security Hub controls to
detect non-compliance after it occurs. They do not block actions but
alert on violations.

**Common detective Guardrails:**

| Guardrail | What it detects | Implementation |
|---|---|---|
| Detect Public S3 Buckets | S3 bucket with public read/write | Config rule + Security Hub |
| Detect Unencrypted EBS | EBS volume without encryption | Config rule + Security Hub |
| Detect IAM Keys Older Than 90 Days | Access keys not rotated | Config rule |
| Detect Root MFA Not Enabled | Root account without MFA | Config rule + Security Hub |
| Detect Security Group Open to World | SG with 0.0.0.0/0 ingress on sensitive ports | Config rule |

**Detection flow:**

```text
1. Resource created/modified in enrolled account
2. Config evaluates rules against the resource
3. If non-compliant → Config rule status: NonCompliant
4. Security Hub aggregates the finding
5. Security Hub severity: LOW|MEDIUM|HIGH|CRITICAL
6. Alert/notification via EventBridge → SNS/Slack/email
```

### Proactive Guardrails

Proactive Guardrails use Config rules to detect resources that WOULD
violate policy, before they are fully operational.

**Example:** a proactive Config rule for CloudFormation checks if a
stack being created includes an unencrypted S3 bucket. The finding is
generated during stack creation, allowing remediation before the
resource is fully provisioned.

## Landing zone baseline StackSets

### Default baseline StackSets

Control Tower deploys these StackSets to every enrolled account:

| StackSet Name | Purpose | Resources Created |
|---|---|---|
| AWSControlTowerLogging | Centralized CloudTrail | CloudTrail trail, S3 bucket in logging account |
| AWSControlTowerSecurity | Security monitoring | Config recorder, Security Hub, GuardDuty (if enabled) |
| AWSControlTowerBP-BASELINE-CLOUDTRAIL | CloudTrail baseline config | Trail settings, event selectors |
| AWSControlTowerBP-BASELINE-CONFIG | Config recorder baseline | Config recorder, delivery channel |
| AWSControlTowerBP-BASELINE-CLOUDWATCH | CloudWatch alarms | Alarms for root login, IAM changes, etc. |
| AWSControlTowerBP-BASELINE-IAM | IAM baseline | Password policy, role baseline |

### StackSet deployment mechanics

```text
1. Account vended via Account Factory
2. Placed in a registered OU
3. Control Tower creates AWSControlTowerExecutionRole in the account
4. Management account's StackSet admin role deploys StackSets
5. StackSets create resources in the new account via execution role
6. CloudTrail → sends logs to logging account's S3 bucket
7. Config → sends compliance data to config aggregator
8. Security Hub → sends findings to security account (if delegated)
```

### Verifying StackSet deployment

```bash
# Check all StackSet instances for the new account
for stackset in AWSControlTowerLogging AWSControlTowerSecurity AWSControlTowerBP-BASELINE-CLOUDTRAIL AWSControlTowerBP-BASELINE-CONFIG; do
  echo "=== $stackset ==="
  aws cloudformation list-stack-instances \
    --stack-set-name "$stackset" \
    --query "Summaries[?Account=='123456789012'].{Account:Account,Region:Region,Status:StackInstanceStatus}" \
    --output table
done
```

**Expected:** all StackInstances with status `CURRENT`.

**If a StackInstance is `OUTDATED` or `INOPERABLE`:** the StackSet
deployment failed. Check the StackSet operation history for error
details:

```bash
aws cloudformation list-stack-set-operations \
  --stack-set-name "AWSControlTowerLogging" \
  --query "Summaries[?Status!='SUCCEEDED']" \
  --output table
```

## OU registration verification

### How to check if an OU is registered

```bash
# Method 1: Check enabled controls for the OU
aws controltower list-enabled-controls \
  --control-source-ou "ou-bbb-ccc" \
  --region us-east-1 \
  --query 'EnabledControls[*].ControlIdentifier' \
  --output table

# If the OU is registered, this returns control identifiers like:
# arn:aws:controltower:us-east-1::control/AWS-GR_AUDIT_BUCKET_POLICY
# arn:aws:controltower:us-east-1::control/AWS-GR_RESTRICT_ROOT_USER

# Method 2: Check if the OU has the Control Tower service-linked role
aws iam list-entities-for-policy \
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSControlTowerServiceRolePolicy" \
  --entity-filter "ROLE"
```

### Consequences of unregistered OU

| Feature | Registered OU | Unregistered OU |
|---|---|---|
| SCPs (Guardrails) | Inherited automatically | NOT inherited |
| Config rules (Detective) | Auto-deployed via StackSets | NOT deployed |
| CloudTrail (Baseline) | Auto-deployed | NOT deployed |
| Security Hub | Auto-enabled | NOT enabled |
| SSO auto-provision | Automatic | Manual setup required |
| Landing zone updates | Auto-propagated | Not propagated |

**An account in an unregistered OU is a compliance gap.** It has none
of the Guardrails, baselines, or monitoring that Control Tower provides.

## Custom baseline StackSets

### Creating a custom StackSet for account customization

```bash
# Create a custom StackSet with service-managed permissions
aws cloudformation create-stack-set \
  --stack-set-name "CustomBaseline-VPC" \
  --template-body file://custom-vpc.yaml \
  --permission-model SERVICE_MANAGED \
  --capabilities CAPABILITY_NAMED_IAM \
  --auto-deployment 'Enabled=true,RetainStacksOnAccountRemoval=false' \
  --call-as SELF
```

### Custom StackSet template example

```yaml
# custom-vpc.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Custom VPC baseline for Account Factory accounts

Resources:
  CustomVPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: Custom-Baseline-VPC

  PublicSubnet:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref CustomVPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: Custom-Baseline-Public

  PrivateSubnet:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref CustomVPC
      CidrBlock: 10.0.2.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      Tags:
        - Key: Name
          Value: Custom-Baseline-Private
```

### Auto-deployment behavior

When `auto-deployment` is enabled, the StackSet automatically deploys
to any new account that is placed in a targeted OU. No manual
intervention is needed — the StackSet deploys within minutes of account
creation.

**Key constraint:** auto-deployed StackSets use the
`AWSControlTowerExecutionRole` in the target account. This role must
exist before the StackSet can deploy. Control Tower creates this role
during account enrollment, so auto-deployment works for enrolled
accounts but NOT for accounts in unregistered OUs.

## Compliance verification checklist

After provisioning an account, verify:

```bash
# 1. SCP inheritance
aws organizations list-policies-for-target \
  --target-id "123456789012" \
  --filter SERVICE_CONTROL_POLICY \
  --output table

# 2. Config rules in the account
aws configservice describe-config-rules \
  --query 'ConfigRules[*].ConfigRuleName' \
  --output table \
  --profile target-account

# 3. Security Hub enabled
aws securityhub describe-hub --profile target-account

# 4. CloudTrail trail active
aws cloudtrail describe-trails \
  --query 'trailList[*].{Name:Name,IsLogging:IsLogging}' \
  --output table \
  --profile target-account

# 5. StackSet deployment status (in management account)
aws cloudformation list-stack-instances \
  --stack-set-name "AWSControlTowerLogging" \
  --query "Summaries[?Account=='123456789012'].Status"
```
