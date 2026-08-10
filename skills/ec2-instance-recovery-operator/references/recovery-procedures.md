# EC2 Instance Recovery Diagnostic Procedures Reference

Load this reference when diagnosing an impaired EC2 instance. The
procedures below are the canonical sequences for each symptom
archetype, with the read-only diagnostic commands and the CLI to fix
each root cause.

## Decision tree — which diagnostic archetype

| Symptom | Use | Why |
|---|---|---|
| `SystemStatus: impaired`, `InstanceStatus: ok` | **Host hardware** | Stop/start relocates; recover reboots same host |
| `InstanceStatus: impaired`, `SystemStatus: ok` | **OS-level** | Reboot or SSM session; stop/start rarely helps |
| Both `impaired` | **Network/ENI** | VPC route table, ENI attachment, SG rules |
| `State: running`, no SSH, SSM `Online` | **Access control** | SG ingress, IAM role, key pair |
| `State: running`, no SSH, SSM `ConnectionLost` | **OS hang** | Reboot; if persistent, EBS detach/attach |
| Console: kernel panic | **Kernel/Module** | EBS detach/attach to revert; stop/start |
| Console: disk full | **Storage** | SSM session to clean; expand EBS |
| `State: stopped` after launch | **User-data** | Check console output; fix user-data |
| ASG rapid churn | **ASG misconfig** | Freeze ASG; diagnose activity history |

## Procedure: System status check failure (hardware degradation)

**Symptom:** `SystemStatus.Status: impaired` AND
`InstanceStatus.Status: ok`.

**Diagnostics:**

```bash
# 1. Confirm status
aws ec2 describe-instance-status --instance-ids <id> \
  --include-all-instances \
  --query 'InstanceStatuses[0].{State:InstanceState.Name,
    System:SystemStatus.Status,Instance:InstanceStatus.Status,
    Events:Events}'

# 2. Check for scheduled events
aws ec2 describe-instance-status --instance-ids <id> \
  --query 'InstanceStatuses[0].Events'

# 3. Check instance store vs EBS root
aws ec2 describe-instances --instance-ids <id> \
  --query 'Reservations[0].Instances[0].{Root:RootDeviceType,
    Devices:BlockDeviceMappings,Placement:Placement}'

# 4. Check ASG membership
aws autoscaling describe-auto-scaling-instances \
  --instance-ids <id>

# 5. Check Capacity Reservation binding
aws ec2 describe-instances --instance-ids <id> \
  --query 'Reservations[0].Instances[0].CapacityReservationId'

# 6. Check existing recovery alarms
aws cloudwatch describe-alarms-for-metric \
  --namespace AWS/EC2 \
  --metric-name StatusCheckFailed_System \
  --dimensions Name=InstanceId,Value=<id>
```

**Recovery options (in priority order):**

| Condition | Action | Command |
|---|---|---|
| No scheduled event, EBS root, no ASG | Stop/start | `aws ec2 stop-instances --instance-ids <id>` then `start-instances` |
| No scheduled event, instance-store root | BLOCK — warn operator | Data loss on stop; use reboot or wait for AWS |
| Pending `system-reboot` event | Wait for AWS | Do NOT manually reboot |
| Pending `instance-stop` event | Stop/start before window | `aws ec2 stop-instances --instance-ids <id>` |
| ASG member | Suspend HealthCheck first | `aws autoscaling suspend-processes --auto-scaling-group-name <asg> --scaling-processes HealthCheck` |
| Capacity Reservation bound | Capture ID, re-bind on start | `aws ec2 modify-instance-capacity-reservation-attributes ...` after start |

## Procedure: CloudWatch recovery alarm configuration

**Goal:** auto-recover the instance on future `SystemStatus` failures
without manual intervention.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name recover-<id> \
  --metric-name StatusCheckFailed_System \
  --namespace AWS/EC2 \
  --dimensions Name=InstanceId,Value=<id> \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --period 60 \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:automate:<region>:ec2:recover \
  --profile <profile>
