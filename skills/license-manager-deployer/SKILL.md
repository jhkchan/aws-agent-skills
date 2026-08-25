---
name: license-manager-deployer
description: 'Provisions AWS License Manager configurations with production defaults: license configurations (license type, count, rules), resource associations (EC2 instances, Systems Manager managed instances, on- premises resources), license rules enforcement (vCPU-based, instance- based, cores-based counting), cross-account sharing via AWS Organizations, automated discovery via Systems Manager inventory, license violation detection and alerting, self-service portal grants, Oracle license tracking, SQL Server licensing, subscription management, CloudWatch integration for violations. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a License Manager configuration, tracking Oracle or SQL Server licenses, setting up vCPU-based license. Triggers: create license configuration, license manager vcpu counting, oracle license tracking, sql server licensing, cross-account license sharing, license manager organizations, license violation alerting, license manager grants, ssm license discovery.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with license-manager access (and organizations:EnableAWSServiceAccess for cross-account sharing, ssm managed-instance activation for on-premises discovery). Works with Terraform aws_licensemanager_license_configuration resource and CloudFormation AWS::LicenseManager::LicenseConfiguration templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, license-manager, cloudops, deploy, governance, licensing, provisioning, oracle, sql-server, organizations, ssm
  dependencies: aws-orchestrator
  keywords: aws, license manager, license configuration, cloudops, deploy, provisioning, vcpu counting, oracle licensing, sql server licensing, cross-account, organizations, ssm discovery, license violation, grants, self-service portal
  when_to_use: Invoke when the user wants to create an AWS License Manager license configuration, track Oracle or SQL Server licenses, enforce vCPU/ instance/cores-based license counting, distribute license configurations across AWS Organizations member accounts, enable SSM- based automated discovery of licensed resources, set up license violation detection and alerting, or configure self-service license grants. Do NOT invoke for AWS Marketplace subscription purchase (use Marketplace skills), IAM policy management, or AWS Cost Explorer analysis.
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
  total — NOT 100 instances.

- **"Associating a license configuration with a resource automatically
  tracks it."** Only partially. The license configuration must be
  associated with a resource, AND Systems Manager inventory must be
  enabled for discovery of non-EC2 resources. For on-premises or SSM-
  managed instances, SSM inventory with the `Aws:SoftwareInventory`
  plugin is REQUIRED for License Manager to discover them.

- **"Cross-account license sharing works out of the box."** It does
  NOT. Cross-account sharing requires: (1) Organizations with all-
  features enabled, (2) License Manager enabled as a trusted service,
  (3) a delegated administrator account, and (4) explicit sharing to
  member accounts. Without Organizations integration, configurations
  are account-local.

## Configuration dependency graph (novel heuristic)

| Configuration | Hard dependencies | Silent failure | Enables |
|---|---|---|---|
| License configuration | license type known; count > 0; rule syntax valid | rule errors only caught at enforcement | the tracking entity |
| License rules | counting type selected; vendor rule format known | wrong syntax = silent non-enforcement | enforcement at launch |
| Resource association (EC2) | EC2 instance / AMI / launch template exists | association to stopped instance still counts | consumption tracking |
| Resource association (SSM) | SSM managed instance active; inventory configured | without inventory, on-prem invisible | on-prem tracking |
| Cross-account sharing | Organizations all-features; trusted service; delegated admin | sharing to non-Org account fails | multi-account distribution |
| Violation detection | hard limit; resources associated | soft limit never triggers violations | compliance alerting |
| Grants | allowed operations; principal has IAM permission | grants without expiry = permanent risk | delegated management |

**The license-rules row is the one a baseline model misses.** Creating
a configuration without the correct `LicenseRules` means License Manager
accepts it but does NOT enforce vendor-specific conditions. The
procedure below forces an explicit decision on rules per vendor.

## Expert heuristic: vCPU vs instance-based vs cores-based counting

A baseline model says "set the license count." The correct heuristic
recognizes that the counting type fundamentally changes what is measured.

```text
LicenseCountingType:
  ├── vCPU      → counts total vCPUs across running associated instances
  │                Used for: Oracle, many per-vCPU commercial products
  │                License count = total vCPUs entitled
  │                100 vCPUs = 50 instances of 2 vCPU each
  │
  ├── Instance  → counts each running associated instance as 1 license
  │                Used for: per-instance software (middleware, ISV tools)
  │                License count = total instances entitled
  │
  └── Core      → counts physical CPU cores (NOT vCPUs)
                   Used for: SQL Server, Windows Server
                   License count = total cores entitled
```

**Key implication:** Oracle Database is vCPU-counted. SQL Server is
core-counted. Generic per-instance licenses use Instance counting.
Choosing the wrong type makes the entire configuration non-compliant.

