# End-to-end usage scenario: ec2-backup-operator

A walkthrough showing the skill planning a pre-migration AMI creation
from a running prod webapp instance. The operator accepts a crash-
consistent AMI (`--no-reboot=true`) because the webapp is stateless and
the DB has its own snapshot. The skill's pre-checks pass on instance
state, all 3 attached volumes, AMI-name uniqueness, and IAM permissions,
producing a READY plan with the exact `create-image` CLI, the CONFIRM
gate, and the deregister+delete cleanup notes — and contrasted with the
BLOCKED case where a snapshot is referenced by a registered AMI.

## Input (user prompt)

> Pre-migration AMI for the prod webapp i-0prodapp123456789ab. Crash-
> consistent is fine (webapp is stateless; DB has its own snapshot).
> Name it prod-webapp-pre-migration-2026-08-07.

```json
{
  "Operation": "create-image",
  "Target": "i-0prodapp123456789ab",
  "AMIName": "prod-webapp-pre-migration-2026-08-07",
  "NoReboot": true,
  "Instance": {
    "InstanceId": "i-0prodapp123456789ab",
    "State": "running",
    "BlockDeviceMappings": [
      {"DeviceName": "/dev/sda1", "Ebs": {"VolumeId": "vol-0root123", "State": "in-use"}},
      {"DeviceName": "/dev/sdb", "Ebs": {"VolumeId": "vol-0logs123", "State": "in-use"}},
      {"DeviceName": "/dev/sdc", "Ebs": {"VolumeId": "vol-0data123", "State": "in-use"}}
    ],
    "IamInstanceProfile": "arn:aws:iam::111111111111:instance-profile/prod-webapp",
    "Architecture": "x86_64"
  },
  "AMINameUniqueness": {
    "Result": "empty"
  }
}
```

## Skill output

```text
OPERATION: create-image
VERDICT: READY
TARGET: i-0prodapp123456789ab (running, prod webapp)
PRE_CHECKS:
  - [PASS] Instance State running (AMI create allowed)
  - [PASS] All 3 attached volumes State in-use
  - [PASS] AMI Name "prod-webapp-pre-migration-2026-08-07" is unique
  - [PASS] Caller holds ec2:CreateImage on the instance ARN
  - [PASS] --no-reboot=true accepted (crash-consistent AMI for stateless
    webapp; DB has its own snapshot)
STEPS:
  1. CONFIRM: About to create-image from i-0prodapp123456789ab in
     account 111111111111 region us-east-1. With --no-reboot=true, the
     instance will NOT be rebooted (crash-consistent AMI). Estimated
     duration: ~5 minutes (3 volumes, ~500 GB total). Proceed? (yes/no)
  2. aws ec2 describe-volumes \
       --volume-ids vol-0root123 vol-0logs123 vol-0data123 \
       --output json > /tmp/pre-ami-$(date +%s).json
  3. aws ec2 create-image \
       --instance-id i-0prodapp123456789ab \
       --name "prod-webapp-pre-migration-2026-08-07" \
       --description "Pre-migration capture; webapp + logs + data volumes" \
       --no-reboot \
       --tag-specifications \
         "ResourceType=image,Tags=[{Key=source-instance,Value=i-0prodapp123456789ab},{Key=purpose,Value=pre-migration},{Key=delete-after,Value=2026-09-07}]" \
         "ResourceType=snapshot,Tags=[{Key=source-instance,Value=i-0prodapp123456789ab},{Key=purpose,Value=pre-migration}]"
  4. aws ec2 wait image-available --image-ids <ImageId from step 3>
POST_VERIFY:
  - (pending execution)
  - aws ec2 describe-images --image-ids <ImageId> --owners self
    → State: available
  - aws ec2 describe-snapshots --snapshot-ids <snap-1>,<snap-2>,<snap-3>
    → all State: completed
  - Test-launch a t3.medium from the new AMI into a dev subnet to verify
    bootability (architecture matches; volumes attach correctly)
NEW_RESOURCE: (pending — will be ami-0new1234567890abcd + 3 backing
  snapshots)
REBOOT: no (--no-reboot=true; crash-consistent AMI)
NOTES:
  - The AMI references 3 EBS snapshots. Full cleanup when the AMI is no
    longer needed is deregister-image AND delete-snapshot per snapshot
    (deregister alone preserves the snapshots and they keep billing).
  - Tag delete-after=2026-09-07 triggers automated cleanup via a
    scheduled Lambda; review before enabling auto-cleanup.
  - For an app-consistent AMI, re-run without --no-reboot (reboots the
    source instance ~2 min for fs quiesce).
  - AMI launch-permissions: private by default. Share via
    modify-image-attribute --launch-permission to another account;
    ALSO modify-snapshot-attribute --create-volume-permission if the
    recipient needs to create volumes directly from the AMI's snapshots.
  - The webapp is stateless; the AMI's crash-consistent state is fine.
    For databases, prefer stopped-instance AMI or DB-native snapshots.
```

## Contrast — BLOCKED case (snapshot referenced by AMI)