```

The alarm fires after 2 consecutive 1-minute periods of
`StatusCheckFailed_System >= 1` (i.e., 2 minutes of system status
failure). The recover action reboots the instance on the same host.

**Do NOT use `StatusCheckFailed_Instance` for the recover action.**
The EC2 recover action only addresses hardware (System) failures. An
alarm on `StatusCheckFailed_Instance` with the recover action fires
but does nothing useful — the OS issue persists.

## Procedure: EBS detach/attach for data salvage

**When:** Instance is unreachable (OS hung, SSH/SSM both down) but EBS
volumes are healthy. Goal: repair the filesystem without stop/start.

```bash
# 1. Capture pre-state
aws ec2 describe-volumes \
  --filters Name=attachment.instance-id,Values=<unhealthy-id> \
  --output json > /tmp/volumes-pre.json

# 2. Identify a rescue instance in the same AZ
aws ec2 describe-instances \
  --filters Name=availability-zone,Values=<az> \
            Name=instance-state-name,Values=running \
  --query 'Reservations[*].Instances[*].[InstanceId,PrivateIpAddress]'

# 3. Force detach the root volume from the unhealthy instance
aws ec2 detach-volume \
  --volume-id <vol-id> \
  --instance-id <unhealthy-id> \
  --force

# 4. Attach to the rescue instance
aws ec2 attach-volume \
  --volume-id <vol-id> \
  --instance-id <rescue-id> \
  --device /dev/sdf

# 5. On the rescue instance (via SSH or SSM):
#    sudo mkdir -p /mnt/recovery
#    sudo mount /dev/sdf /mnt/recovery
#    # Fix the issue (e.g., revert bad config, remove kernel module)
#    sudo umount /mnt/recovery

# 6. Detach from rescue
aws ec2 detach-volume \
  --volume-id <vol-id> \
  --instance-id <rescue-id>

# 7. Re-attach to the original instance
aws ec2 attach-volume \
  --volume-id <vol-id> \
  --instance-id <unhealthy-id> \
  --device /dev/xvda

# 8. Start the original instance (if it was stopped)
aws ec2 start-instances --instance-ids <unhealthy-id>
```

**Filesystem check after forced detach:**

```bash
# On the rescue instance, before mounting:
sudo fsck -y /dev/sdf
```

A forced detach (without stopping the instance) can leave the
filesystem in an inconsistent state. Always run `fsck` on the rescue
instance before mounting.

## Procedure: AMI forensic snapshot

**When:** Before any recovery action that could fail or destroy the
instance. The AMI is the point-in-time rollback.

```bash
# For a hung instance (cannot clean shutdown):
aws ec2 create-image \
  --instance-id <id> \
  --name forensic-<id>-$(date +%Y%m%d%H%M%S) \
  --description "Forensic snapshot before recovery" \
  --no-reboot \
  --profile <profile>

# For a healthy instance (clean shutdown):
aws ec2 create-image \
  --instance-id <id> \
  --name ami-<id>-$(date +%Y%m%d%H%M%S) \
  --description "Production AMI" \
  --profile <profile>
```

**Poll for completion:**

```bash
aws ec2 describe-images \
  --image-ids <ami-id> \
  --query 'Images[0].State'
# State transitions: pending -> available

# Check snapshot completion
aws ec2 describe-snapshots \
  --filters Name=description,Values="Created by CreateImage(*) for <id>" \
  --query 'Snapshots[*].[SnapshotId,State,Progress]'
```

AMI creation is async. The API returns immediately; the actual
snapshot takes 5-30 minutes depending on EBS size. Do NOT stop or
terminate the instance until the AMI is `available`.

## Procedure: ASG instance replacement

**When:** The instance is in an ASG and health checks are failing.
Prefer the ASG's managed replacement over manual recovery.

```bash
# 1. Check ASG configuration
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names <asg> \
  --query 'AutoScalingGroups[0].{Min:MinSize,Max:MaxSize,
    Desired:DesiredCapacity,HealthCheckType:HealthCheckType,
    HealthCheckGracePeriod:HealthCheckGracePeriod}'

# 2. Check ASG activity (why instances are churning)
aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name <asg> \
  --max-records 10

# 3. Check ELB / target group health
aws elbv2 describe-target-health \
  --target-group-arn <tg-arn>

# 4. To stand back and let the ASG handle it:
#    (ensure HealthCheck process is Resumed)
aws autoscaling resume-processes \
  --auto-scaling-group-name <asg> \
  --scaling-processes HealthCheck

# 5. To freeze the ASG (stop churn for diagnosis):
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name <asg> \
  --min-size 0 --max-size 0 --desired-capacity 0
