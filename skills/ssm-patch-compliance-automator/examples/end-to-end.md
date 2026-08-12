# End-to-end usage scenario: ssm-patch-compliance-automator

A walkthrough showing the skill designing patch automation for a mixed
OS fleet: an AUTOMATION_DEPLOYED Amazon Linux 2023 workflow with full
safety gates and a REVIEW_REQUIRED Windows workflow blocked by a
network-egress gap.

## Input (user prompt)

> We need to automate patching for our production fleet. We have 120
> Amazon Linux 2023 instances and 45 Windows Server 2022 instances in
> a private VPC. Patch the Linux fleet weekly on Saturdays. For
> Windows, also weekly but on Sundays. We want compliance reporting
> and critical instances excluded.

```
Design reference: prod-patch-rollout-2026
Account: 111111111111
Region: us-east-1

Linux fleet:
  - 120 Amazon Linux 2023 instances (prod)
  - Tagged: "Patch Group" = "al2023-prod"
  - SSM agent: all Online
  - Baseline desired: Critical/Important immediate, Medium 7 days
  - Schedule: weekly Saturday 02:00 UTC, 4 hours
  - Pre-prod validation: canary completed (3 instances, Compliant)
  - RebootOption: RebootIfNeeded

Windows fleet:
  - 45 Windows Server 2022 instances (prod, private VPC)
  - VPC: no NAT gateway, no WSUS, no VPC endpoints for Windows Update
  - Tagged: "Patch Group" = "win2022-prod"
  - SSM agent: all Online
  - Baseline desired: MSRC Critical/Important, 3 days
  - Schedule: weekly Sunday 02:00 UTC, 6 hours

Critical exceptions (Linux fleet):
  - i-0db123prod: database proxy, change-frozen
  - i-0aux456legacy: legacy app, patching breaks JCE
```

## Skill output

