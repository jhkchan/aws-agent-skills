# End-to-end usage scenario: ebs-volume-auditor

A walkthrough showing the skill auditing an EBS volume that is
simultaneously unencrypted (HIGH) AND gp2 (LOW) AND marked
`DeleteOnTermination: true` (CONFIG_GAP finding) — demonstrating severity
aggregation, the encryption-immutability remediation flow, and the
assume-breach workflow for snapshot lineage.

## Input (user prompt)

> Review this EBS volume before our PCI-DSS audit next week. It hosts the
> application config directory for our checkout service.

```json
{
  "VolumeId": "vol-0prod-checkout-config",
  "State": "in-use",
  "Size": 50,
  "VolumeType": "gp2",
  "Encrypted": false,
  "Iops": 150,
  "Attachments": [
    {
      "InstanceId": "i-0checkoutworker-prod",
      "State": "attached",
      "DeleteOnTermination": true,
      "AttachTime": "2026-04-01T08:00:00Z"
    }
  ],
  "Tags": [
    {"Key": "Name", "Value": "checkout-config-prod"},
    {"Key": "env", "Value": "prod"}
  ]
}
```

Region encryption-by-default: `false`

## Skill output

```text
RESOURCE: vol-0prod-checkout-config
VERDICT: UNENCRYPTED
REASON: Volume is unencrypted (Step 1, HIGH) — PCI-DSS violation. The
volume is also gp2 (legacy type) and the attachment has
DeleteOnTermination: true, compounding the exposure. Region does not
enforce encryption-by-default, so future volumes inherit the same gap.
FINDINGS:
  - [HIGH] Encrypted is false — PCI-DSS Requirement 3.4 violation; data
    at rest is unencrypted (Step 1). The volume hosts checkout service
    config which typically contains merchant credentials and API keys.
  - [CONFIG_GAP] DeleteOnTermination: true on a data volume — terminating
    i-0checkoutworker-prod destroys this volume irrecoverably. Data
    volumes should set DeleteOnTermination: false (not in verdict enum;
    surfaced as a finding).
  - [LOW] VolumeType gp2 — upgrade path gp3, ~20% cheaper, IOPS/throughput
    independently tunable (Step 5)
  - [CONFIG_GAP] Region encryption-by-default is false — future volumes
    will also be unencrypted (Step 1, account-level)
REMEDIATION:
  1. HIGH — Snapshot and re-create encrypted. Encryption is immutable:
     SNAP=$(aws ec2 create-snapshot --volume-id vol-0prod-checkout-config \
       --description "PCI-encrypt-migration" --query SnapshotId --output text)
     aws ec2 wait snapshot-completed --snapshot-ids $SNAP
     ENC=$(aws ec2 copy-snapshot --source-snapshot-id $SNAP \
       --source-region us-east-1 --encrypted \
       --kms-key-id arn:aws:kms:us-east-1:111111111111:key/prod-key \
       --query SnapshotId --output text)
     aws ec2 wait snapshot-completed --snapshot-ids $ENC
     NEW=$(aws ec2 create-volume --snapshot-id $ENC \
       --availability-zone us-east-1a --volume-type gp3 --encrypted \
       --kms-key-id arn:aws:kms:us-east-1:111111111111:key/prod-key \
       --query VolumeId --output text)
     aws ec2 wait volume-available --volume-ids $NEW
     aws ec2 attach-volume --volume-id $NEW \
       --instance-id i-0checkoutworker-prod --device /dev/sdf
     aws ec2 modify-instance-attribute --instance-id i-0checkoutworker-prod \
       --block-device-mappings "[{\"DeviceName\":\"/dev/sdf\",\"Ebs\":{\"DeleteOnTermination\":false}}]"
     aws ec2 detach-volume --volume-id vol-0prod-checkout-config
     aws ec2 delete-volume --volume-id vol-0prod-checkout-config
  2. CONFIG_GAP — Account-level fix (do this FIRST to stop the bleeding):
     aws ec2 enable-ebs-encryption-by-default --region us-east-1
  3. LOW — Moot; the new volume will be gp3.
```

## What the skill caught that a generic assistant misses

1. **PCI-DSS Requirement 3.4 citation.** A generic assistant says
   "encryption is recommended." The skill cites the specific compliance
   requirement (PCI-DSS 3.4) and frames the finding as a violation, not a
   suggestion — which is how an auditor will treat it.

2. **The DeleteOnTermination footgun on a data volume.** A generic
   assistant flags the missing encryption but misses that terminating the
   worker instance will destroy the config volume irrecoverably. The
   skill surfaces this as a CONFIG_GAP finding inside the verdict (it
   does not change the verdict because it is not in the enum, but it is
   in FINDINGS).

3. **Encryption-immutability remediation flow.** A generic assistant
   suggests "enable encryption on the volume." That is impossible — EBS
   encryption is fixed at creation. The skill gives the correct 7-step
   migration flow (snapshot → copy-snapshot --encrypted → create-volume
   → attach → fix DeleteOnTermination → detach → delete).

4. **Account-level root cause.** The region's encryption-by-default is
   `false` — even after fixing this one volume, the next volume created
   in the region will also be unencrypted. The skill surfaces
   `enable-ebs-encryption-by-default` as the higher-leverage remediation.

5. **Severity aggregation.** The verdict is UNENCRYPTED (HIGH, worst
   finding) but the FINDINGS list shows the per-dimension breakdown: HIGH
   for the encryption gap, CONFIG_GAP for DeleteOnTermination and for the
   account-level setting, LOW for the gp2 type. The operator can triage
   each finding independently.

## Slash-command invocation

```
/aws:audit-ebs-volume
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this EBS volume before our PCI audit"
```

The orchestrator emits
`[Phase: Audit | Skills routed: ebs-volume-auditor]` and hands off to
this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit this EBS volume for PCI"
# [Phase: Audit | Skills routed: ebs-volume-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the volume, validate the posture:

```bash
# Verify the new volume is encrypted gp3
aws ec2 describe-volumes --volume-ids <new-vol-id> \
  --profile default --output json | jq '.Volumes[0] | {Encrypted, VolumeType, KmsKeyId}'

# Confirm encryption-by-default is now on for the region
aws ec2 get-ebs-encryption-by-default --region us-east-1 --profile default

# Sweep for other unencrypted volumes in the account/region
aws ec2 describe-volumes --filters Name=encrypted,Values=false \
  --profile default --region us-east-1 --output text \
  --query 'Volumes[*].VolumeId'

# Sweep for public snapshots (run per region)
for R in us-east-1 us-west-2 eu-west-1 ap-southeast-1; do
  aws ec2 describe-snapshots --owner-ids self --region $R \
    --profile default --query 'Snapshots[*].SnapshotId' --output text |
    tr '\t' '\n' |
    xargs -I{} aws ec2 describe-snapshot-attribute \
      --snapshot-id {} --attribute createVolumePermission \
      --region $R --profile default --output json 2>/dev/null |
    jq -r 'select(.CreateVolumePermissions[0].Group=="all") | .SnapshotId'
done
```

Then monitor CloudTrail for `CreateVolume` events from unexpected accounts
for any snapshot that was public during the exposure window.