```

**ASG-managed replacement flow:**
1. Health check fails → ASG marks instance `Unhealthy`.
2. ASG launches a replacement.
3. Replacement passes health check → registers with ELB / target group.
4. ASG terminates the unhealthy instance.

The total time is 3-10 minutes. Do NOT manually terminate the
unhealthy instance — the ASG handles it after the replacement is
healthy.

## Procedure: SSM Session Manager access

**When:** Instance is `running` but SSH is unavailable. SSM Session
Manager provides shell access via the SSM agent without SSH keys or
ingress rules.

```bash
# 1. Verify SSM agent is online
aws ssm describe-instance-information \
  --filters Key=InstanceIds,Values=<id> \
  --query 'InstanceInformationList[0].{Ping:PingStatus,
    Agent:AgentVersion,Platform:PlatformName}'

# 2. If PingStatus: Online, start a session
aws ssm start-session \
  --target <id>

# 3. For port forwarding (e.g., database access):
aws ssm start-session \
  --target <id> \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["5432"],"localPortNumber":["5432"]}'
```

**If SSM PingStatus: ConnectionLost:**
- The SSM agent is hung or the OS network stack is down.
- Try reboot: `aws ec2 reboot-instances --instance-ids <id>`.
- If reboot does not restore SSM, use EBS detach/attach.

**If SSM PingStatus: (empty — not registered):**
- The instance lacks an IAM role with `AmazonSSMManagedInstanceCore`.
- Attach the role, then wait 5-10 minutes for the agent to register.

## Procedure: EC2 Serial Console access

**When:** SSH, SSM, and the network are all down. The serial console
provides tty access via the serial port, independent of the network.

```bash
# 1. Enable at the account level (one-time)
aws ec2 enable-serial-console-access

# 2. Verify access is enabled
aws ec2 get-serial-console-access-status

# 3. Start a serial console session (via the browser-based console)
#    https://console.aws.amazon.com/ec2/v2/home#SerialConsole
#    Or via the SSH-based push:
ssh -i <key> <instance-id>.serial-console.ec2-instance-connect.<region>.aws
```

The serial console shows the boot messages and provides a login
prompt (if the OS is configured for serial login). Use for kernel
panic diagnosis, GRUB bootloader issues, and filesystem corruption
that prevents normal boot.

## Diagnostic command quick-reference

| Goal | Command |
|---|---|
| Instance status | `aws ec2 describe-instance-status --instance-ids <id> --include-all-instances` |
| Instance details | `aws ec2 describe-instances --instance-ids <id>` |
| Console output | `aws ec2 get-console-output --instance-id <id> --latest` |
| EBS volumes | `aws ec2 describe-volumes --filters Name=attachment.instance-id,Values=<id>` |
| ASG membership | `aws autoscaling describe-auto-scaling-instances --instance-ids <id>` |
| SSM status | `aws ssm describe-instance-information --filters Key=InstanceIds,Values=<id>` |
| Recovery alarm | `aws cloudwatch describe-alarms-for-metric --namespace AWS/EC2 --metric-name StatusCheckFailed_System --dimensions Name=InstanceId,Value=<id>` |
| Scheduled events | `aws ec2 describe-instance-status --instance-ids <id> --query 'InstanceStatuses[0].Events'` |
| Stop instance | `aws ec2 stop-instances --instance-ids <id>` |
| Start instance | `aws ec2 start-instances --instance-ids <id>` |
| Reboot instance | `aws ec2 reboot-instances --instance-ids <id>` |
| Create AMI | `aws ec2 create-image --instance-id <id> --name <name> [--no-reboot]` |
| Detach volume | `aws ec2 detach-volume --volume-id <vol> --instance-id <id> [--force]` |
| Attach volume | `aws ec2 attach-volume --volume-id <vol> --instance-id <id> --device <dev>` |
| SSM session | `aws ssm start-session --target <id>` |
| Suspend ASG HealthCheck | `aws autoscaling suspend-processes --auto-scaling-group-name <asg> --scaling-processes HealthCheck` |
| Set recovery alarm | `aws cloudwatch put-metric-alarm --alarm-name <name> --metric-name StatusCheckFailed_System ... --alarm-actions arn:aws:automate:<region>:ec2:recover` |
