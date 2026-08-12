# End-to-end usage scenario: inspector2-automation-automator

A walkthrough showing the skill designing two Inspector automation
workflows for the same account: an AUTOMATION_DEPLOYED Critical
EC2 patching workflow with snapshot gate, and a REVIEW_REQUIRED
multi-account ECR finding workflow blocked on delegated admin
configuration. Demonstrates the severity matrix and the
delegated-admin prerequisite.

## Input (user prompt)

> Set up Inspector automation for our production workloads. We have
> a Critical CVE on an EC2 instance we want auto-patched, and a
> separate High CVE on ECR images across 15 member accounts.

```
Design reference: prod-inspector-rollout
Account: 111111111111
Region: us-east-1

Finding 1: ec2-critical-cve
  CVE: CVE-2026-1234 on openssl (CVSS 9.8)
  Severity: CRITICAL
  Resource: AWS_EC2_INSTANCE i-0abc123def456 (Amazon Linux 2,
    SSM agent healthy, Patch Group tag = "critical-patch-group")
  Inspector coverage: enabled (EC2/ECR/Lambda)
  SSM service role ARN:
    arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole
  Pre-prod validation: completed (Cycle 1 Scan + Cycle 2 Install).

Finding 2: ecr-multi-account-cve
  CVE: CVE-2026-2211 on amazon-linux base (CVSS 8.2)
  Severity: HIGH
  Resources: AWS_ECR_CONTAINER_IMAGE across 15 member accounts
  Org ID: o-abc123def (management account 111111111111)
  Delegated admin: NOT configured for inspector2.amazonaws.com
  Inspector enabled per-member, but no aggregated view.
```

## Skill output

```text
FINDING: prod-inspector-rollout / ec2-critical-cve
SEVERITY: CRITICAL
DETECTION:
  - Source: aws.inspector2 via EventBridge (rule inspector-critical-auto-patch)
  - Resource: AWS_EC2_INSTANCE i-0abc123def456
  - CVE: CVE-2026-1234 on openssl (CVSS 9.8)
RESPONSE:
  - Action: SSM patch via AWS-RunPatchBaseline (snapshot + install)
  - SLA: 24 hours (4-hour automation window)
  - Automation: EventBridge -> SSM Automation (custom runbook with snapshot gate)
SSM_RUNBOOK: Custom-InspectorCriticalPatch
  Steps:
    1. aws:createImage (pre-patch snapshot, NoReboot=true)
    2. aws:runCommand AWS-RunPatchBaseline (Operation=Install, RebootOption=RebootIfNeeded)
    3. aws:waitForAwsResourceProperty (verify Installed state)
VERIFICATION:
  - Rescan: aws inspector2 list-findings --filter-criteria findingArn=<arn>,status=OPEN
  - Security Hub: aws securityhub get-findings --filter-criteria GeneratorId=aws-inspector
MULTI_ACCOUNT: single (111111111111)
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws events put-rule --name inspector-critical-auto-patch --event-pattern '{"source":["aws.inspector2"],"detail-type":["Inspector Finding"],"detail":{"severity":["CRITICAL"],"status":["OPEN"],"resources":{"type":["AWS_EC2_INSTANCE"]}}}'
  aws events put-targets --rule inspector-critical-auto-patch --targets '[{"Id":"ssm-automation","Arn":"arn:aws:ssm:us-east-1:111111111111:automation-definition/Custom-InspectorCriticalPatch","RoleArn":"arn:aws:iam::111111111111:role/service-role/AmazonInspectorEventBridgeInvokeSSM"}]'

FINDING: prod-inspector-rollout / ecr-multi-account-cve
SEVERITY: HIGH
DETECTION:
  - Source: aws.inspector2 (per-member-account; no aggregated view)
  - Resources: AWS_ECR_CONTAINER_IMAGE across 15 member accounts
  - CVE: CVE-2026-2211 on amazon-linux base (CVSS 8.2)
RESPONSE:
  - Action: notify + CodeBuild rebuild trigger
  - SLA: 7 days
  - Automation: BLOCKED (delegated admin not configured)
SSM_RUNBOOK: n/a (container finding -> CodeBuild rebuild)
VERIFICATION: blocked
MULTI_ACCOUNT: REVIEW_REQUIRED — delegated admin not configured
VERDICT: REVIEW_REQUIRED
GAP: Inspector delegated admin not configured for org o-abc123def. Without delegated admin, findings must be queried per-member-account individually; aggregated EventBridge rules cannot be built. Configure via aws organizations register-delegated-administrator --account-id 111111111111 --service-principal inspector2.amazonaws.com. Then enable Inspector for all member accounts from the delegated admin.
TEMPLATE: (blocked until delegated admin configured)
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED for EC2
Critical + REVIEW_REQUIRED for ECR multi-account.** Roll out the
EC2 patching workflow immediately; the multi-account ECR workflow
is blocked until delegated admin is configured.

## What the skill caught that a generic assistant misses

1. **The snapshot gate.** A generic assistant runs
   `AWS-RunPatchBaseline` directly. The skill inserts a
   `aws:createImage` step before patching — without a pre-patch
   snapshot, a bad patch is unrecoverable without rebuild.

2. **The SSM patch baseline approval delay.** A generic assistant
   assumes patches apply immediately. The skill flags
   `ApproveAfterDays` — if the baseline is set to 7 days, freshly
   announced CVEs will NOT be patched even when the runbook fires.

3. **The ECR push-time scan gap.** A generic assistant thinks ECR
   scans are continuous. The skill surfaces that scans are
   push-time; existing images need scheduled rescans to detect
   newly-published CVEs.

4. **The delegated admin prerequisite.** A generic assistant tries
   to wire fleet-wide EventBridge rules without delegated admin.
   The skill refuses — REVIEW_REQUIRED — because per-member finding
   queries cannot be aggregated without delegated admin.

5. **The Lambda code scan static-only caveat.** A generic assistant
   treats Lambda code scans as runtime protection. The skill notes
   they are static analysis at deploy time — pair with GuardDuty
   for runtime coverage.

6. **The Inspector -> Security Hub one-way sync.** A generic
   assistant suggests closing findings in Security Hub. The skill
   notes the integration is one-way: closing in Inspector closes
   in SecHub (within 5 min), but closing in SecHub does NOT close
   in Inspector.

## Slash-command invocation

```
/aws:automate-inspector2-remediation
```

Or via the orchestrator:

```
/aws:pipeline
You: "automate Inspector finding remediation"
```

## CLI routing

```bash
node cli/bin/cli.js route "automate Inspector finding"
# [Phase: Automate | Skills routed: inspector2-automation-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# Discover Inspector coverage
aws inspector2 list-coverage \
  --filter-criteria accountId=111111111111 \
  --region us-east-1 --profile default

