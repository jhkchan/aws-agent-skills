# Patch Groups & Maintenance Windows Reference

Load this reference when planning patch group registration or
maintenance window integration for an SSM Patch Baseline.

## Patch group decision tree

| Scenario | Patch group value | Targeting method |
|---|---|---|
| Web fleet (AL2023) | `al2023-prod-web` | `tag:Patch Group` |
| App fleet (Windows) | `win-prod-app` | `tag:Patch Group` |
| macOS dev fleet | `macos-dev-fleet` | `tag:Patch Group` |
| Multi-tier (web/app/db) | One group per tier | Separate maintenance windows per tier |
| Multi-account (Organizations) | Same group value across accounts | RAM share or per-account baseline |

## Patch group registration

**Tag your instances first:**
```bash
# Tag an EC2 instance with the Patch Group tag
aws ec2 create-tags \
  --resources i-0abc123 \
  --tags "Key=Patch Group,Value=al2023-prod-web"
```

**Register the patch group with the baseline:**
```bash
aws ssm register-patch-baseline-for-patch-group \
  --baseline-id pb-0abc123 \
  --patch-group "al2023-prod-web"
```

**Tag key rules:**
- The tag key MUST be exactly `Patch Group` (case-sensitive).
- `patch-group`, `PatchGroup`, `patch_group` will NOT work.
- The tag value can be any string matching `[A-Za-z0-9:_-]{1,255}`.
- One instance can have only one `Patch Group` tag value.

**Verify patch group registration:**
```bash
aws ssm describe-patch-groups \
  --operating-system AMAZON_LINUX_2023 \
  --query 'Mappings[?PatchGroup==`al2023-prod-web`]'
```

**Verify instances are tagged:**
```bash
aws ec2 describe-instances \
  --filters "Name=tag:Patch Group,Values=al2023-prod-web" \
  --query 'Reservations[].Instances[].InstanceId'
```

## Maintenance window integration

**Decision: do you need a maintenance window?**

| Scenario | Maintenance window? | Why |
|---|---|---|
| Production fleet | YES — controlled install window | Patches install during off-peak hours |
| Dev / staging | Optional — Scan-only association is fine | Auto-patch on schedule is acceptable |
| Air-gapped | YES — custom Sources require staging | Coordinate with mirror sync |
| Regulated (PCI/HIPAA) | YES — audit trail required | Documented patch window for auditors |

**Create a maintenance window:**
```bash
aws ssm create-maintenance-window \
  --name "al2023-prod-patch-window" \
  --schedule "cron(0 2 ? * SUN *)" \
  --duration 2 \
  --cutoff 30 \
  --allow-unassociated-targets \
  --tags '[{"Key":"Environment","Value":"prod"}]'
```

**Schedule reference:**
- `cron(0 2 ? * SUN *)` — every Sunday at 2:00 AM (Region timezone).
- `rate(7 days)` — every 7 days from creation time.
- Use `cron` for day-of-week/time control; use `rate` for interval-based.

**Register targets (instances matching the Patch Group tag):**
```bash
aws ssm register-target-with-maintenance-window \
  --window-id mw-0abc123 \
  --resource-type INSTANCE \
  --targets '[
    {"Key":"tag:Patch Group","Values":["al2023-prod-web"]}
  ]' \
  --owner-information "AL2023 prod web fleet" \
  --name "al2023-web-targets"
```

**Register the patch install task:**
```bash
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

**Task parameter reference:**
- `Operation`: `Scan` (check only, report compliance) or `Install`
  (install approved patches and reboot if needed).
- `SnapshotId`: used for patch snapshot management. Leave empty for
  default behavior.
- `InstallOverrideList`: (optional) S3 URL to a JSON list of specific
  patches to install, overriding the baseline.

## MaxConcurrency and MaxErrors guidance

| Fleet size | MaxConcurrency | MaxErrors | Rationale |
|---|---|---|---|
| < 10 instances | `1` | `1` | One at a time, stop on first error |
| 10-50 instances | `10%` | `3` | 10% at a time, stop after 3 failures |
| 50-200 instances | `5%` | `5` | 5% at a time, broader error tolerance |
| 200+ instances | `1%` | `10` | 1% at a time, high error tolerance |

**Rules:**
- `MaxConcurrency` can be a percentage (`10%`) or a fixed number (`5`).
- `MaxErrors` must be less than or equal to the number of targets.
- For production, set `MaxErrors` low enough to stop before a fleet-wide
  outage (e.g., 3-5 errors out of 100 instances = stop).

## Maintenance window service role

The maintenance window task needs an IAM role with permission to run
`AWS-RunPatchBaseline` on the targets:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["ssm:SendCommand", "ssm:GetCommandInvocation"],
    "Resource": ["arn:aws:ssm:*:*:document/AWS-RunPatchBaseline",
                 "arn:aws:ec2:*:*:instance/*"]
  }]
}
```

The trust policy must allow `ssm.amazonaws.com`:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ssm.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

## Scan-only association (no maintenance window)

For environments where you want compliance reporting without automatic
installation, create a State Manager association instead of a
maintenance window:

```bash
aws ssm create-association \
  --name AWS-RunPatchBaseline \
  --targets '[{"Key":"tag:Patch Group","Values":["al2023-prod-web"]}]' \
  --schedule-expression "rate(1 day)" \
  --parameters '{"Operation":["Scan"]}' \
  --compliance-severity CRITICAL
```

This scans daily and reports compliance without installing patches.
