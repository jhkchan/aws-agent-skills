# Advanced patterns — license-manager-deployer

Mindset misconceptions, the configuration dependency graph, and recent AWS features, moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Mindset — one-line takeaway and three misconceptions (moved from SKILL.md)

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

## Configuration dependency graph (moved from SKILL.md)

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

## Step 11 — Recent features (moved from SKILL.md)

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
