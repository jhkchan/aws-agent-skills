---
name: license-manager-deployer
description: >-
  Provisions AWS License Manager configurations with production defaults:
  license configurations (license type, count, rules), resource
  associations (EC2 instances, Systems Manager managed instances, on-
  premises resources), license rules enforcement (vCPU-based, instance-
  based, cores-based counting), cross-account sharing via AWS
  Organizations, automated discovery via Systems Manager inventory,
  license violation detection and alerting, self-service portal grants,
  Oracle license tracking, SQL Server licensing, subscription management,
  CloudWatch integration for violations. Emits a READY_TO_DEPLOY
  checklist with verification commands. Use when creating a License
  Manager configuration, tracking Oracle or SQL Server licenses, setting
  up vCPU-based license enforcement, distributing licenses across
  Organization accounts, detecting license violations, or configuring
  self-service license grants. Triggers: create license configuration,
  license manager vcpu counting, oracle license tracking, sql server
  licensing, cross-account license sharing, license manager organizations,
  license violation alerting, license manager grants, ssm license
  discovery.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with license-manager
  access (and organizations:EnableAWSServiceAccess for cross-account
  sharing, ssm managed-instance activation for on-premises discovery).
  Works with Terraform aws_licensemanager_license_configuration resource
  and CloudFormation AWS::LicenseManager::LicenseConfiguration templates.
keywords:
  - aws
  - license manager
  - license configuration
  - cloudops
  - deploy
  - provisioning
  - vcpu counting
  - oracle licensing
  - sql server licensing
  - cross-account
  - organizations
  - ssm discovery
  - license violation
  - grants
  - self-service portal
tags:
  - aws
  - license-manager
  - cloudops
  - deploy
  - governance
  - licensing
  - provisioning
  - oracle
  - sql-server
  - organizations
  - ssm
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Governance
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - license-manager
    - cloudops
    - deploy
    - governance
    - licensing
    - oracle
    - sql-server
    - organizations
    - ssm
  dependencies:
    - aws-orchestrator
  keywords:
    - create license configuration
    - license manager vcpu counting
    - oracle license tracking
    - sql server licensing
    - cross-account license sharing
    - license manager organizations
    - license violation alerting
    - license manager grants
    - ssm license discovery
  when_to_use: >-
    Invoke when the user wants to create an AWS License Manager license
    configuration, track Oracle or SQL Server licenses, enforce vCPU/
    instance/cores-based license counting, distribute license
    configurations across AWS Organizations member accounts, enable SSM-
    based automated discovery of licensed resources, set up license
    violation detection and alerting, or configure self-service license
    grants. Do NOT invoke for AWS Marketplace subscription purchase (use
    Marketplace skills), IAM policy management, or AWS Cost Explorer
    analysis.
---

# License Manager Deployer

An AWS CloudOps agent skill that provisions AWS License Manager
configurations with correct defaults. The skill walks the operator
through license type selection (vCPU-based, instance-based, cores-
based), license count and rules, resource associations (EC2, Systems
Manager managed instances, on-premises), cross-account sharing via
AWS Organizations, automated discovery via Systems Manager inventory,
license violation detection, self-service portal grants, and vendor-
specific tracking (Oracle, SQL Server). It captures licensing decisions,
explains why each default matters, and emits a READY_TO_DEPLOY checklist
with copy-pasteable verification commands.

## Activation keywords

create license configuration, license manager vCPU counting, Oracle
license tracking, SQL Server licensing, cross-account license sharing,
license manager Organizations, license violation alerting, license
manager grants, SSM license discovery.

## STRICT output contract