If the operator had tried to delete `snap-0amibacking123` without first
deregistering the AMI it backs, the pre-check gate would fire and no
CLI would execute:

```text
OPERATION: delete-snapshot
VERDICT: BLOCKED
TARGET: snap-0amibacking123
PRE_CHECKS:
  - [PASS] Snapshot State completed (safe to delete in principle)
  - [FAIL] Snapshot referenced by AMI ami-0oldprod
    (describe-images --owners self --filters
    BlockDeviceMapping.SnapshotId=snap-0amibacking123 returned
    ami-0oldprod in State available). Deleting this snapshot would
    brick launches from ami-0oldprod — the volume cannot be created.
  - [PASS] FSR check empty (no FSR cleanup needed)
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
NEW_RESOURCE: (none)
REBOOT: n/a
NOTES:
  - Deregister the AMI first (metadata only; snapshots preserved):
      aws ec2 deregister-image --image-id ami-0oldprod
  - Then re-verify no remaining AMI references the snapshot:
      aws ec2 describe-images --owners self \
        --filters BlockDeviceMapping.SnapshotId=snap-0amibacking123
      MUST return empty.
  - Then re-issue the delete:
      aws ec2 delete-snapshot --snapshot-id snap-0amibacking123
  - Storage cost saving may lag by weeks (EBS snapshots are incremental
    and reference-counted; blocks migrate to later snapshots).
```

## What the skill caught that a generic assistant misses

1. **`--no-reboot` decision explicit.** A generic assistant runs the
   default `create-image`, which reboots the source instance for an
   app-consistent AMI. The skill surfaces the crash-consistent vs app-
   consistent trade-off and lets the operator choose based on workload
   semantics.

2. **Pre-state snapshot for rollback.** A generic assistant omits the
   pre-AMI `describe-volumes` capture. The skill snapshots the volume
   metadata before any state-changing CLI so a failed AMI create can be
   triaged against the pre-state.

3. **Lineage tags.** A generic assistant creates an anonymous AMI. The
   skill tags both the AMI and the snapshots with `source-instance`,
   `purpose`, `delete-after` — enabling automated cleanup, audit trails,
   and cost-allocation tracking.

4. **Cleanup lifecycle (deregister + delete-snapshot).** A generic
   assistant omits that `deregister-image` alone preserves the snapshots
   (they keep billing). The skill surfaces the full cleanup sequence in
   NOTES, so the operator plans the eventual storage-cost recovery.

5. **Launch permissions vs snapshot permissions.** A generic assistant
   conflates the two. The skill surfaces that AMI launch permission does
   NOT share the underlying snapshots — recipients can launch but
   cannot create-volume directly.

6. **Architecture compatibility for test-launch.** A generic assistant
   omits the test-launch verification. The skill surfaces the
   test-launch step (with architecture matching) to verify the AMI is
   bootable before relying on it for migration.

7. **CONFIRM gate.** A generic assistant auto-executes. The skill emits
   `CONFIRM:` and waits — AMI create (without `--no-reboot`) reboots
   the source, and the operator must explicitly approve.

8. **Deregister-before-delete for snapshots.** A generic assistant
   blindly runs `delete-snapshot`. The skill pre-checks AMI references
   and BLOCKS the delete if any AMI uses the snapshot — preventing a
   bricked-launch incident.

## Slash-command invocation

```
/aws:operate-ec2-backup
```

Or via the orchestrator:

```
/aws:pipeline
You: "create a pre-migration AMI from i-0prodapp123456789ab (crash-consistent OK)"
```

The orchestrator emits
`[Phase: Operate | Skills routed: ec2-backup-operator]` and hands off to
this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "create pre-migration AMI from i-0prodapp123456789ab"
# [Phase: Operate | Skills routed: ec2-backup-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the AMI becomes available:

```bash
# Verify the AMI and its backing snapshots
aws ec2 describe-images \
  --image-ids ami-0new1234567890abcd \
  --owners self \
  --profile default \
  --query 'Images[0].[Name,State,BlockDeviceMappings[*].Ebs.SnapshotId,Architecture]'

# Test-launch a t3.medium from the new AMI into a dev subnet
aws ec2 run-instances \
  --image-id ami-0new1234567890abcd \
  --instance-type t3.medium \
  --subnet-id subnet-0dev \
  --security-group-ids sg-0dev \
  --key-name dev-key \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=ami-test-launch},{Key=temp,Value=true},{Key=delete-after,Value=2026-08-10}]" \
  --profile default

# Verify boot and application health
aws ssm send-command \
  --instance-ids <test-instance-id> \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["systemctl status nginx","curl -s -o /dev/null -w \"%{http_code}\" http://localhost"]' \
  --profile default

# After verification, terminate the test instance
aws ec2 terminate-instances --instance-ids <test-instance-id> --profile default

# Plan the eventual cleanup (deregister + delete-snapshot)
aws ec2 describe-images \
  --image-ids ami-0new1234567890abcd \
  --owners self \
  --query 'Images[0].BlockDeviceMappings[*].Ebs.SnapshotId' \
  --output text \
  --profile default
# Then per snapshot: deregister-image + delete-snapshot
```