## Expert heuristic: cross-Org distribution via Organizations

```text
Cross-account license sharing flow:
  1. Organization exists with ALL features enabled
     aws organizations describe-organization --query 'Organization.FeatureSet'
     → Must be "ALL" (not "CONSOLIDATED_BILLING")
  2. License Manager is a trusted service
     aws organizations enable-aws-service-access \
       --service-principal license-manager.amazonaws.com
  3. (Recommended) Delegated administrator
     aws organizations register-delegated-administrator \
       --account-id <delegated-acct> \
       --service-principal license-manager.amazonaws.com
  4. License configuration shared cross-account
     aws license-manager create-license-configuration-cross-account \
       --license-configuration-arn arn:aws:license-manager:... \
       --target-organization-structure '{"OrganizationalUnits":["ou-xxx"]}'
  5. Target accounts receive the share (automatic for OU-shared)
  6. Target accounts associate the config with their resources
```

**Key implication:** Without steps 1-3, step 4 fails. The Organizations
enablement is a prerequisite, not an option.

## Expert heuristic: SSM managed instance discovery

For EC2, the license configuration is associated at launch. For on-
premises or SSM-managed instances, SSM inventory is the discovery
mechanism.

```text
SSM discovery flow:
  1. On-prem server activated as SSM managed instance (mi-xxxx)
  2. SSM Inventory association collects software data
     aws ssm create-association --name AWS-InventoryManagement ...
  3. License Manager reads SSM inventory to discover software
  4. Consumption tracked against license count
```

**Key implication:** without SSM inventory, on-premises resources are
invisible to License Manager.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| License counting type identified | Determines measurement method | Confirm vCPU, Instance, or Core |
| License count known | Total entitlement to track | Confirm owned license count |
| License rule syntax (if vendor-specific) | Vendor rules enforced at launch | Validate rule format for Oracle/SQL Server |
| Enforcement decision (hard vs soft) | Hard blocks launches; soft only alerts | Confirm `LicenseRulesEnforce` choice |
| Organizations all-features (if cross-account) | Required for Org-based sharing | `aws organizations describe-organization` |
| License Manager trusted (if cross-account) | Service access for sharing | `aws organizations list-aws-service-access-for-organization` |
| Delegated administrator (if cross-account) | Centralized license management | `aws organizations list-delegated-administrators` |
| SSM inventory configured (if on-prem) | Required for non-EC2 discovery | `aws ssm describe-instance-information` |
| SNS topic ARN (if alerting) | Alerting destination | `aws sns list-topics` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — License configuration model

A license configuration is the central entity in License Manager.

| Element | Description | API field |
|---|---|---|
| Name | Configuration identifier | `--name` |
| License type | Counting method (vCPU/Instance/Core) | `--license-counting-type` |
| License count | Total entitlement | `--license-count` |
| License rules | Vendor-specific rule string | `--license-rules` |
| Enforcement | Hard limit or soft (alert only) | `--license-rules-enforce` |

**Create a license configuration:**

```bash
LIC_CONFIG_ARN=$(aws license-manager create-license-configuration \
  --name "oracle-db-vcpu-tracking" \
  --license-counting-type vCPU \
  --license-count 100 \
  --license-rules 'Tenancy=Shared,HonorVcpuOptimization=true' \
  --license-rules-enforce \
  --region us-east-1 \
  --query 'LicenseConfigurationArn' --output text)
```

## Step 2 — License type selection (vCPU, instance, cores)

| Counting type | What is counted | Typical vendors | License count unit |
|---|---|---|---|
| `vCPU` | Total virtual CPUs across running associated instances | Oracle Database, many ISV | Total vCPUs |
| `Instance` | Each running associated instance = 1 | Per-instance middleware/tools | Total instances |
| `Core` | Physical CPU cores (not vCPUs) | SQL Server, Windows Server | Total cores |

**Critical:** the counting type determines what `LicenseCount` means. A
count of 100 with vCPU = 100 vCPUs. With Instance = 100 instances. With
Core = 100 cores. Misunderstanding this is the #1 cause of silent
over/under-licensing.

## Step 3 — License rules (vendor-specific syntax)

License rules are vendor-specific conditions expressed as a comma-
separated key=value string.

### Oracle Database license rules

```bash
# Oracle Database — vCPU counting, shared tenancy, honor vCPU opt
LICENSE_RULES='Tenancy=Shared,HonorVcpuOptimization=true'

# Oracle Database — dedicated host (BYOL)
LICENSE_RULES='Tenancy=Host,HonorVcpuOptimization=true'
```

| Rule key | Values | Effect |
|---|---|---|
| `Tenancy` | `Shared`, `Instance`, `Host` | Resource tenancy constraint |
| `HonorVcpuOptimization` | `true`, `false` | If true, treats 4 vCPUs as 1 license (matches Oracle model) |