When this skill is invoked with a License-Manager-provisioning request
(create a license configuration, track Oracle or SQL Server licenses,
set up vCPU-based enforcement, distribute licenses across Organization
accounts, configure violation alerting, or a partial configuration), the
agent MUST respond with the READY_TO_DEPLOY checklist defined in the
"Output format" section using the literal all-caps labels
`LICENSE_MANAGER:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — License configuration model | Core licensing model |
| Step 2 — License type selection (vCPU, instance, cores) | Counting method |
| Step 3 — License rules (vendor-specific syntax) | Oracle, SQL Server rules |
| Step 4 — Resource associations (EC2, SSM, on-prem) | Resource scope |
| Step 5 — Cross-account sharing via Organizations | Multi-account distribution |
| Step 6 — Automated discovery via Systems Manager | Inventory-based discovery |
| Step 7 — License violations detection and alerting | Compliance enforcement |
| Step 8 — Self-service portal grants | Delegated license grants |
| Step 9 — Oracle license tracking specifics | Oracle rules + vCPU |
| Step 10 — SQL Server licensing specifics | Core-factor + cores counting |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/license-rules-and-counting.md | Counting + rules detail |
| references/cross-account-and-discovery.md | Org sharing + SSM detail |

## Mindset

**One-line takeaway:** A License Manager license configuration defines
the counting rule (vCPU, instance, or cores), the license count
entitlement, the enforcement rule (hard limit vs soft limit), and the
vendor-specific license rule string. License Manager discovers resources
via Systems Manager and enforces limits by preventing non-compliant EC2
instance launches. Cross-account sharing requires AWS Organizations
integration (delegated administrator + service access). Violations are
detected against the hard limit; alerting goes to SNS/CloudWatch.

Three misconceptions dominate License Manager misconfiguration at
provisioning time:

- **"License count and vCPU count are the same."** They are NOT. A
  license configuration has a `LicenseCount` (number of licenses
  owned). The `LicenseCountingType` determines how consumption is
  measured: `vCPU` counts total vCPUs across associated instances,
  `Instance` counts each running instance, `Core` counts physical CPU
  cores. A license count of 100 with `vCPU` counting means 100 vCPUs
  total — NOT 100 instances. Mixing these up causes silent over-
  licensing or under-licensing.

- **"Associating a license configuration with a resource automatically
  tracks it."** Only partially. The license configuration must be
  associated with a resource (EC2 instance, AMI, launch template, or
  SSM-managed instance), AND Systems Manager inventory must be enabled
  for discovery of non-EC2 resources. For EC2, License Manager tracks
  via the instance launch association. For on-premises or SSM-managed
  instances, SSM inventory with the `Aws:SoftwareInventory` plugin is
  REQUIRED for License Manager to discover and count them.

- **"Cross-account license sharing works out of the box."** It does
  NOT. Cross-account sharing requires: (1) AWS Organizations with all-
  features enabled, (2) License Manager enabled as a trusted service
  in Organizations, (3) a delegated administrator account, and (4) the
  license configuration explicitly shared with member accounts via
  `create-license-configuration-cross-account`. Without Organizations
  integration, license configurations are account-local.

## Configuration dependency graph (novel heuristic)

License Manager configurations are NOT independent. The counting type
determines the license rule syntax. Resource association depends on
SSM enablement for non-EC2 resources. Cross-account sharing depends on
Organizations. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| License configuration | license type known; count > 0; license rule syntax valid for the vendor | license rule syntax errors are only caught at enforcement time (not at creation) | the license tracking entity |
| License rules | counting type selected; vendor rule format known | Oracle rules require `Tenancy` and `HonorVcpuOptimization`; wrong syntax = silent non-enforcement | enforcement at launch |
| Resource association (EC2) | EC2 instance exists (or AMI/launch template) | association to a stopped instance still counts; association is a tracking link, not a billing link | consumption tracking |
| Resource association (SSM/on-prem) | SSM managed instance active; SSM inventory configured | without SSM inventory, on-prem instances are invisible to License Manager | on-prem license tracking |
| Cross-account sharing | Organizations all-features; License Manager trusted service; delegated admin configured | sharing to an account NOT in the Org silently fails; sharing requires explicit accept in target account | multi-account license distribution |
| Violation detection | license configuration has a hard limit; resources associated | soft limit (enforce=false) NEVER triggers violations; alerting requires SNS/CloudWatch Events setup | compliance alerting |
| Self-service grants | grant created with allowed operations; principal has IAM permission | grants without an expiry create permanent access security risk | delegated license management |

**The license-rules-row is the one a baseline model misses.** Creating
a license configuration without the correct `LicenseRules` (the vendor-
specific rule string) means License Manager accepts the configuration
but does NOT enforce vendor-specific conditions (e.g., Oracle tenancy,
SQL Server core factor). The procedure below forces an explicit
decision on license rules per vendor.

**Cross-dependency gotchas:**
- License counting type and license rules MUST be consistent. An Oracle
  database license with `Instance` counting but Oracle rules referencing
  vCPU tenancy will not enforce correctly. Oracle is vCPU-counted.
- Cross-account sharing requires the target account to accept the share.
  The share is a request, not an automatic push.
- SSM discovery for on-premises resources requires the `Aws:SoftwareInventory`
  SSM document association with `Applications` collection enabled.
- Hard limit (enforce=true) prevents new EC2 instance launches that
  exceed the count. Soft limit (enforce=false) only alerts. This is a
  critical decision that depends on compliance posture.

## Expert heuristic: vCPU vs instance-based vs cores-based counting

A baseline model says "set the license count." The correct heuristic
recognizes that the counting type fundamentally changes what is being
measured and which vendor rules apply.

```text
LicenseCountingType:
  ├── vCPU      → counts total vCPUs across all associated running instances
  │                Used for: Oracle, many per-vCPU commercial products
  │                License count = total vCPUs entitled
  │                Example: 100 vCPUs = 50 instances of 2 vCPU each
  │
  ├── Instance  → counts each running associated instance as 1 license
  │                Used for: per-instance software (some middleware, ISV tools)
  │                License count = total instances entitled
  │                Example: 100 instances = 100 EC2 instances regardless of size
  │
  └── Core      → counts physical CPU cores (NOT vCPUs; NOT hyperthreading)
                   Used for: SQL Server, Windows Server (core-based licensing)
                   License count = total cores entitled
                   Example: 100 cores = 6 instances of 16 cores each
