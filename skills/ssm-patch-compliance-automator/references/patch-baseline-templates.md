# Patch Baseline Templates Reference

Supplementary reference for the SSM Patch Compliance Automator skill. Use
when creating OS-specific patch baselines, selecting patch filters, or
debugging baseline-approval issues.

## Filter key reference per OS

Each operating system supports a different set of patch-filter keys.
Using the wrong key produces an empty baseline (no patches approved).

| OS | Supported filter keys | Common values |
|---|---|---|
| AMAZON_LINUX_2 | `PRODUCT`, `CLASSIFICATION`, `SEVERITY` | Product: `Amazon Linux 2`; Classification: `Security`, `Bugfix`; Severity: `Critical`, `Important`, `Medium`, `Low` |
| AMAZON_LINUX_2023 | `PRODUCT`, `CLASSIFICATION`, `SEVERITY` | Product: `Amazon Linux 2023`; same classification/severity as AL2 |
| UBUNTU_20_04 | `PRODUCT`, `PRIORITY`, `SECTION` | Product: `Ubuntu 20.04`; Priority: `Critical`, `Important`, `Medium`, `Low` |
| UBUNTU_22_04 | `PRODUCT`, `PRIORITY`, `SECTION` | Product: `Ubuntu 22.04`; same priority values |
| UBUNTU_24_04 | `PRODUCT`, `PRIORITY`, `SECTION` | Product: `Ubuntu 24.04`; same priority values |
| WINDOWS | `PRODUCT`, `CLASSIFICATION`, `MSRC_SEVERITY` | Product: e.g., `WindowsServer2022`; Classification: `Security Updates`, `Critical Updates`, `Update Rollups`, `Service Packs`; MSRC_SEVERITY: `Critical`, `Important`, `Moderate`, `Low` |
| REDHAT_ENTERPRISE_LINUX | `PRODUCT`, `CLASSIFICATION`, `SEVERITY` | Product: `RedHatEnterpriseLinux`; Classification: `Security`, `Bugfix`, `Enhancement`; Severity: `Critical`, `Important`, `Moderate`, `Low` |
| CENTOS | `PRODUCT`, `CLASSIFICATION`, `SEVERITY` | Same as RHEL (CentOS 7 is EOL) |

## Amazon Linux 2023 — production baseline template

```bash
aws ssm create-patch-baseline \
  --name "al2023-prod-baseline" \
  --operating-system AMAZON_LINUX_2023 \
  --approval-rules '{
    "PatchRules": [
      {
        "PatchFilterGroup": [
          {"Key": "PRODUCT", "Values": ["Amazon Linux 2023"]},
          {"Key": "CLASSIFICATION", "Values": ["Security"]},
          {"Key": "SEVERITY", "Values": ["Critical", "Important"]}
        ],
        "ComplianceLevel": "CRITICAL",
        "ApproveAfterDays": 0,
        "EnableNonSecurity": false
      },
      {
        "PatchFilterGroup": [
          {"Key": "PRODUCT", "Values": ["Amazon Linux 2023"]},
          {"Key": "CLASSIFICATION", "Values": ["Security", "Bugfix"]}
        ],
        "ComplianceLevel": "MEDIUM",
        "ApproveAfterDays": 7,
        "EnableNonSecurity": true
      }
    ]
  }'
```

## Ubuntu 22.04 — production baseline template

```bash
aws ssm create-patch-baseline \
  --name "ubuntu2204-prod-baseline" \
  --operating-system UBUNTU_22_04 \
  --approval-rules '{
    "PatchRules": [
      {
        "PatchFilterGroup": [
          {"Key": "PRODUCT", "Values": ["Ubuntu22.04"]},
          {"Key": "PRIORITY", "Values": ["Critical", "Important"]}
        ],
        "ComplianceLevel": "CRITICAL",
        "ApproveAfterDays": 0
      },
      {
        "PatchFilterGroup": [
          {"Key": "PRODUCT", "Values": ["Ubuntu22.04"]},
          {"Key": "PRIORITY", "Values": ["Medium"]}
        ],
        "ComplianceLevel": "MEDIUM",
        "ApproveAfterDays": 14
      }
    ]
  }'
```

## Windows Server 2022 — production baseline template

