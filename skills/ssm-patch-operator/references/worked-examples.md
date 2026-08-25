# Worked Examples — ssm-patch-operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Worked example — Scan-only association missing patches

```text
OPERATION: install
VERDICT: BLOCKED
TARGET: i-0fedcba9876543210
PRE_CHECKS:
  - [PASS] PingStatus Active
  - [PASS] IAM role includes AmazonSSMManagedInstanceCore
  - [PASS] EC2 State running
  - [PASS] Free disk 22 GB on /
  - [FAIL] Effective baseline is AWS-AmazonLinux2DefaultPatchBaseline
    (no Patch Group tag, no custom baseline association). Operator intent
    was "apply the prod-linux-critical baseline" — the instance is
    silently on the AWS default. Install would apply the default-baseline
    approved set, NOT the operator's prod-linux-critical rules.
  - [PASS] Maintenance window mw-0bbb has the instance as a target
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
COMPLIANCE_DELTA: (none)
REBOOT: (none)
NOTES:
  - Either tag the instance for the prod-linux-critical baseline:
      aws ec2 create-tags --resources i-0fedcba9876543210 \
        --tags Key="Patch Group",Value=prod-linux-critical
    then re-fetch get-patch-baseline-for-instance to confirm.
  - OR set pb-0aaa1234 as the regional default for AMAZON_LINUX_2:
      aws ssm set-default-patch-baseline \
        --baseline-id pb-0aaa1234 --operating-system AMAZON_LINUX_2
    (replaces AWS-AmazonLinux2DefaultPatchBaseline region-wide — review
    blast radius before applying.)
  - Re-run this skill after remediation; pre-checks will re-evaluate.
```

### Worked example — Maintenance window register-task

```text
OPERATION: register-mw-task
VERDICT: READY
TARGET: mw-0bbb (prod-patch-window, cron 0 02 ? * SAT *)
PRE_CHECKS:
  - [PASS] mw-0bbb exists, enabled, schedule valid (Saturdays 02:00 UTC,
    4 h duration, 1 h cutoff)
  - [PASS] Targets: Key=tag:"Patch Group",Values=prod-linux-critical →
    14 instances match
  - [PASS] Service role arn:aws:iam::111111111111:role/service-role/AmazonSSMAutomationRole
    trusts ssm.amazonaws.com
  - [PASS] Task parameters: Operation=Install, RebootOption=NoReboot
  - [PASS] Task invocation lambda/automation role attached
STEPS:
  1. CONFIRM: About to register-task-with-maintenance-window on mw-0bbb
     in account 111111111111 region us-east-1. This will run
     AWS-RunPatchBaseline Operation=Install on up to 14 instances tagged
     Patch Group=prod-linux-critical every Saturday 02:00 UTC. Rate
     control: max-concurrency 10%, max-errors 0. Proceed? (yes/no)
  2. aws ssm register-task-with-maintenance-window \
       --window-id mw-0bbb \
       --targets "Key=tag:Patch Group,Values=prod-linux-critical" \
       --task-arn "AWS-RunPatchBaseline" \
       --task-type RUN_COMMAND \
       --service-role-arn arn:aws:iam::111111111111:role/service-role/AmazonSSMAutomationRole \
       --task-invocation-parameters '{"RunCommand":{"DocumentVersion":"$DEFAULT","Parameters":{"Operation":["Install"],"RebootOption":["NoReboot"],"SnapshotIds":[""]}}}' \
       --max-concurrency "10%" --max-errors 0 \
       --priority 1 \
       --name "Install-Security-Patches"
  3. aws ssm describe-maintenance-window-tasks --window-id mw-0bbb
POST_VERIFY:
  - (pending next execution)
COMPLIANCE_DELTA: (will be reported after the next Saturday 02:00 UTC run)
REBOOT: deferred (NoReboot; kernel patches activate on next reboot)
NOTES:
  - Verify target membership weekly: instances drift in/out of the Patch
    Group tag.
  - First execution is the next Saturday 02:00 UTC. To run immediately for
    verification: aws ssm start-automation-execution or send a one-off
    send-command to a single instance.
```