```

**Key implication:** Oracle Database licenses are vCPU-counted (with
specific tenancy and honor-vcpu-optimization rules). SQL Server licenses
are core-counted (with a core factor of 0.5 for Standard, applies the
core-factor table). Generic per-instance licenses use Instance counting.
Choosing the wrong type makes the entire configuration non-compliant.

## Expert heuristic: cross-Org license distribution via Organizations

A baseline model says "share the license configuration." The correct
heuristic recognizes that cross-account sharing via Organizations is a
multi-step enablement, not a single API call.

```text
Cross-account license sharing flow:
  1. Organization exists with ALL features enabled
     aws organizations describe-organization --query 'Organization.FeatureSet'
     → Must be "ALL" (not "CONSOLIDATED_BILLING")
  2. License Manager is a trusted service in Organizations
     aws organizations enable-aws-service-access \
       --service-principal license-manager.amazonaws.com
  3. (Recommended) Delegated administrator for License Manager
     aws organizations register-delegated-administrator \
       --account-id <delegated-acct> \
       --service-principal license-manager.amazonaws.com
  4. License configuration is shared cross-account
     aws license-manager create-license-configuration-cross-account \
       --license-configuration-arn arn:aws:license-manager:... \
       --target-organization-structure '{"OrganizationalUnits":["ou-xxx"]}'
     OR share to specific accounts
  5. Target accounts accept the share (automatic for Org-shared configs)
  6. Target accounts associate the shared configuration with their resources
```

**Key implication:** Without step 1-3, step 4 fails. The Organizations
enablement is a prerequisite, not an option. The delegated administrator
centralizes license management in a designated account (e.g., a
governance/CTO account).

## Expert heuristic: SSM managed instance discovery

A baseline model says "associate the license config with instances."
The correct heuristic recognizes that on-premises and non-EC2 resources
require SSM managed instances with inventory enabled for License Manager
to discover them.

```text
SSM discovery for License Manager:
  1. On-prem server is activated as an SSM managed instance
     aws ssm create-activation --iam-role SSMServiceRole ...
     → Server runs SSM agent, registers as mi-xxxx
  2. SSM Inventory association collects software + OS data
     aws ssm create-association \
       --name AWS-InventoryManagement ...
       → Targets: mi-xxxx
       → Collect: Applications, "AWS:InstanceInformation"
  3. License Manager reads SSM inventory to discover software
     → Configuration → Discovery Settings → link to SSM inventory
  4. License configuration associated with discovered resources
     → Resource discovered by SSM shows in License Manager console
  5. Consumption tracked against license count