```text
PATCH: prod-patch-rollout-2026
FLEET: 120 Amazon Linux 2023 + 45 Windows Server 2022 (prod)
BASELINE:
  - Name: al2023-prod-baseline
  - OS: AMAZON_LINUX_2023
  - Approval rules: Critical/Important ApproveAfterDays 0; Medium ApproveAfterDays 7
  - Baseline ID: pb-0abc123def
PATCH_GROUP:
  - Tag key: Patch Group
  - Tag value: al2023-prod
  - Instance count: 118 (2 exceptions excluded)
MAINTENANCE_WINDOW:
  - Scan schedule: cron(0 6 * * ? *) daily 06:00 UTC
  - Install schedule: cron(0 2 ? * SAT *) weekly Saturday 02:00 UTC
  - Duration: 4 hours
  - Cutoff: 1 hour
  - MaxConcurrency: 10% (12 instances at a time)
  - MaxErrors: 5% (6 errors before window cancels)
COMPLIANCE_MONITORING:
  - Inventory schema: AWS:PatchCompliance (auto-populated by Scan)
  - Config rule: ec2-managedinstance-patch-compliance
  - Dashboard: patch-compliance-overview
SAFETY:
  - Pre-patch snapshot: enabled (aws:createImage before Install)
  - SNS notification: arn:aws:sns:us-east-1:111111111111:patch-notify
  - Approval gate: none (reversible via AMI rollback)
  - Exception list: 2 instances (i-0db123prod, i-0aux456legacy)
    - Tagged: Patch Group=critical-scan-only (Scan daily, no Install)
    - Review dates: i-0db123prod 2026-10-01, i-0aux456legacy 2026-09-15
REBOOT: RebootIfNeeded
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws ssm create-patch-baseline --name "al2023-prod-baseline" --operating-system AMAZON_LINUX_2023 --approval-rules '{"PatchRules":[...]}'
  aws ec2 create-tags --resources <instance-id> --tags "Key=Patch Group,Value=al2023-prod"
  aws ssm register-patch-baseline-for-patch-group --baseline-id pb-0abc123def --patch-group al2023-prod
  aws ssm create-maintenance-window --name "al2023-prod-install" --schedule "cron(0 2 ? * SAT *)" --duration 4 --cutoff 1
  aws ssm register-task-with-maintenance-window --window-id <id> --task-arn "AWS-RunPatchBaseline" --task-invocation-parameters '{"RunCommand":{"Parameters":{"Operation":["Install"],"RebootOption":["RebootIfNeeded"]}}}' --max-concurrency "10%" --max-errors "5%"

---

PATCH: prod-patch-rollout-2026
FLEET: 45 Windows Server 2022 (prod, private VPC)
BASELINE:
  - Name: win2022-prod-baseline
  - OS: WINDOWS
  - Approval rules: MSRC Critical/Important ApproveAfterDays 3
  - Baseline ID: pb-0xyz789ghi
PATCH_GROUP:
  - Tag key: Patch Group
  - Tag value: win2022-prod
  - Instance count: 45
MAINTENANCE_WINDOW:
  - Scan schedule: TBD (blocked)
  - Install schedule: cron(0 2 ? * SUN *) weekly Sunday 02:00 UTC (blocked)
  - Duration: 6 hours
  - MaxConcurrency: 5%
  - MaxErrors: 3%
COMPLIANCE_MONITORING: TBD
SAFETY: TBD
REBOOT: TBD
VERDICT: REVIEW_REQUIRED
GAP: Windows instances are in a private VPC without NAT gateway, WSUS server, or VPC endpoints for Windows Update. Patches will fail to download. Resolution options: (1) add a NAT gateway to the private subnet; (2) deploy a WSUS server in the VPC; (3) create VPC endpoints for Windows Update endpoints (limited support, requires S3 and other endpoints). Additionally, no pre-patch snapshot workflow, SNS notification, or compliance dashboard is configured for the Windows fleet.
TEMPLATE: (blocked until network egress is resolved)
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED for Linux +
REVIEW_REQUIRED for Windows.** Roll out the Linux workflow immediately;
the Windows workflow requires network-egress resolution before any
patching can proceed.

## What the skill caught that a generic assistant misses

1. **The tag-key case sensitivity.** A generic assistant uses
   `PatchGroup` or `patch-group`. The skill verifies the exact key is
   `Patch Group` (capital P, capital G, one space) and flags any drift
   that would make instances invisible to Patch Manager.

2. **The network-egress gap for Windows.** A generic assistant creates
   the Windows baseline and maintenance window, assuming patches will
   download. The skill catches that Windows instances in a private VPC
   without NAT or WSUS cannot reach Windows Update — the Install task
   will fail silently (no patches downloaded, zero compliance change).

3. **The per-instance concurrency sizing.** A generic assistant sets
   `MaxConcurrency: 1` or the full fleet count. The skill sizes
   concurrency to 10% (12 instances at a time for a 120-instance fleet),
   with a 5% error budget — balancing speed against blast radius.

4. **The NoReboot trap.** A generic assistant may recommend `NoReboot`
   to avoid disruptions. The skill warns that `NoReboot` creates a
   false-positive compliance state: SSM reports Compliant but the
   running kernel is unpatched until a separate reboot occurs.

5. **The StackSet association gap.** A generic assistant deploys a
   StackSet for patch baselines and assumes the baseline is wired.
   The skill notes that StackSets deploy the baseline resource only;
   patch-group associations require separate per-account automation
   (CloudFormation `AWS::SSM::Association` or Lambda custom resource).

6. **The critical-exception lifecycle.** A generic assistant simply
   excludes critical instances. The skill creates a scan-only patch
   group for exceptions with quarterly review dates and named approvers,
   preventing permanent security holes from expired exceptions.

## Slash-command invocation

```
/aws:automate-patch-compliance
```

Or via the orchestrator:

```
/aws:pipeline
You: "automate patch compliance for AL2023 fleet"
```

## CLI routing

```bash
node cli/bin/cli.js route "automate patch compliance"
# [Phase: Automate | Skills routed: ssm-patch-compliance-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# Check SSM agent health across the fleet
aws ssm describe-instance-information \
  --query 'InstanceInformationList[?PingStatus==`Online`].{Id:InstanceId,OS:PlatformName,Ver:PlatformVersion}' \
  --output table --region us-east-1 --profile default

# Verify Patch Group tags (exact key with space)
aws ec2 describe-tags \
  --filters "Name=key,Values=Patch Group" \
  --query 'Tags[].{Resource:ResourceId,Group:Value}' \
  --output table --region us-east-1 --profile default

# Check current patch compliance
aws ssm describe-instance-patch-states \
  --instance-ids $(aws ssm describe-instance-information \
    --query 'InstanceInformationList[?PingStatus==`Online`].InstanceId' \
    --output text --region us-east-1 --profile default | tr '\t' ' ') \
  --region us-east-1 --profile default

# Verify existing baselines
aws ssm describe-patch-baselines \
  --query 'BaselineIdentities[?OperatingSystem==`AMAZON_LINUX_2023`].{Name:BaselineName,Id:BaselineId,Default:IsDefaultBaseline}' \
  --output table --region us-east-1 --profile default

# Check maintenance windows
aws ssm describe-maintenance-windows \
  --query 'WindowIdentities[].{Name:Name,Schedule:Schedule,Duration:Duration,Cutoff:Cutoff}' \
  --output table --region us-east-1 --profile default
```

Then paste the output into the skill for workflow design.
