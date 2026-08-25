# Diagnostic & Remediation Commands — SSM Managed Instance Auditor

Pre-flight safety gates and per-verdict remediation runbooks moved from SKILL.md. Load before any remediation CLI.

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`send-command Operation=Install`, `update-association`,
  `delete-association`, `start-session`), the auditor MUST emit:
  `CONFIRM: About to <action> on instance <id> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`. Do NOT execute the
  CLI command until the operator confirms. `AWS-ApplyPatchBaseline`
  with `Operation=Install` reboots Windows instances and may restart
  services on Linux — never auto-trigger.
- **`SendCommand` target blast radius.** Always pass `--instance-ids
  <id>` (single instance) for remediation commands, NEVER
  `--targets Key=InstanceIds,Values=*` or a tag-based target. A
  mis-scoped patch Install can reboot an entire fleet simultaneously.
- **Patch Install pre-flight:** before running `Operation=Install`,
  verify the patch baseline's `ApprovalRules` match the intended
  maintenance window. Custom baselines can auto-approve more than
  expected. Run `aws ssm describe-patch-baseline --baseline-id <id>`
  to confirm.
- **Session start pre-flight:** confirm CloudTrail logs `StartSession`
  data events in the region. Without it, the session is unauditable —
  fix logging BEFORE invoking `start-session` for verification.
- **Association modification:** snapshot
  `aws ssm describe-association --association-id <id> --output json`
  BEFORE `update-association`. SSM keeps association version history
  (up to 99 versions) but explicit rollback is easier with a snapshot.
- **Prefer `RateControl` on SendCommand.** When running fleet-wide
  remediation, set `--max-errors 0` and `--max-concurrency "10%"` —
  halt on first error to avoid cascading bad patches.
## Remediation guidance (moved from SKILL.md)

**Ordering principle:** fix coverage first (no other dimension
matters on an unreachable instance), then compliance, then access
path, then config gaps. Within each dimension, prefer read-only
verification before state-changing operations.

### For UNMANAGED — coverage gap (Rules C-1, C-2, C-3)

1. **C-1 (no IAM profile on EC2):** Attach the modern instance role:
   ```bash
   aws ec2 associate-iam-instance-profile \
     --instance-id i-0abc123def456789a \
     --iam-instance-profile Name=AmazonSSMManagedInstanceCore-Role
   ```
   Confirm the role exists or create it:
   ```bash
   aws iam create-role --role-name AmazonSSMManagedInstanceCore-Role \
     --assume-role-policy-document file://trust-ec2.json
   aws iam attach-role-policy --role-name AmazonSSMManagedInstanceCore-Role \
     --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
   ```
2. **C-2 (stale ping):** Diagnose in order: (a) instance running?
   (`ec2 describe-instances`); (b) SSM Agent service running on host?
   (`ssm send-command AWS-RunShellScript "systemctl status amazon-ssm-agent"`
   if reachable); (c) VPC endpoints present in the instance's VPC? (d)
   security group allows HTTPS/443 outbound to SSM endpoints?
3. **C-3 (hybrid activation role):** Create a new activation with the
   correct role and re-register the instance:
   ```bash
   aws ssm create-activation --iam-role AmazonSSMManagedInstanceCore-Role \
     --registration-limit 1 --expiry-date $(date -u -v+7d +%Y-%m-%d)
   ```
4. After coverage is restored, RE-RUN the audit — patch, session, and
   inventory data need a fresh collection cycle before they are
   trustworthy.

### For NONCOMPLIANT — failed patches or associations (Rules P-1, A-1)

1. **P-1 (missing patches):** Run a one-time Install (with confirmation):
   ```bash
   aws ssm send-command \
     --instance-ids i-0abc123def456789a \
     --document-name "AWS-ApplyPatchBaseline" \
     --parameters "Operation=[Install]" \
     --max-errors 0 --max-concurrency 1
   ```
   For Windows, plan for a reboot (`AWS-RebootEC2Instance` document).
2. **A-1 (failed association):** Diagnose via:
   ```bash
   aws ssm describe-association-execution-targets \
     --association-id <id> --execution-id <execution-id>
   ```
   Common causes: S3 output bucket deleted, IAM role revoked
   `s3:PutObject`, document parameter mismatch. Fix root cause before
   re-running.

### For NO_SESSION_MANAGER — open SSH with no managed access (Rule S-1)

1. Verify Session Manager prerequisites: agent v2.3.12.0+,
   `AmazonSSMManagedInstanceCore` attached.
2. Test Session Manager:
   ```bash
   aws ssm start-session --target i-0abc123def456789a
   ```
3. After verifying, restrict the SSH security group rule to a narrow
   egress CIDR (or remove the rule entirely if Session Manager is the
   sole intended path):
   ```bash
   aws ec2 revoke-security-group-ingress --group-id sg-xxx \
     --protocol tcp --port 22 --cidr 0.0.0.0/0
   aws ec2 authorize-security-group-ingress --group-id sg-xxx \
     --protocol tcp --port 22 --cidr <corporate-egress>/32
   ```
4. Enable session logging (Rule S-3 remediation):
   ```bash
   aws ssm update-session-manager-preferences \
     --s3-bucket-name <audit-bucket> \
     --cloud-watch-log-group <log-group> \
     --kms-key-id <key-id>
   ```

### For CONFIG_GAP — inventory / agent / logging gaps

1. **V-1 (stale agent):** Create the auto-update association:
   ```bash
   aws ssm create-association --name AWS-UpdateSSMAgent \
     --targets Key=InstanceIds,Values=i-0abc123def456789a \
     --schedule-expression "rate(1 day)"
   ```
2. **I-1 (no inventory):** Create the inventory association with a
   schema:
   ```bash
   aws ssm create-association --name AWS-GatherSoftwareInventory \
     --targets Key=InstanceIds,Values=i-0abc123def456789a \
     --schedule-expression "rate(12 hours)" \
     --parameters "applications=[Enabled],networkConfig=[Enabled]"
   ```
3. **S-3 (no session logging):** See NO_SESSION_MANAGER step 4 above.
4. **P-2 (no Patch Group tag):** Tag the instance to map to your
   custom baseline:
   ```bash
   aws ec2 create-tags --resources i-0abc123def456789a \
     --tags "Key=Patch Group,Value=<baseline-group>"
   ```

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit (weekly) — SSM state drifts as instances
   are launched/terminated.
3. Recommend enabling SSM Change Manager / Incident Manager for
   production fleets (defence-in-depth).