```

**Key implication:** for EC2 instances, the license configuration can
be associated at launch (via launch template or run-instances
--license-specifications) and License Manager tracks automatically. For
on-premises or SSM-managed instances, SSM inventory is the discovery
mechanism — without it, those resources are invisible to License
Manager.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| License counting type identified | Determines measurement method | Confirm vCPU, Instance, or Core |
| License count known | Total entitlement to track | Confirm owned license count |
| License rule syntax (if vendor-specific) | Vendor rules enforced at launch | Validate rule format for Oracle/SQL Server |
| Enforcement decision (hard vs soft limit) | Hard limit blocks launches; soft only alerts | Confirm `LicenseRulesEnforce` choice |
| AWS Organizations all-features (if cross-account) | Required for Org-based sharing | `aws organizations describe-organization` |
| License Manager trusted in Organizations (if cross-account) | Service access for cross-account sharing | `aws organizations list-aws-service-access-for-organization` |
| Delegated administrator (if cross-account, recommended) | Centralized license management | `aws organizations list-delegated-administrators` |
| SSM inventory configured (if on-premises discovery) | Required for non-EC2 resource discovery | `aws ssm describe-instance-information` |
| SNS topic ARN (if violation alerting) | Alerting destination | `aws sns list-topics` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — License configuration model

A license configuration is the central entity in License Manager. It
defines the license type, count, rules, and enforcement behavior.

| Element | Description | API field |
|---|---|---|
| Name | Configuration identifier | `--name` |
| License type | Counting method (vCPU/Instance/Core) | `--license-counting-type` |
| License count | Total entitlement | `--license-count` |
| License rules | Vendor-specific rule string (JSON) | `--license-rules` |
| Enforcement | Hard limit (block) or soft (alert) | `--license-rules-enforce` (true/false) |

**Create a license configuration:**

```bash
LIC_CONFIG_ID=$(aws license-manager create-license-configuration \
  --name "oracle-db-vcpu-tracking" \
  --license-counting-type vCPU \
  --license-count 100 \
  --license-rules 'Tenancy=Shared,HonorVcpuOptimization=true' \
  --license-rules-enforce \
  --region us-east-1 \
  --query 'LicenseConfigurationArn' --output text)

echo "License configuration ARN: $LIC_CONFIG_ID"
```

**Verify the configuration:**

```bash
aws license-manager get-license-configuration \
  --license-configuration-arn "$LIC_CONFIG_ID" \
  --region us-east-1
```

## Step 2 — License type selection (vCPU, instance, cores)

| Counting type | What is counted | Typical vendors | License count unit |
|---|---|---|---|
| `vCPU` | Total virtual CPUs across running associated instances | Oracle Database, many ISV | Total vCPUs |
| `Instance` | Each running associated instance = 1 | Per-instance middleware/tools | Total instances |
| `Core` | Physical CPU cores (not vCPUs) | SQL Server, Windows Server | Total cores |

**Critical:** the counting type determines what `LicenseCount` means.
A count of 100 with vCPU counting = 100 vCPUs total. With Instance
counting, 100 = 100 instances. With Core counting, 100 = 100 cores.
Misunderstanding this is the #1 cause of silent over/under-licensing.

## Step 3 — License rules (vendor-specific syntax)

License rules are vendor-specific conditions expressed as a comma-
separated key=value string. Different vendors have different rule
schemas.

### Oracle Database license rules

```bash
# Oracle Database — vCPU counting, shared tenancy, honor vCPU optimization
LICENSE_RULES='Tenancy=Shared,HonorVcpuOptimization=true'

# Oracle Database — dedicated host (Bring Your Own License to a Dedicated Host)
LICENSE_RULES='Tenancy=Host,HonorVcpuOptimization=true'

# Oracle Database — dedicated instance
LICENSE_RULES='Tenancy=Instance,HonorVcpuOptimization=true'
```

| Rule key | Values | Effect |
|---|---|---|
| `Tenancy` | `Shared`, `Instance`, `Host` | Resource tenancy constraint |
| `HonorVcpuOptimization` | `true`, `false` | If true, treats 4 vCPUs as 1 license when thread scheduling is enabled |

### SQL Server license rules

```bash
# SQL Server — core-based with 0.5 core factor for Standard Edition
LICENSE_RULES='location=EC2,coreFactor=0.5'

