# EC2 Instance Recovery - Advanced Patterns

Expert behaviors, defense-in-depth safety deep dive, and recent
features - moved verbatim from SKILL.md.

### Step 0: Expert knowledge — non-obvious EC2 recovery behaviors

- **Stop/start vs. reboot is the most important decision.** Stop/start
  RELOCATES the instance to a new physical host (clears hardware
  issues, loses instance-store data, releases dedicated host and
  Capacity Reservation binding). Reboot STAYS on the same host
  (preserves everything, but does not clear host-level hardware
  issues). For `SystemStatus: impaired`, stop/start is the fix; for
  `InstanceStatus: impaired`, reboot or SSM access is the fix.

- **The CloudWatch EC2 recover action is an API-driven same-host
  reboot.** Triggered by `StatusCheckFailed_System > 0 for N
  datapoints`. It only helps for recoverable transient hardware
  issues. For persistent issues, AWS schedules a `system-reboot` or
  `instance-stop` event — recover masks the symptom.

- **ASG health check replacement is usually preferred over manual
  recovery.** The ASG's built-in recovery (launch replacement, drain
  old, terminate) is more reliable than manual stop/start. Manually
  recovering an ASG instance risks termination during recovery.
  Suspend `HealthCheck` if manual recovery is required.

- **EBS detach/attach is the safest data-salvage path.** If an
  instance is unreachable but EBS volumes are healthy, detach the
  root volume, attach to a rescue instance in the same AZ, fix the
  issue, detach, re-attach to the original. Preserves all data.

- **AMI creation is non-blocking.** `create-image --no-reboot`
  captures WITHOUT a clean shutdown (best-effort consistency).
  `create-image` (default) does a clean shutdown first. For forensic
  snapshots of a hung instance, use `--no-reboot`.

- **EC2 Serial Console (2024+) provides OS-level access without
  network.** If SSH, SSM, and the network are all down, the EC2
  Serial Console provides a tty to the instance's serial port. This
  requires explicit enablement per instance (`--enable-api-serial-
  console` at the account level + per-instance).

- **Capacity Reservation binding is volatile on stop.** When an
  instance with `CapacityReservationSpecification.TargetCapacity=
  ReservationId` stops, the binding is released. On start, the
  instance launches only if the reservation still has capacity. To
  preserve: re-specify the reservation at start, or use an open
  reservation in the same AZ.

- **Instance-store (ephemeral) volumes are NEVER recoverable after
  stop.** The data lives on the physical host. Stop releases the
  host. Start lands elsewhere. EBS-backed volumes (including EBS
  snapshots) are independent of the host.

- **Placement group recovery is constrained.** A `cluster` placement
  group instance stopped may not be able to restart if the group
  lacks free capacity (the cluster relies on low-latency interconnect
  between specific hosts). Prefer reboot (same host) for placement-
  group members.

- **`StatusCheckFailed_System` and `StatusCheckFailed_Instance` are
  separate CloudWatch metrics.** A recovery alarm on
  `StatusCheckFailed_System` triggers the EC2 recover action (same-
  host reboot). A recovery alarm on `StatusCheckFailed_Instance` does
  nothing useful — recover only addresses hardware. For instance-
  status issues, use a Lambda-backed custom alarm that triggers SSM
  or reboot.

- **EC2 automatic recovery (2024-2025 GA) is AWS-managed.** AWS can
  now automatically recover an instance on detected hardware failure
  WITHOUT a customer-configured CloudWatch alarm. This is enabled by
  default for most instance types. The instance reboots on the same
  host; EBS and instance-store data are preserved. If automatic
  recovery does not fire, the manual CloudWatch alarm + recover
  action is the fallback.

- **`get-console-output` returns the LAST boot only.** Each
  `stop/start` or `reboot` clears the prior console log. For
  historical diagnosis, capture the output BEFORE rebooting.

## Pre-flight safety deep dive (defense-in-depth)

- **Capture pre-state for rollback.** Before any recovery:
  `aws ec2 describe-instances --instance-ids <id> --output json >
  /tmp/<id>-pre-$(date +%s).json` AND `aws ec2 describe-volumes
  --filters Name=attachment.instance-id,Values=<id> --output json >
  /tmp/<id>-volumes-$(date +%s).json` AND `aws ec2 get-console-output
  --instance-id <id> --latest > /tmp/<id>-console-$(date +%s).txt`.

- **Forensic AMI first.** If there is ANY chance the recovery could
  fail or the instance could be terminated, create an AMI first.
  The AMI is the point-in-time rollback.

- **EBS volume inventory.** Capture all volume IDs and attachment
  state. For detach/attach, verify the device name is free on the
  target instance.

- **ASG process suspension.** For manual recovery of ASG instances:
  `aws autoscaling suspend-processes --auto-scaling-group-name <asg>
  --scaling-processes HealthCheck AlarmNotification`. Resume after
  recovery completes.

- **Capacity Reservation re-targeting.** Capture
  `CapacityReservationId` before stop. On start:
  `aws ec2 modify-instance-capacity-reservation-attributes
  --instance-id <id> --capacity-reservation-specification
  'CapacityReservationTarget={CapacityReservationId=<id>}'`.

- **Placement group capacity check.** For cluster placement group
  instances, verify free capacity before stop/start. Prefer reboot
  if capacity is uncertain.

## Recent AWS features (2024-2026)

- **EC2 automatic recovery (2024-2025 GA):** AWS automatically
  recovers instances on detected hardware failure without a customer-
  configured alarm. Same-host reboot, preserves EBS and instance-
  store. Manual CloudWatch recover is the fallback.

- **EC2 Serial Console (2024 GA):** OS-level tty access via the
  serial port, independent of SSH/SSM/network. Requires account-
  level enablement and per-instance opt-in. Use when SSH and SSM
  are both down.

- **Capacity Reservation preservation on stop/start (2024-2025):**
  New APIs allow preserving the binding through stop/start when the
  reservation has capacity. Use
  `modify-instance-capacity-reservation-attributes` to re-bind.

- **ASG Capacity Rebalance (2024-2025):** Proactively replaces
  instances at risk of interruption (Spot) or hardware degradation
  (on-demand). Configure via `--capacity-rebalance`.

- **Application Recovery Controller (2024-2026):** Zonal shift
  (evacuate an AZ) and routing control (kill switch) for coordinated
  regional failover beyond single-instance recovery.

- **SSM Session Manager port forwarding (2024):** SSH-less access to
  databases and internal services via the impaired instance's SSM
  agent. Useful for live troubleshooting without SSH keys.

- **EBS Fast Snapshot Restore (2024-2025):** Eliminates first-read
  I/O latency for recovery launches from a snapshot. Enable on the
  snapshot before launching the recovery instance.

- **EC2 Operating System Log (2025):** The console captures pre-
  reboot OS-level diagnostic logs, reducing reliance on
  `get-console-output` for post-recovery forensics.
