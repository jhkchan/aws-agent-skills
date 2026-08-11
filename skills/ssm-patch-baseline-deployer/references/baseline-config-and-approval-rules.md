# Patch Baseline Config & Approval Rules Reference

Load this reference when planning or executing any SSM Patch Baseline
deployment. The procedures below are the canonical baseline
configurations, approval rule patterns, and verification sequences for
each OS archetype.

## Decision tree — which baseline archetype

| Scenario | Use | Why |
|---|---|---|
| Amazon Linux 2023 fleet | **AL2023 custom baseline, product `Amazon Linux 2023`** | AL2023 uses dnf, not yum |
| Windows Server fleet | **Windows baseline, MSRC severity filter** | Microsoft severity classification |
| macOS fleet (SSM-managed) | **macOS baseline, product `macOS`** | New OS support (2024-2026) |
| Air-gapped environment | **Custom baseline with `Sources`** | Local mirror repo config |
| Dev / staging | **ApproveAfterDays 0-3** | Quick turnaround for testing |
| Production (regulated) | **ApproveAfterDays 3-7 + maintenance window** | Soak time + controlled install |
| Emergency security patch | **Separate rule, ApproveAfterDays 0, CRITICAL** | Bypass the normal soak period |

## Amazon Linux 2023 procedure

**When to use:** EC2 instances running Amazon Linux 2023.

**Pre-checks:**
1. Operating System: `AMAZON_LINUX_2023`.
2. Product filter: `Amazon Linux 2023` (NOT `Amazon Linux 2`).
3. Classification: `Security`, `Bugfix` are valid for AL2023.
4. Severity: `Critical`, `Important`, `Medium`, `Low` are valid.

**CLI structure:**
```bash
aws ssm create-patch-baseline \
  --name "al2023-prod-security" \
  --operating-system AMAZON_LINUX_2023 \
  --approval-rules '{
    "PatchRules": [{
      "PatchFilterGroup": {
        "OperatingSystem": "AMAZON_LINUX_2023",
        "PatchFilters": [
          {"Key":"PRODUCT","Values":["Amazon Linux 2023"]},
          {"Key":"CLASSIFICATION","Values":["Security","Bugfix"]},
          {"Key":"SEVERITY","Values":["Critical","Important"]}
        ]
      },
      "ApproveAfterDays": 7,
      "ComplianceLevel": "CRITICAL",
      "EnableNonSecurity": true
    }]
  }'
```

**Common failure modes:**
- "Zero patches approved" — product filter is `Amazon Linux 2` instead of
  `Amazon Linux 2023`. The most common AL2023 patching mistake.
- "Compliance shows all instances compliant" — same root cause: zero
  patches match means zero patches are missing.

## Windows Server procedure

**When to use:** EC2 or on-prem instances running Windows Server.

**Pre-checks:**
1. Operating System: `WINDOWS_SERVER`.
2. Product: `WindowsServer2019`, `WindowsServer2022`, `WindowsServer2016`,
   `WindowsServer2012R2`.
3. Classification: `Critical Updates`, `Security Updates`, `Update
  Rollups`, `Service Packs`.
4. Severity: `MSRC_SEVERITY` key with `Critical`, `Important`, `Medium`,
  `Low`.

**CLI structure:**
```bash
aws ssm create-patch-baseline \
  --name "win-prod-critical" \
  --operating-system WINDOWS_SERVER \
  --approval-rules '{
    "PatchRules": [{
      "PatchFilterGroup": {
        "OperatingSystem": "WINDOWS_SERVER",
        "PatchFilters": [
          {"Key":"PRODUCT","Values":["WindowsServer2022"]},
          {"Key":"CLASSIFICATION","Values":["Critical Updates","Security Updates"]},
          {"Key":"MSRC_SEVERITY","Values":["Critical"]}
        ]
      },
      "ApproveAfterDays": 0,
      "ComplianceLevel": "CRITICAL",
      "EnableNonSecurity": false
    }]
  }' \
  --rejected-patches '["KB5012345"]' \
  --rejected-patches-action BLOCK_AS_PENDING
```