# SQL Server — core-based with 1.0 core factor for Enterprise Edition
LICENSE_RULES='location=EC2,coreFactor=1.0'
```

| Rule key | Values | Effect |
|---|---|---|
| `location` | `EC2`, `Host` | Resource location constraint |
| `coreFactor` | Decimal (0.5, 1.0) | Multiplier applied to physical cores for counting |

**Common mistake:** creating a license configuration without
`--license-rules`. The configuration is created but no vendor-specific
enforcement occurs. This is the #2 cause of silent non-compliance (the
#1 being wrong counting type).

## Step 4 — Resource associations (EC2, SSM, on-prem)

A license configuration must be associated with resources for
consumption tracking.

### Association at EC2 instance launch (recommended)

```bash
# Associate via launch template (recommended)
aws ec2 create-launch-template \
  --launch-template-name oracle-workload-template \
  --launch-template-data '{
    "ImageId":"ami-xxx",
    "InstanceType":"m5.2xlarge",
    "LicenseSpecifications":[
      {"LicenseConfigurationArn":"'"$LIC_CONFIG_ID"'"}
    ]
  }'

# Associate at run-instances time
aws ec2 run-instances \
  --image-id ami-xxx \
  --instance-type m5.2xlarge \
  --license-specifications "LicenseConfigurationArn=$LIC_CONFIG_ID" \
  --region us-east-1
```

### Association with existing resources

```bash
# Associate with an existing AMI (inherits to all instances launched from it)
aws license-manager associate-license-to-ami \
  --license-configuration-arn "$LIC_CONFIG_ID" \
  --resource-id ami-xxx \
  --region us-east-1

# License Manager tracks EC2 instances via SSM inventory
# For non-EC2 (on-premises), see references/cross-account-and-discovery.md
```

### SSM managed instance discovery

For on-premises or SSM-managed instances, SSM inventory MUST be enabled:

```bash
# Verify SSM inventory is configured
aws ssm describe-instance-information \
  --filters "Key=ResourceType,Values=ManagedInstance" \
  --region us-east-1

# Check inventory association (must include Applications collection)
aws ssm describe-association \
  --association-id "$ASSOC_ID" --region us-east-1
```

## Step 5 — Cross-account sharing via Organizations

Cross-account sharing requires Organizations enablement. The sharing
flow is multi-step.

### Verify Organizations prerequisites

```bash
# Check Organization feature set (must be ALL)
aws organizations describe-organization \
  --query 'Organization.FeatureSet' --output text

# Check License Manager service access
aws organizations list-aws-service-access-for-organization \
  --query 'EnabledServicePrincipals[?ServicePrincipal==`license-manager.amazonaws.com`]'
```

### Enable License Manager in Organizations

```bash
# Enable License Manager as a trusted service
aws organizations enable-aws-service-access \
  --service-principal license-manager.amazonaws.com

# (Recommended) Register a delegated administrator
aws organizations register-delegated-administrator \
  --account-id 999999999999 \
  --service-principal license-manager.amazonaws.com
```

### Share the license configuration

```bash
# Share to specific accounts
aws license-manager create-license-configuration-cross-account \
  --license-configuration-arn "$LIC_CONFIG_ID" \
  --target-organization-structure '{"Accounts":["111122223333","111122224444"]}' \
  --region us-east-1

# Share to an Organizational Unit
aws license-manager create-license-configuration-cross-account \
  --license-configuration-arn "$LIC_CONFIG_ID" \
  --target-organization-structure '{"OrganizationalUnits":["ou-xxx-yyyyyyyy"]}' \
  --region us-east-1
```

**Critical:** cross-account sharing requires explicit acceptance by the
target account if the share is to specific accounts. For Organization-
wide sharing via OU, acceptance is automatic.

## Step 6 — Automated discovery via Systems Manager

License Manager uses Systems Manager (SSM) inventory to discover
resources and count license consumption automatically.

### Configure SSM discovery settings

```bash
# Configure License Manager discovery settings
aws license-manager update-service-settings \
  --organization-configuration '{"EnableIntegration":true}' \
  --region us-east-1

# Verify discovery is enabled
aws license-manager get-service-settings \
  --query 'OrganizationConfiguration.EnableIntegration' --region us-east-1
```

### Verify SSM inventory is collecting data

```bash
# List managed instances with inventory
aws ssm get-inventory \
  --query 'Entities[*].{Id:Id,Type:Data.\"AWS:InstanceInformation\".Content[0].ResourceType}' \
  --region us-east-1
