# End-to-end usage scenario: ec2-instance-recovery-operator

A walkthrough showing the skill planning a stop/start recovery for a
SystemStatus-impaired instance, with all pre-checks passing and the
operator confirming at the CONFIRM gate. Contrasted with the BLOCKED
case where an ASG-managed instance-store instance cannot be safely
stop/started.

## Input (user prompt)

> Instance `i-0abcdef1234567890` has a failing system status check
> (hardware degradation). It's EBS-backed, not in an ASG, no Capacity
> Reservation. Stop/start to relocate to a new host.

```json
{
  "Operation": "stop-start",
  "Instance": "i-0abcdef1234567890",
  "InstanceStatus": {
    "State": "running",
    "SystemStatus": {"Status": "impaired"},
    "InstanceStatus": {"Status": "ok"},
    "Events": []
  },
  "InstanceDetails": {
    "InstanceType": "m5.2xlarge",
    "RootDeviceType": "ebs",
    "BlockDeviceMappings": [
      {"DeviceName": "/dev/xvda", "Ebs": {"VolumeId": "vol-0abc", "DeleteOnTermination": true}}
    ],
    "Placement": {"Tenancy": "default"},
    "CapacityReservationId": null
  },
  "AsgMembership": null,
  "ExistingRecoveryAlarms": []
}
```

## Skill output

```text
OPERATION: stop-start
VERDICT: READY
TARGET: i-0abcdef1234567890 (state: running, system-status: impaired,
        instance-status: ok)
PRE_CHECKS:
  - [PASS] Instance exists, not terminated
  - [PASS] SystemStatus impaired (host issue), InstanceStatus ok
  - [PASS] RootDeviceType: ebs (no data loss on stop)
  - [PASS] No instance-store block devices
  - [PASS] ASG: not a member (no suspend needed)
  - [PASS] Capacity Reservation: not bound
  - [PASS] Placement: default (no cluster constraint)
STEPS:
  1. CONFIRM: About to stop and start i-0abcdef1234567890 in account
     111111111111 region us-east-1. This will RELOCATE to a new host
     (clears hardware impairment), cause 2-5 min downtime, preserve
     EBS. Proceed? (yes/no)
  2. aws ec2 stop-instances --instance-ids i-0abcdef1234567890
  3. Poll describe-instance-status every 30s until stopped
  4. aws ec2 start-instances --instance-ids i-0abcdef1234567890
  5. Poll describe-instance-status every 30s until running + ok
POST_VERIFY:
  - (pending execution)
  - describe-instance-status: both checks ok
  - Application health endpoint: HTTP 200
  - EBS volume vol-0abc reattached at /dev/xvda
NOTES:
  - Stop/start is correct for SystemStatus impaired. Reboot would
    keep the instance on the same impaired host.
  - Set up a CloudWatch recovery alarm for auto-recovery:
    aws cloudwatch put-metric-alarm --alarm-name recover-i-0abcdef
      --metric-name StatusCheckFailed_System --namespace AWS/EC2
      --dimensions Name=InstanceId,Value=i-0abcdef1234567890
      --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold
      --period 60 --evaluation-periods 2
      --alarm-actions arn:aws:automate:us-east-1:ec2:recover
```

## Contrast — BLOCKED case (ASG + instance-store)

If the operator had specified an ASG-managed instance with
`RootDeviceType: instance-store`, the pre-check gate would fire and
no CLI would execute:

