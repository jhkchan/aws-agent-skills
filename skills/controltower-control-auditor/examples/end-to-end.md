# End-to-end usage scenario: controltower-control-auditor

A walkthrough showing the skill auditing a Control Tower OU that has both
a drifted preventive control (DRIFT — SCP modified) and a missing execution
role in one account (CONFIG_GAP), demonstrating severity aggregation, the
silent-enforcement-break concept, and the disable/re-enable remediation.

## Input (user prompt)

> Review our Control Tower posture on the Workloads OU before the
> quarterly compliance review. Here is the audit data.

```
Audit target OU: arn:aws:organizations::111111111111:ou/o-abcd/ou-workloads

Landing zone version: 3.3
Landing zone state: ACTIVE
Landing zone drift status: NOT_DETECTED

Enabled controls (list-enabled-controls):
  1. arn:aws:controltower:us-east-1::control/AWS-GR_RESTRICTED_COMMON_PORTS
     Type: PREVENTIVE | Category: MANDATORY | Status: SUCCEEDED
  2. arn:aws:controltower:us-east-1::control/AWS-GR_DISABLE_ROOT_ACCESS_KEYS_NO_HSM
     Type: PREVENTIVE | Category: MANDATORY | Status: SUCCEEDED
  3. arn:aws:controltower:us-east-1::control/AWS-GR_ROOT_MFA_ENABLED
     Type: DETECTIVE | Category: MANDATORY | Status: SUCCEEDED

SCP verification:
  AWSControlTowerGuardrailRestrictedCommonPorts:
    Expected: Deny ec2:AuthorizeSecurityGroupIngress on ports 0, 23, 3389, 22, ...
    Actual content: MODIFIED — Deny on port 22 (SSH) was REMOVED
    Drift type: SCP_CONTENT_MISMATCH
  AWSControlTowerGuardrailDisableRootAccessKeys: Content matches baseline
  AWSControlTowerGuardrailRootMfaEnabled: Content matches baseline

Config recorder status (per account):
  Account 111111111112: ENABLED, recording: true
  Account 111111111113: ENABLED, recording: true
  Account 111111111115: DISABLED, recording: false

AWSControlTowerExecutionRole (per account):
  Account 111111111112: Present, trust policy correct
  Account 111111111113: Present, trust policy correct
  Account 111111111115: MISSING — role was deleted

Account Factory baseline stacks (AWSControlTowerBP): All deployed, no drift
```

## Skill output

```text
LANDING_ZONE: production-landing-zone
OU: arn:aws:organizations::111111111111:ou/o-abcd/ou-workloads
VERDICT: DRIFT
REASON: Preventive control AWS-GR_RESTRICTED_COMMON_PORTS shows SUCCEEDED
but the backing SCP was modified outside Control Tower — the Deny on port 22
(SSH) was removed, allowing inbound SSH despite the guardrail (Step 2).
Account 111111111115 also has Config recorder disabled and the execution
role missing.
FINDINGS:
  - [DRIFT] SCP "AWSControlTowerGuardrailRestrictedCommonPorts" content
    mismatch: Deny on port 22 removed — enforcement broken while control
    shows SUCCEEDED (Step 2)
  - [CONFIG_GAP] Config recorder disabled in account 111111111115 —
    detective controls silently cannot evaluate (Step 4)
  - [CONFIG_GAP] AWSControlTowerExecutionRole missing in account
    111111111115 — account is stranded, Control Tower cannot manage it
    (Step 5)
  - [OK] Mandatory control AWS-GR_DISABLE_ROOT_ACCESS_KEYS_NO_HSM: SUCCEEDED,
    SCP matches baseline
  - [OK] Account Factory baselines: all StackSets deployed, no drift
REMEDIATION:
  1. DRIFT — Re-deploy the canonical SCP by disabling and re-enabling the
     control:
     aws controltower disable-control \
       --controlIdentifier arn:aws:controltower:us-east-1::control/AWS-GR_RESTRICTED_COMMON_PORTS \
       --targetIdentifier arn:aws:organizations::111111111111:ou/o-abcd/ou-workloads
     aws controltower enable-control \
       --controlIdentifier arn:aws:controltower:us-east-1::control/AWS-GR_RESTRICTED_COMMON_PORTS \
       --targetIdentifier arn:aws:organizations::111111111111:ou/o-abcd/ou-workloads
     NOTE: During the disable window, the SCP is not enforcing. Schedule
     during a maintenance window.
  2. DRIFT — Audit CloudTrail for organizations:UpdatePolicy events on the
     SCP to identify who modified it.
  3. CONFIG_GAP — Re-enable Config recorder in account 111111111115:
     aws configservice start-configuration-recorder \
       --configuration-recorder-name default --profile acct-111115
  4. CONFIG_GAP — Recreate AWSControlTowerExecutionRole in account
     111111111115 by updating the StackSet instance:
     aws cloudformation update-stack-instances \
       --stack-set-name AWSControlTowerBP \
       --accounts 111111111115 --regions us-east-1
```

## What the skill caught that a generic assistant misses

1. **The SUCCEEDED status is not proof of enforcement.** A generic
   assistant sees "SUCCEEDED" and moves on. The skill cross-references the
   SCP content against the baseline — the guardrail looks enabled but the
   Deny on port 22 was silently removed. This is the core D1 delta: Control
   Tower status reflects the last operation, not the current enforcement
   state.

2. **Config recorder disabled = detective controls are dead.** A generic
   assistant notes the recorder is off but does not connect it to detective
   control health. The skill explains that AWS-GR_ROOT_MFA_ENABLED (a
   detective control) silently stops evaluating in account 111111111115 —
   no Security Hub findings means "not checked," not "compliant."

3. **Execution role missing = account stranded.** A generic assistant
   recommends "recreate the role." The skill explains WHY this matters:
   Control Tower assumes this role to deploy StackSets, enable new controls,
   and update baselines. Without it, account 111111111115 cannot receive
   any Control Tower updates — it is stranded.

4. **Severity aggregation with per-finding breakdown.** The verdict is
   DRIFT (worst finding), but the FINDINGS list shows the individual
   severities. This lets the operator triage each finding independently and
   understand that the SCP drift is higher priority than the Config/role
   gaps.

## Slash-command invocation

```
/aws:audit-controltower-controls
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit our Control Tower guardrails before the compliance review"
```

The orchestrator emits
`[Phase: Audit | Skills routed: controltower-control-auditor]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit control tower landing zone"
# [Phase: Audit | Skills routed: controltower-control-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the findings, validate the posture:

```bash
# Verify the SCP was re-deployed correctly
aws organizations list-policies --filter SERVICE_CONTROL_POLICY \
  --profile default --output json | jq '.Policies[] | select(.Name | contains("RestrictedCommonPorts"))'

# Confirm Config recorder is back on
aws configservice describe-configuration-recorder-status \
  --profile acct-111115 --output json

# Verify the execution role exists
aws iam get-role --role-name AWSControlTowerExecutionRole \
  --profile acct-111115 --output json | jq '.Role.AssumeRolePolicyDocument'

# Check for any stuck control operations
aws controltower list-control-operations \
  --filter targetIdentifier=arn:aws:organizations::111111111111:ou/o-abcd/ou-workloads \
  --profile default --output table
```

Then monitor CloudTrail for `organizations:UpdatePolicy` and
`config:StopConfigurationRecorder` events for 1-2 weeks to detect recurrence.