```

**Critical:** without SSM inventory, License Manager cannot discover
on-premises or cross-account resources. EC2 instances are tracked via
the association at launch (not SSM inventory).

## Step 7 — License violations detection and alerting

License Manager detects violations against the hard limit
(`LicenseRulesEnforce=true`). When a new EC2 instance launch would
exceed the license count, the launch is BLOCKED and a violation event
is emitted. Alerting requires CloudWatch Events / EventBridge + SNS.

### CloudWatch Events rule for license violations

```bash
# Create EventBridge rule matching License Manager violations
aws events put-rule \
  --name license-manager-violations \
  --event-pattern '{
    "source": ["aws.license-manager"],
    "detail-type": ["License Manager License Configuration Violation"]
  }' \
  --region us-east-1

# Add SNS target
aws events put-targets \
  --rule license-manager-violations \
  --targets '{"Id":"1","Arn":"arn:aws:sns:us-east-1:123456789012:license-alerts"}' \
  --region us-east-1
```

### List recent violations

```bash
aws license-manager list-license-specifications-for-resources \
  --resource-arns arn:aws:ec2:us-east-1:123456789012:instance/i-xxx \
  --region us-east-1

# List usage records (consumption)
aws license-manager list-usage-records-for-license-configuration \
  --license-configuration-arn "$LIC_CONFIG_ID" \
  --region us-east-1
```

## Step 8 — Self-service portal grants

License Manager grants allow delegated users to consume licenses
without direct console access to the license configuration.

### Create a grant

```bash
# Grant a principal (IAM entity) permission to use licenses
aws license-manager create-grant \
  --grant-name "dev-team-oracle-grant" \
  --license-configuration-arn "$LIC_CONFIG_ID" \
  --principals '["arn:aws:iam::123456789012:role/DevTeamRole"]' \
  --allowed-operations '["CreateGrant","CheckoutLicense","ViewGrant","ListLicenses"]' \
  --region us-east-1
```

### Grant with expiry (security best practice)

```bash
# Time-limited grant (recommended for temporary access)
aws license-manager create-grant \
  --grant-name "contractor-grant-30d" \
  --license-configuration-arn "$LIC_CONFIG_ID" \
  --principals '["arn:aws:iam::123456789012:role/ContractorRole"]' \
  --allowed-operations '["CheckoutLicense","ViewGrant"]' \
  --expiration "2026-09-05T00:00:00Z" \
  --region us-east-1
```

**Security note:** grants without an expiry create permanent access.
Always set an expiry for non-permanent roles.

## Step 9 — Oracle license tracking specifics

Oracle Database licensing is the most common License Manager use case.
Key specifics:

- **Counting type:** `vCPU` (Oracle is licensed per vCPU, with a
  minimum of 2 vCPUs per instance).
- **HonorVcpuOptimization:** when true, License Manager treats 4 vCPUs
  as 1 license when thread scheduling is enabled on the EC2 instance
  (i.e., 2 vCPUs count as 1 for licensing purposes if hyperthreading
  is on). This matches Oracle's standard processor licensing model.
- **Tenancy:** `Shared` (default, runs on shared EC2 hardware),
  `Instance` (dedicated instance), `Host` (dedicated host — required
  for some Oracle BYOL scenarios).

```bash
# Oracle Database Standard Edition — vCPU, shared tenancy, honor opt
LIC_ARN=$(aws license-manager create-license-configuration \
  --name "oracle-db-se-vcpu" \
  --license-counting-type vCPU \
  --license-count 200 \
  --license-rules 'Tenancy=Shared,HonorVcpuOptimization=true' \
  --license-rules-enforce \
  --region us-east-1 \
  --query 'LicenseConfigurationArn' --output text)
```

## Step 10 — SQL Server licensing specifics

SQL Server uses core-based licensing with a core factor:

- **Counting type:** `Core` (physical cores, not vCPUs).
- **Core factor:** 0.5 for Standard Edition, 1.0 for Enterprise
  Edition. The core factor multiplies physical cores to compute
  license consumption (e.g., 8 physical cores × 0.5 = 4 licenses).
- **Minimum:** 4 cores per physical processor (SQL Server minimum).

```bash
# SQL Server Standard — core-based, 0.5 factor
LIC_ARN=$(aws license-manager create-license-configuration \
  --name "sqlserver-std-core" \
  --license-counting-type Core \
  --license-count 24 \
  --license-rules 'location=EC2,coreFactor=0.5' \
  --license-rules-enforce \
  --region us-east-1 \
  --query 'LicenseConfigurationArn' --output text)