```bash
aws ssm create-patch-baseline \
  --name "win2022-prod-baseline" \
  --operating-system WINDOWS \
  --approval-rules '{
    "PatchRules": [
      {
        "PatchFilterGroup": [
          {"Key": "MSRC_SEVERITY", "Values": ["Critical", "Important"]},
          {"Key": "CLASSIFICATION", "Values": ["Security Updates"]}
        ],
        "ComplianceLevel": "CRITICAL",
        "ApproveAfterDays": 3
      },
      {
        "PatchFilterGroup": [
          {"Key": "MSRC_SEVERITY", "Values": ["Moderate"]},
          {"Key": "CLASSIFICATION", "Values": ["Security Updates", "Update Rollups"]}
        ],
        "ComplianceLevel": "MEDIUM",
        "ApproveAfterDays": 14
      }
    ]
  }'
```

## Emergency baseline (zero-day response)

```bash
aws ssm create-patch-baseline \
  --name "al2023-emergency-zero-day" \
  --operating-system AMAZON_LINUX_2023 \
  --approval-rules '{
    "PatchRules": [
      {
        "PatchFilterGroup": [
          {"Key": "PRODUCT", "Values": ["Amazon Linux 2023"]},
          {"Key": "CLASSIFICATION", "Values": ["Security"]}
        ],
        "ComplianceLevel": "CRITICAL",
        "ApproveAfterDays": 0
      }
    ]
  }' \
  --approved-patches '["CVE-2026-1234-fix-package"]' \
  --approved-patches-compliance-level "CRITICAL"
```

## Rejected-patches behavior

```bash
# Reject specific problematic packages
aws ssm update-patch-baseline \
  --baseline-id "pb-0abc123def" \
  --rejected-patches '["kernel-6.1.55-*.el9"]' \
  --rejected-patches-action "BLOCK"
```

`RejectedPatchesAction` values:
- `BLOCK` (default) — the patch is blocked from installation even if
  it matches an approval rule. Scan reports it as missing.
- `ALLOW_AS_DEPENDENCY` — the patch can be installed as a dependency
  of another approved patch, but is not installed on its own.

## ComplianceLevel values

| ComplianceLevel | Meaning | Config impact |
|---|---|---|
| `CRITICAL` | Must be patched immediately | Config reports as CRITICAL non-compliance |
| `HIGH` | High priority | Config reports as HIGH non-compliance |
| `MEDIUM` | Medium priority | Config reports as MEDIUM non-compliance |
| `LOW` | Low priority | Config reports as LOW non-compliance |
| `INFORMATIONAL` | Informational only | Config reports as INFORMATIONAL |
| `UNSPECIFIED` | No severity assigned | Config reports as UNSPECIFIED |

## Patch-source configuration (custom repositories)

For instances that pull from a custom repository (e.g., internal mirror):

```bash
aws ssm create-patch-baseline \
  --name "al2023-internal-repo-baseline" \
  --operating-system AMAZON_LINUX_2023 \
  --sources '[
    {
      "Name": "internal-mirror",
      "Products": ["Amazon Linux 2023"],
      "Configuration": "[amzn2023]\nname=Amazon Linux 2023 internal mirror\nbaseurl=https://internal-mirror.company.com/al2023/\nenabled=1\ngpgcheck=1\ngpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-amazon-linux-2023"
    }
  ]'
```

Use this when the fleet is in a private VPC and uses a local mirror
instead of the public Amazon Linux repos. Verify the mirror is
reachable from the instances before deploying the baseline.

## Appendix A — OS-specific baseline quick reference (moved from SKILL.md)

| OS | Filter keys | Typical approval |
|---|---|---|
| AL2/AL2023 | `CLASSIFICATION`, `SEVERITY` | Critical: 0d; Medium: 7d |
| Ubuntu | `CLASSIFICATION`, `PRIORITY` | Critical: 0d; Standard: 7d |
| Windows | `MSRC_SEVERITY`, `CLASSIFICATION` | Critical: 3d (after Patch Tuesday) |
| RHEL | `CLASSIFICATION`, `SEVERITY` | Critical: 0d; Medium: 7d |

For detailed templates per OS, see **references/patch-baseline-templates.md**.
