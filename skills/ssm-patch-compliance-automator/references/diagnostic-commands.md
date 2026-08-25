# Diagnostic Commands — SSM Patch Compliance Automator

Pre-flight safety checks moved from SKILL.md. Load before any state-changing operation.

## Pre-flight safety checks (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE** before any state-changing operation.
- **Back up current patch-baseline associations:**
  `aws ssm describe-patch-groups > /tmp/patch-groups-backup.json`
- **Before Scan→Install switch:** run Install manually on 3+ sample
  instances and verify compliance state flips.
- **For critical-instance Install:** route through SSM Change Manager.