```

## Step 11 — Recent features

**Recent AWS features (2023-2026):**

- **License Manager integration with AWS IAM Identity Center (2023-
  2024):** Self-service portal now supports IAM Identity Center (SSO)
  for end-user authentication, simplifying grant access for non-IAM
  users.

- **Enhanced violation reporting (2023-2024):** License Manager now
  emits richer violation details in EventBridge, including the
  specific resource ARN, license configuration ARN, and violation
  reason code, enabling more granular alerting and remediation.

- **Cross-Region license tracking (2023-2024):** License Manager now
  tracks resource consumption across regions within the same account,
  with aggregated usage reporting in the home region.

- **Terraform provider improvements (2023-2024):** The Terraform
  `aws_licensemanager_license_configuration` resource now supports
  `license_rule` as a structured map (not just a raw string),
  improving readability and validation.

- **License Manager Marketplace integration (2024-2025):** Enhanced
  integration with AWS Marketplace for subscription-based licenses,
  allowing License Manager to track Marketplace-purchased software
  alongside BYOL configurations.

- **CloudWatch metric enhancements (2024-2025):** License Manager now
  publishes consumption metrics to CloudWatch (license count consumed,
  license count remaining), enabling dashboards and threshold alarms
  beyond violation-only alerting.

## NEVER do these things

1. **NEVER confuse license count with vCPU count.** The
   `LicenseCountingType` determines what is measured. A count of 100
   with vCPU counting means 100 vCPUs total, NOT 100 instances. Always
   confirm the counting type before setting the count.

2. **NEVER create a license configuration without license rules for
   vendor-specific licenses.** Oracle and SQL Server require specific
   rule strings (`Tenancy`, `HonorVcpuOptimization` for Oracle;
   `coreFactor` for SQL Server). Without rules, the configuration
   exists but does NOT enforce vendor conditions.

3. **NEVER assume cross-account sharing works without Organizations.**
   Cross-account license sharing requires Organizations all-features,
   License Manager as a trusted service, and (recommended) a delegated
   administrator. Without these, the share API call fails.

4. **NEVER forget SSM inventory for on-premises discovery.** EC2
   instances are tracked via launch association, but on-premises and
   SSM-managed instances require SSM inventory with the `Applications`
   collection. Without it, those resources are invisible.

5. **NEVER use soft limit (enforce=false) when compliance requires
   blocking.** Soft limit only alerts on violations; it does NOT block
   non-compliant launches. For compliance-critical licenses (Oracle,
   SQL Server), use hard limit (enforce=true).

6. **NEVER create grants without an expiry for temporary roles.**
   Grants without expiry create permanent access. Always set
   `--expiration` for contractor, developer, or temporary roles.

7. **NEVER assume license rule syntax errors are caught at creation.**
   License Manager accepts the configuration but enforcement may
   silently fail if the rule syntax is wrong. Validate rules against
   the vendor documentation before deploying.

8. **NEVER skip the delegated administrator for multi-account
   Organizations.** Without a delegated administrator, license
   management must be done from the management account, which violates
   least-privilege best practices.

9. **NEVER forget to set up CloudWatch Events for violation alerting.**
   Hard-limit violations emit events, but without an EventBridge rule +
   SNS target, no one is notified. Violation detection without alerting
   is useless.

10. **NEVER mix counting types within the same vendor's licensing
    model.** Oracle is vCPU-counted. SQL Server is core-counted.
    Creating an Oracle configuration with Core counting or SQL Server
    with vCPU counting produces non-compliant tracking.

## Output format

```text
LICENSE_MANAGER: <license-configuration-name> (<license-config-id-or-arn>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] License configuration name: <name>
  [✓|✗] Counting type: vCPU | Instance | Core
  [✓|✗] License count: <count> (<unit>)
  [✓|✗] License rules: <rules-string-or-none>
  [✓|✗] Enforcement: Hard limit (enforce=true) | Soft limit (enforce=false)
  [✓|✗] Resource association: EC2 (launch template / run-instances) | SSM managed instances | AMI
  [✓|✗] Cross-account sharing: Disabled | Enabled (Organizations all-features, OU <ou-id>)
  [✓|✗] Delegated administrator: <account-id> | Not configured
  [✓|✗] SSM discovery: Enabled (inventory configured) | Disabled
  [✓|✗] Violation alerting: EventBridge rule + SNS <topic-arn> | Not configured
  [✓|✗] Grants: <count> grants (<details-or-none>)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws license-manager get-license-configuration --license-configuration-arn <arn> --region <region>
  aws license-manager list-usage-records-for-license-configuration --license-configuration-arn <arn> --region <region>
  aws license-manager list-license-specifications-for-resources --resource-arns <resource-arn> --region <region>
