# EC2 Instance Recovery - Worked Examples

Additional worked examples (the primary recover-instance stop/start
example stays in SKILL.md). Same STRICT output contract.

### Worked example — detach-attach-ebs (data salvage, COMPLETED)

```text
OPERATION: detach-attach-ebs
VERDICT: COMPLETED
TARGET: i-0abcdef1234567890 (volume vol-0abc to rescue i-0rescue9999)
PRE_CHECKS:
  - [PASS] Source instance unreachable but not terminated
  - [PASS] EBS volume vol-0abc attached, DeleteOnTermination: false
  - [PASS] Rescue instance i-0rescue9999 in same AZ (us-east-1a)
  - [PASS] Device name /dev/sdf free on rescue instance
STEPS:
  1. (executed) aws ec2 detach-volume --volume-id vol-0abc
     --instance-id i-0abcdef1234567890 --force
  2. (executed) aws ec2 attach-volume --volume-id vol-0abc
     --instance-id i-0rescue9999 --device /dev/sdf
  3. (executed) Operator reverted bad config, unmounted, detached
  4. (executed) aws ec2 attach-volume --volume-id vol-0abc
     --instance-id i-0abcdef1234567890 --device /dev/xvda
POST_VERIFY:
  - [PASS] Volume vol-0abc in-use on i-0abcdef1234567890 at /dev/xvda
  - [PASS] Instance boots; nginx config valid; application responds
NOTES:
  - EBS detach/attach preserved all data on the root volume without
    a stop/start. Safest path when OS is reachable from a rescue
    instance but not from the original.
```

### Worked example — diagnose-impaired (BLOCKED with remediation)

```text
OPERATION: diagnose-impaired
VERDICT: BLOCKED
TARGET: i-0abcdef1234567890 (state: running, system-status: ok,
        instance-status: impaired)
PRE_CHECKS:
  - [PASS] Instance exists, not terminated
  - [PASS] InstanceStatus impaired (OS-level, not hardware)
  - [PASS] SSM PingStatus: ConnectionLost (agent hung)
  - [FAIL] Console output: kernel panic in module xyz-driver
    (OS unresponsive; SSH/SSM unavailable)
STEPS: (none — root cause is kernel panic)
POST_VERIFY: (none)
NOTES:
  - Root cause: kernel panic from xyz-driver. The instance is running
    but the OS is hung — SSH and SSM are both down.
  - Fix options:
    A) EBS detach/attach to rescue, remove the driver, reattach.
    B) stop/start if instance-store data is expendable.
  - Capture console output BEFORE any recovery action:
    aws ec2 get-console-output --instance-id i-0abcdef1234567890
      --latest > /tmp/i-0abcdef-console-$(date +%s).txt
```