### SQL Server license rules

```bash
# SQL Server Standard — core-based with 0.5 core factor
LICENSE_RULES='location=EC2,coreFactor=0.5'

# SQL Server Enterprise — core-based with 1.0 core factor
LICENSE_RULES='location=EC2,coreFactor=1.0'
```

| Rule key | Values | Effect |
|---|---|---|
| `location` | `EC2`, `Host` | Resource location constraint |
| `coreFactor` | Decimal (0.5, 1.0) | Multiplier applied to physical cores |

**Common mistake:** creating a configuration without `--license-rules`.
It is accepted but no vendor-specific enforcement occurs. This is the
#2 cause of silent non-compliance.

## Step 4 — Resource associations (EC2, SSM, on-prem)

### Association at EC2 instance launch (recommended)

```bash
# Associate via launch template
aws ec2 create-launch-template \
  --launch-template-name oracle-workload-template \
  --launch-template-data '{
    "ImageId":"ami-xxx",
    "InstanceType":"m5.2xlarge",
    "LicenseSpecifications":[
      {"LicenseConfigurationArn":"'"$LIC_CONFIG_ARN"'"}
    ]
  }'

# Associate at run-instances time
aws ec2 run-instances \
  --image-id ami-xxx \
  --instance-type m5.2xlarge \
  --license-specifications "LicenseConfigurationArn=$LIC_CONFIG_ARN"
```

### Association with existing AMI

```bash
aws license-manager associate-license-to-ami \
  --license-configuration-arn "$LIC_CONFIG_ARN" \
  --resource-id ami-xxx
```

For on-premises or SSM-managed instances, SSM inventory MUST be enabled
(see references/cross-account-and-discovery.md).

## Step 5 — Cross-account sharing via Organizations

### Verify and enable prerequisites

```bash
# Check Organization feature set (must be ALL)
aws organizations describe-organization \
  --query 'Organization.FeatureSet' --output text

# Enable License Manager as a trusted service
aws organizations enable-aws-service-access \
  --service-principal license-manager.amazonaws.com

# Register a delegated administrator
aws organizations register-delegated-administrator \
  --account-id 999999999999 \
  --service-principal license-manager.amazonaws.com
```

### Share the license configuration

```bash
# Share to an Organizational Unit (auto-accepted)
aws license-manager create-license-configuration-cross-account \
  --license-configuration-arn "$LIC_CONFIG_ARN" \
  --target-organization-structure '{"OrganizationalUnits":["ou-app-abcdef"]}' \
  --region us-east-1

# Share to specific accounts (requires acceptance)
aws license-manager create-license-configuration-cross-account \
  --license-configuration-arn "$LIC_CONFIG_ARN" \
  --target-organization-structure '{"Accounts":["111122223333"]}' \
  --region us-east-1
```

## Step 6 — Automated discovery via Systems Manager

License Manager uses SSM inventory to discover resources and count
consumption automatically.

```bash
# Enable License Manager integration with SSM
aws license-manager update-service-settings \
  --organization-configuration '{"EnableIntegration":true}' \
  --region us-east-1

# Verify SSM inventory is collecting data
aws ssm get-inventory \
  --query 'Entities[*].{Id:Id,Type:Data.\"AWS:InstanceInformation\".Content[0].ResourceType}' \
  --region us-east-1
```

**Critical:** without SSM inventory, License Manager cannot discover
on-premises or cross-account resources.

## Step 7 — License violations detection and alerting

Hard-limit violations (`LicenseRulesEnforce=true`) BLOCK non-compliant
launches and emit events. Alerting requires EventBridge + SNS.

```bash
# Create EventBridge rule for license violations
aws events put-rule \
  --name license-manager-violations \
  --event-pattern '{
    "source": ["aws.license-manager"],
    "detail-type": ["License Manager License Configuration Violation"]
  }'

# Add SNS target
aws events put-targets \
  --rule license-manager-violations \
  --targets '{"Id":"1","Arn":"arn:aws:sns:us-east-1:123456789012:license-alerts"}'

# List usage records (consumption)
aws license-manager list-usage-records-for-license-configuration \
  --license-configuration-arn "$LIC_CONFIG_ARN" --region us-east-1
```

## Step 8 — Self-service portal grants

Grants allow delegated users to consume licenses without direct console
access.

```bash
# Create a grant with expiry (recommended)
aws license-manager create-grant \
  --grant-name "dev-team-oracle-grant" \
  --license-configuration-arn "$LIC_CONFIG_ARN" \
  --principals '["arn:aws:iam::123456789012:role/DevTeamRole"]' \
  --allowed-operations '["CreateGrant","CheckoutLicense","ViewGrant","ListLicenses"]' \
  --expiration "2026-09-05T00:00:00Z" \
  --region us-east-1
```