```

### Worked example — Oracle Database vCPU tracking with cross-Org sharing

```text
LICENSE_MANAGER: oracle-db-vcpu-tracking (lic-aaa111222333444aaa)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] License configuration name: oracle-db-vcpu-tracking
  [✓] Counting type: vCPU
  [✓] License count: 200 (vCPUs)
  [✓] License rules: Tenancy=Shared,HonorVcpuOptimization=true
  [✓] Enforcement: Hard limit (enforce=true)
  [✓] Resource association: EC2 (launch template lt-aaa111222333)
  [✓] Cross-account sharing: Enabled (Organizations all-features, OU ou-app-abcdef)
  [✓] Delegated administrator: 999999999999
  [✓] SSM discovery: Enabled (inventory configured for managed instances)
  [✓] Violation alerting: EventBridge rule license-manager-violations + SNS arn:aws:sns:us-east-1:123456789012:license-alerts
  [✓] Grants: 1 grant (dev-team-oracle-grant, principal DevTeamRole, no expiry)
  [✓] Tags: Vendor=Oracle, Environment=production, ManagedBy=license-manager
VERIFICATION_COMMANDS:
  aws license-manager get-license-configuration --license-configuration-arn arn:aws:license-manager:us-east-1:123456789012:license-configuration:lic-aaa111222333444aaa --region us-east-1
  aws license-manager list-usage-records-for-license-configuration --license-configuration-arn arn:aws:license-manager:us-east-1:123456789012:license-configuration:lic-aaa111222333444aaa --region us-east-1
  aws license-manager list-license-specifications-for-resources --resource-arns arn:aws:ec2:us-east-1:123456789012:launch-template/lt-aaa111222333 --region us-east-1
```

## Error handling

### License configuration creation fails with validation error
- Verify `--license-counting-type` is one of `vCPU`, `Instance`,
  `Core`. Verify `--license-count` is a positive integer. Verify
  `--license-rules` syntax matches the vendor rule format.

### Cross-account sharing fails
- Verify Organizations is all-features enabled. Verify License Manager
  is a trusted service. Verify the target account/OU exists in the
  Organization. Use `describe-organization` and `list-roots` to
  verify.

### SSM discovery not finding on-premises resources
- Verify the on-premises server is an active SSM managed instance
  (`describe-instance-information`). Verify the SSM inventory
  association includes the `Applications` collection. Verify License
  Manager discovery settings have `EnableIntegration=true`.

### Violations not being alerted
- Verify `LicenseRulesEnforce=true` (soft limit never blocks). Verify
  the EventBridge rule matches `aws.license-manager` source and the
  correct `detail-type`. Verify the SNS topic policy allows
  EventBridge to publish.

### License consumption not updating
- Verify the license configuration is associated with running
  resources (not stopped). For EC2, verify the association via launch
  template or `--license-specifications` at launch. For SSM, verify
  inventory is collecting.

## Domain

AWS CloudOps / AWS License Manager Configuration Provisioning &
Software License Compliance.

## AWS documentation

- **License Manager Guide** — https://docs.aws.amazon.com/license-manager/latest/userguide/what-is.html
- **Create license configuration** — https://docs.aws.amazon.com/license-manager/latest/userguide/create-license-configuration.html
- **License counting types** — https://docs.aws.amazon.com/license-manager/latest/userguide/counting-types.html
- **License rules** — https://docs.aws.amazon.com/license-manager/latest/userguide/license-rules.html
- **Cross-account sharing** — https://docs.aws.amazon.com/license-manager/latest/userguide/cross-account.html
- **SSM discovery** — https://docs.aws.amazon.com/license-manager/latest/userguide/discovery.html
- **Grants (self-service)** — https://docs.aws.amazon.com/license-manager/latest/userguide/grants.html
- **Oracle licensing** — https://docs.aws.amazon.com/license-manager/latest/userguide/oracle.html
- **SQL Server licensing** — https://docs.aws.amazon.com/license-manager/latest/userguide/sql-server.html
- **Violations** — https://docs.aws.amazon.com/license-manager/latest/userguide/violations.html
