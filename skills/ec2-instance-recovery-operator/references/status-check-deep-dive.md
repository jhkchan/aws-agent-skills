# EC2 Status Checks — Deep Dive Reference

Load this reference when classifying an impairment as System vs
Instance status, and when choosing between stop/start, reboot,
recover, and ASG replacement.

## The two status checks

| Check | What it monitors | Frequency | Failure = |
|---|---|---|---|
| **System status check** (`StatusCheckFailed_System`) | AWS hardware: network reachability, power, host software | Every 1 minute | Host/hardware impairment; AWS-managed |
| **Instance status check** (`StatusCheckFailed_Instance`) | Guest OS: filesystem, kernel, system services, network config | Every 1 minute | OS-level impairment; customer-managed |

A `StatusCheckFailed` (aggregate) metric fires if EITHER check fails.
The aggregate is useful for alerting; the per-check metrics are
useful for diagnosis.

## CloudWatch metrics

| Metric | Meaning | Use |
|---|---|---|
| `StatusCheckFailed_System` | 1 if system check failed this minute | Recovery alarm trigger |
| `StatusCheckFailed_Instance` | 1 if instance check failed this minute | Diagnostic; do NOT use recover action |
| `StatusCheckFailed` | 1 if either check failed | Alerting; not for recovery action selection |
| `StatusCheckFailed_Aggregate` | Per-instance aggregate | Fleet-wide dashboards |

## EC2 recover action — what it does and does not do

**Does:**
- Reboot the instance ON THE SAME HOST.
- Preserve EBS attachments and instance-store data.
- Trigger on `StatusCheckFailed_System > threshold` via CloudWatch
  alarm action `arn:aws:automate:<region>:ec2:recover`.
- Complete in 1-5 minutes from alarm breach.

**Does NOT:**
- Relocate the instance to a new host (use stop/start for that).
- Fix OS-level issues (`InstanceStatus: impaired`).
- Work on `terminated` or `stopped` instances.
- Work on all previous-gen instance types (verify via
  `describe-instance-types`).

## EC2 automatic recovery (2024-2025 GA)

AWS now automatically recovers instances on detected hardware failure
WITHOUT a customer-configured alarm. This is enabled by default for
most current-gen instance types.

- The instance reboots on the same host.
- EBS and instance-store data are preserved.
- If automatic recovery does not fire (or fails), the manual
  CloudWatch recover alarm is the fallback.
- To verify if an instance was auto-recovered: check CloudTrail for
  `RecoverInstance` events, or `describe-instances` for
  `StateTransitionReason: User initiated (date)`.

## Stop/start — what changes

| Attribute | Stop/start |
|---|---|
| Physical host | **Changes** (new host on start) |
| Public IP | **Changes** (new public IP unless Elastic IP) |
| Private IP | Preserved |
| Elastic IP | Preserved (stays associated) |
| EBS volumes | Preserved (reattached automatically) |
| Instance-store volumes | **LOST** (data gone) |
| RAM contents | **LOST** |
| Capacity Reservation binding | **Released** (must re-bind on start) |
| Placement group (cluster) | May fail to restart (capacity) |
| Dedicated host | **Released** (must verify availability) |
| ENI | Preserved |
| Security groups | Preserved |
| User-data | Preserved (re-executed on start if configured) |

## Reboot — what changes

| Attribute | Reboot |
|---|---|
| Physical host | **Same** (no change) |
| Public IP | Preserved |
| Private IP | Preserved |
| Elastic IP | Preserved |
| EBS volumes | Preserved |
| Instance-store volumes | Preserved (data intact) |
| RAM contents | **LOST** (warm reboot) |
| Capacity Reservation | Preserved |
| Placement group | Preserved |

## Choosing the operation

```
StatusCheckFailed_System?
├── Yes → Stop/start (relocate) OR CloudWatch recover (same-host)
│         (If pending scheduled event, wait for AWS)
└── No
    └── StatusCheckFailed_Instance?
        ├── Yes → Reboot (same host) OR SSM session (live)
        │         (If OS hung and SSH/SSM down: EBS detach/attach)
        └── No → Not a status-check issue; check application health

ASG member?
├── Yes → Prefer ASG-managed replacement
│         (Suspend HealthCheck only if manual recovery required)
└── No → Manual recovery is safe

RootDeviceType?
├── ebs → Stop/start is safe (data preserved)
└── instance-store → BLOCK stop/start (data loss)
```

## Capacity Reservation handling during recovery

```bash
# Before stop: capture the reservation ID
aws ec2 describe-instances --instance-ids <id> \
  --query 'Reservations[0].Instances[0].CapacityReservationSpecification'

# After start: re-bind if the binding was released
aws ec2 modify-instance-capacity-reservation-attributes \
  --instance-id <id> \
  --capacity-reservation-specification \
    'CapacityReservationTarget={CapacityReservationId=<cr-id>}'
```

If the reservation no longer has capacity at restart, the instance
launches as an on-demand instance in the open pool. Set up a
CloudWatch alarm on `AvailableCapacity` to catch this.

## Placement group recovery

For `cluster` placement groups, stop/start is risky because:
- The cluster group relies on low-latency interconnect between specific
  hosts.
- Restarting requires a free slot in the same cluster group.
- If the cluster is full, the restart fails with `InsufficientCapacity`.

**Recommended approach for cluster placement group members:**
1. Try reboot first (same host, no capacity risk).
2. If reboot does not resolve the impairment, check cluster capacity:
   `aws ec2 describe-placement-groups --group-names <pg>`.
3. If capacity is available, stop/start.
4. If capacity is NOT available, open an AWS Support case to relocate
   the host.

## Scheduled events reference

| Event code | Meaning | Action |
|---|---|---|
| `system-reboot` | AWS will reboot the host | Wait; do NOT manually reboot |
| `instance-reboot` | AWS requests an instance reboot | Reboot before the deadline |
| `instance-stop` | AWS will stop the instance | Stop/start before the window to relocate |
| `instance-retirement` | Host will be retired | Stop/start before the retirement date |
| `maintenance` | Network maintenance | Plan around the window |

Check for scheduled events:

```bash
aws ec2 describe-instance-status --instance-ids <id> \
  --query 'InstanceStatuses[0].Events[*].{Code:Code,
    Description:Description,NotBefore:NotBefore,NotAfter:NotAfter}'
```

Always respect scheduled events. Manual recovery before a scheduled
`system-reboot` prevents AWS from applying the hardware fix.