**Security note:** grants without an expiry create permanent access.
Always set `--expiration` for non-permanent roles.

## Step 9 — Oracle license tracking specifics

- **Counting type:** `vCPU` (Oracle is licensed per vCPU, minimum 2).
- **HonorVcpuOptimization:** when true, treats 4 vCPUs as 1 license
  when thread scheduling is enabled (matches Oracle's processor model).
- **Tenancy:** `Shared` (default), `Instance` (dedicated instance),
  `Host` (dedicated host — required for some Oracle BYOL scenarios).

```bash
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

- **Counting type:** `Core` (physical cores, not vCPUs).
- **Core factor:** 0.5 for Standard, 1.0 for Enterprise. Multiplies
  physical cores to compute consumption.
- **Minimum:** 4 cores per physical processor.

```bash
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

- **IAM Identity Center integration (2023-2024):** Self-service portal
  supports SSO for non-IAM users, simplifying grant access.
- **Enhanced violation reporting (2023-2024):** Richer EventBridge
  details — resource ARN, configuration ARN, violation reason code.
- **Cross-Region license tracking (2023-2024):** Aggregated usage
  reporting across regions within the same account.
- **Terraform provider improvements (2023-2024):** `license_rule`
  now supports structured map, improving readability.
- **Marketplace integration (2024-2025):** Tracks Marketplace-
  purchased software alongside BYOL configurations.
- **CloudWatch metric enhancements (2024-2025):** Consumption metrics
  published to CloudWatch (consumed, remaining), enabling dashboards.

## NEVER do these things

1. **NEVER confuse license count with vCPU count.** The
   `LicenseCountingType` determines what is measured. A count of 100
   with vCPU counting = 100 vCPUs, NOT 100 instances.

2. **NEVER create a configuration without license rules for vendor-
   specific licenses.** Oracle and SQL Server require specific rule
   strings. Without rules, the configuration exists but does NOT
   enforce vendor conditions.

3. **NEVER assume cross-account sharing works without Organizations.**
   Cross-account sharing requires Organizations all-features, License
   Manager as a trusted service, and a delegated administrator.

4. **NEVER forget SSM inventory for on-premises discovery.** EC2
   instances are tracked via launch association, but on-premises
   requires SSM inventory with `Aws:SoftwareInventory`.

5. **NEVER use soft limit when compliance requires blocking.** Soft
   limit (enforce=false) only alerts. For compliance-critical licenses,
   use hard limit (enforce=true).

6. **NEVER create grants without an expiry for temporary roles.** Set
   `--expiration` for contractor, developer, or temporary roles.

7. **NEVER assume rule syntax errors are caught at creation.** License
   Manager accepts the configuration but enforcement may silently fail.
   Validate rules against vendor documentation.

8. **NEVER skip the delegated administrator for multi-account Orgs.**
   Without it, license management must be from the management account,
   violating least-privilege.

9. **NEVER forget CloudWatch Events for violation alerting.** Hard-
   limit violations emit events, but without EventBridge + SNS, no one
   is notified.

10. **NEVER mix counting types within the same vendor's model.** Oracle
    is vCPU-counted. SQL Server is core-counted. Cross-assigning
    produces non-compliant tracking.

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
  [✓] Grants: 1 grant (dev-team-oracle-grant, principal DevTeamRole)
  [✓] Tags: Vendor=Oracle, Environment=production
VERIFICATION_COMMANDS:
  aws license-manager get-license-configuration --license-configuration-arn arn:aws:license-manager:us-east-1:123456789012:license-configuration:lic-aaa111222333444aaa --region us-east-1
  aws license-manager list-usage-records-for-license-configuration --license-configuration-arn arn:aws:license-manager:us-east-1:123456789012:license-configuration:lic-aaa111222333444aaa --region us-east-1
```

## Error handling

### License configuration creation fails with validation error
- Verify `--license-counting-type` is one of `vCPU`, `Instance`, `Core`.
  Verify `--license-count` is a positive integer. Verify `--license-rules`
  syntax matches the vendor rule format.

### Cross-account sharing fails
- Verify Organizations is all-features enabled. Verify License Manager
  is a trusted service. Verify the target account/OU exists in the Org.

### SSM discovery not finding on-premises resources
- Verify the server is an active SSM managed instance. Verify the SSM
  inventory association includes `Aws:SoftwareInventory`. Verify
  `EnableIntegration=true` in discovery settings.

### Violations not being alerted
- Verify `LicenseRulesEnforce=true`. Verify the EventBridge rule matches
  `aws.license-manager` source. Verify the SNS topic policy allows
  EventBridge to publish.

### License consumption not updating
- Verify the configuration is associated with running resources. For
  EC2, verify the association via launch template. For SSM, verify
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