```text
OPERATION: stop-start
VERDICT: BLOCKED
TARGET: i-0abcdef1234567890 (state: running, system-status: impaired,
        instance-status: ok)
PRE_CHECKS:
  - [PASS] Instance exists, not terminated
  - [PASS] SystemStatus impaired (host issue)
  - [FAIL] RootDeviceType: instance-store — stop/start LOSES the
    root volume and all instance-store data. There is no recovery
    path for ephemeral data on a new host.
  - [FAIL] Instance is in ASG prod-web-asg (InService, Healthy).
    Stopping the instance triggers the ASG health check, which marks
    it Unhealthy and TERMINATES it. Suspend HealthCheck before any
    manual stop.
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
NOTES:
  - Two blocking issues: instance-store data loss + ASG termination.
  - Options:
    A) Accept data loss: suspend ASG HealthCheck, stop/start, resume.
       aws autoscaling suspend-processes --auto-scaling-group-name
         prod-web-asg --scaling-processes HealthCheck
       aws ec2 stop-instances --instance-ids i-0abcdef1234567890
       aws ec2 start-instances --instance-ids i-0abcdef1234567890
       aws autoscaling resume-processes --auto-scaling-group-name
         prod-web-asg --scaling-processes HealthCheck
    B) Prefer reboot (same host, preserves instance-store data):
       aws ec2 reboot-instances --instance-ids i-0abcdef1234567890
       But reboot does NOT clear hardware impairment.
    C) Let the ASG handle it: the ASG will detect Unhealthy, launch
       a replacement, and terminate this instance. This is the
       safest path if the workload is stateless.
```

## What the skill caught that a generic assistant misses

1. **Pre-check gate before any CLI executes.** A generic assistant
   emits `stop-instances` directly. The skill runs deterministic
   pre-checks (status check classification, root device type, ASG
   membership, Capacity Reservation, placement group, pending events)
   and BLOCKS before a stop that would lose data or trigger ASG
   termination.

2. **System vs Instance status classification.** A generic assistant
   says "try rebooting." The skill distinguishes SystemStatus
   (hardware → stop/start) from InstanceStatus (OS → reboot or SSM),
   preventing the wrong operation.

3. **Instance-store data-loss warning.** A generic assistant does not
   check `RootDeviceType`. The skill BLOCKS on instance-store root
   volumes, preventing irreversible data loss.

4. **ASG health-check suspension.** A generic assistant omits that
   stopping an ASG instance triggers termination. The skill requires
   `suspend-processes --scaling-processes HealthCheck` before any
   manual stop.

5. **CloudWatch recovery alarm recommendation.** A generic assistant
   omits ongoing monitoring. The skill emits the `put-metric-alarm`
   command with the correct `StatusCheckFailed_System` metric and the
   `ec2:recover` action ARN.

6. **Capacity Reservation re-binding.** A generic assistant omits
   that stop releases the reservation binding. The skill captures
   the reservation ID and emits the `modify-instance-capacity-
   reservation-attributes` command for re-binding on start.

7. **Console output capture before recovery.** A generic assistant
   reboots first. The skill captures `get-console-output` to a local
   file BEFORE any recovery action, preserving the diagnostic state.

## Slash-command invocation

```
/aws:operate-ec2-instance-recovery
```

Or via the orchestrator:

```
/aws:pipeline
You: "instance i-0abcdef has a failing system status check"
```

The orchestrator emits
`[Phase: Operate | Skills routed: ec2-instance-recovery-operator]`
and hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "instance i-0abcdef has a failing system status check"
# [Phase: Operate | Skills routed: ec2-instance-recovery-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the recovery completes:

```bash
# Verify both status checks pass
aws ec2 describe-instance-status \
  --instance-ids i-0abcdef1234567890 \
  --query 'InstanceStatuses[0].{State:InstanceState.Name,
    System:SystemStatus.Status,Instance:InstanceStatus.Status}' \
  --profile default

# Verify EBS volumes reattached
aws ec2 describe-volumes \
  --filters Name=attachment.instance-id,Values=i-0abcdef1234567890 \
  --query 'Volumes[*].[VolumeId,Attachments[0].Device,Attachments[0].State]' \
  --profile default

# Set up auto-recovery alarm for next time
aws cloudwatch put-metric-alarm \
  --alarm-name recover-i-0abcdef \
  --metric-name StatusCheckFailed_System \
  --namespace AWS/EC2 \
  --dimensions Name=InstanceId,Value=i-0abcdef1234567890 \
  --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold \
  --period 60 --evaluation-periods 2 \
  --alarm-actions arn:aws:automate:us-east-1:ec2:recover \
  --profile default
```
