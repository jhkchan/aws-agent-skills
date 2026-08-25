# Worked Examples — SSM Patch Baseline Deployer

Common baseline-pattern boilerplate moved from SKILL.md. Load when emitting an exact CLI sequence for an OS archetype.

## Common baseline patterns (boilerplate) (moved from SKILL.md)

### Amazon Linux 2023 — auto-approve security patches in 7 days

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
  }' \
  --tags '[{"Key":"Environment","Value":"prod"},{"Key":"Purpose","Value":"al2023-security"}]'

aws ssm register-patch-baseline-for-patch-group \
  --baseline-id <baseline-id> \
  --patch-group "al2023-prod-web"
```

### Windows Server — auto-approve critical patches immediately

```bash
aws ssm create-patch-baseline \
  --name "win-prod-critical" \
  --operating-system WINDOWS_SERVER \
  --approval-rules '{
    "PatchRules": [{
      "PatchFilterGroup": {
        "OperatingSystem": "WINDOWS_SERVER",
        "PatchFilters": [
          {"Key":"PRODUCT","Values":["WindowsServer2019","WindowsServer2022"]},
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
  --rejected-patches-action BLOCK_AS_PENDING \
  --tags '[{"Key":"Environment","Value":"prod"}]'

aws ssm register-patch-baseline-for-patch-group \
  --baseline-id <baseline-id> \
  --patch-group "win-prod-servers"
```

### macOS — patch baseline with Scan-only operation

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
      "ComplianceLevel": "HIGH",
      "EnableNonSecurity": false
    }]
  }' \
  --tags '[{"Key":"Environment","Value":"prod"}]'

aws ssm register-patch-baseline-for-patch-group \
  --baseline-id <baseline-id> \
  --patch-group "macos-prod-fleet"
```

### Maintenance window integration — Install task

```bash
# Register targets (instances with the Patch Group tag)
aws ssm register-target-with-maintenance-window \
  --window-id mw-0abc123 \
  --resource-type INSTANCE \
  --targets '[
    {"Key":"tag:Patch Group","Values":["al2023-prod-web"]}
  ]' \
  --owner-information "AL2023 prod web fleet" \
  --name "al2023-web-targets"

# Register the patch task
aws ssm register-task-with-maintenance-window \
  --window-id mw-0abc123 \
  --targets '[
    {"Key":"WindowTargetIds","Values":["<target-id>"]}
  ]' \
  --task-arn AWS-RunPatchBaseline \
  --service-role-arn arn:aws:iam::111111111111:role/MaintenanceWindowRole \
  --task-type RUN_COMMAND \
  --task-parameters '{"Operation":["Install"],"SnapshotId":[""]}' \
  --max-concurrency "10%" \
  --max-errors "3" \
  --priority 1 \
  --name "al2023-install-patches" \
  --cloudwatch-output-config '{"CloudWatchOutputEnabled":true}'
```

### Custom repository (air-gapped AL2023)

```bash
aws ssm create-patch-baseline \
  --name "al2023-airgapped" \
  --operating-system AMAZON_LINUX_2023 \
  --approval-rules '{
    "PatchRules": [{
      "PatchFilterGroup": {
        "OperatingSystem": "AMAZON_LINUX_2023",
        "PatchFilters": [
          {"Key":"PRODUCT","Values":["Amazon Linux 2023"]},
          {"Key":"CLASSIFICATION","Values":["Security","Bugfix"]}
        ]
      },
      "ApproveAfterDays": 0,
      "ComplianceLevel": "CRITICAL"
    }]
  }' \
  --sources '[{
    "Name":"my-local-mirror",
    "Products":["Amazon Linux 2023"],
    "Configuration":"[amzn2023]\nname=Amazon Linux 2023 local mirror\nbaseurl=https://mirror.internal.corp/al2023\nenabled=1\ngpgcheck=1\ngpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-amazon-linux-2023"
  }]'
```