# List recent Critical findings
aws inspector2 list-findings \
  --filter-criteria 'severity=[{"comparison":"EQUALS","value":"CRITICAL"}],status=[{"comparison":"EQUALS","value":"OPEN"}]' \
  --region us-east-1 --profile default

# Check delegated admin status
aws inspector2 list-delegated-admin-accounts \
  --region us-east-1 --profile default

# Check existing patch baselines
aws ssm describe-patch-baselines \
  --operating-system AMAZON_LINUX_2 \
  --region us-east-1 --profile default

# Check SSM agent health on target instance
aws ssm describe-instance-information \
  --filters Key=InstanceIds,Values=i-0abc123def456 \
  --query 'InstanceInformationList[0].[PingStatus,AgentVersion]' \
  --region us-east-1 --profile default --output text

# Check Security Hub integration
aws inspector2 batch-get-configuration \
  --region us-east-1 --profile default

# Verify the finding in Security Hub
aws securityhub get-findings \
  --filters 'GeneratorId=[{"Value":"aws-inspector","Comparison":"PREFIX"}],SeverityLabel=[{"Value":"CRITICAL","Comparison":"EQUALS"}]' \
  --region us-east-1 --profile default
```

Then paste the output into the skill for workflow design.

## Complementary controls

Pair this skill with related security skills:

- **`securityhub-remediation-automator`** — for findings sourced
  from Security Hub (CIS, PCI, AWS FSBP controls)
- **`config-rule-remediator`** — for non-CVE compliance drift
- **`guardduty-finding-triage`** — for runtime threat detection
  (complements Inspector's static analysis)

Use the `inspector2-coverage-finding-auditor` skill to verify
Inspector coverage gaps (e.g., member accounts without Inspector
enabled, EC2 instances without SSM agent).