## Ubuntu procedure

**When to use:** EC2 instances running Ubuntu 22.04 or 20.04.

**CLI structure:**
```bash
aws ssm create-patch-baseline \
  --name "ubuntu-prod-security" \
  --operating-system UBUNTU_22.04 \
  --approval-rules '{
    "PatchRules": [{
      "PatchFilterGroup": {
        "OperatingSystem": "UBUNTU_22.04",
        "PatchFilters": [
          {"Key":"PRODUCT","Values":["Ubuntu2204"]},
          {"Key":"CLASSIFICATION","Values":["Security"]},
          {"Key":"PRIORITY","Values":["required","important"]}
        ]
      },
      "ApproveAfterDays": 5,
      "ComplianceLevel": "HIGH"
    }]
  }'
```

**Note:** Ubuntu uses `PRIORITY` (not `SEVERITY`) for patch filtering.
Values are `required`, `important`, `optional`.

## macOS procedure

**When to use:** macOS instances managed by SSM (not Jamf-only).

**Pre-checks:**
1. SSM agent installed on the macOS instance.
2. Instance profile includes `AmazonSSMManagedInstanceCore`.
3. Operating System: `MACOS`.
4. Product: `macOS`. Classification: `Security`.

**CLI structure:**
```bash
aws ssm create-patch-baseline \
  --name "macos-prod-baseline" \
  --operating-system MACOS \
  --approval-rules '{
    "PatchRules": [{
      "PatchFilterGroup": {
        "OperatingSystem": "MACOS",
        "PatchFilters": [
          {"Key":"PRODUCT","Values":["macOS"]},
          {"Key":"CLASSIFICATION","Values":["Security"]}
        ]
      },
      "ApproveAfterDays": 3,
      "ComplianceLevel": "HIGH"
    }]
  }'
```

## Approval rule filter reference

| OS | Product example | Classification key | Severity key | Severity values |
|---|---|---|---|---|
| AMAZON_LINUX_2023 | `Amazon Linux 2023` | `CLASSIFICATION` | `SEVERITY` | Critical, Important, Medium, Low |
| AMAZON_LINUX_2 | `Amazon Linux 2` | `CLASSIFICATION` | `SEVERITY` | Critical, Important, Medium, Low |
| UBUNTU_22.04 | `Ubuntu2204` | `CLASSIFICATION` | `PRIORITY` | required, important, optional |
| WINDOWS_SERVER | `WindowsServer2022` | `CLASSIFICATION` | `MSRC_SEVERITY` | Critical, Important, Medium, Low |
| MACOS | `macOS` | `CLASSIFICATION` | (none) | (classification only) |
| REDHAT_ENTERPRISE_LINUX_9 | `RedHatEnterpriseLinux9` | `CLASSIFICATION` | `SEVERITY` | Critical, Important, Moderate, Low |
| DEBIAN_12 | `Debian12` | `CLASSIFICATION` | `PRIORITY` | required, important, optional |

## Verification commands

```bash
# Verify baseline was created
aws ssm describe-patch-baseline \
  --baseline-id <id> \
  --query 'ApprovalRules.PatchRules[0].[ApproveAfterDays,ComplianceLevel]'

# List patch groups registered to the baseline
aws ssm describe-patch-groups \
  --operating-system AMAZON_LINUX_2023 \
  --query 'Mappings[?BaselineId==`<id>`].[PatchGroup,BaselineId]'

# Check patch compliance for an instance
aws ssm describe-instance-patch-states \
  --instance-ids i-0abc123 \
  --query 'InstancePatchStates[].[InstanceId,Operation,InstalledCount,InstalledPendingCount,InstalledRejectedCount,MissingCount,FailedCount]'

# List available patches matching the baseline filters
aws ssm describe-available-patches \
  --filters '[{"Key":"PRODUCT","Values":["Amazon Linux 2023"]},{"Key":"CLASSIFICATION","Values":["Security"]}]' \
  --max-results 50
```
