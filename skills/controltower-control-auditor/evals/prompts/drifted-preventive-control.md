# Eval prompt: drifted-preventive-control

Audit the following Control Tower configuration. Emit the standard VERDICT
block (LANDING_ZONE, OU, VERDICT, REASON, FINDINGS, REMEDIATION).

Audit target OU: arn:aws:organizations::111111111111:ou/o-abcd/ou-drifted-preventive-control

Landing zone version: 3.3
Landing zone state: ACTIVE
Landing zone drift status: NOT_DETECTED

Enabled controls (list-enabled-controls):
  1. arn:aws:controltower:us-east-1::control/AWS-GR_RESTRICTED_COMMON_PORTS
     Type: PREVENTIVE | Category: MANDATORY | Status: SUCCEEDED
  2. arn:aws:controltower:us-east-1::control/AWS-GR_ROOT_MFA_ENABLED
     Type: DETECTIVE | Category: MANDATORY | Status: SUCCEEDED

SCP verification (organizations list-policies --filter SERVICE_CONTROL_POLICY):
  AWSControlTowerGuardrailRestrictedCommonPorts:
    Expected (CT baseline): Deny ec2:AuthorizeSecurityGroupIngress on ports 0, 23, 3389, 22, ...
    Actual content: Policy was MODIFIED — the Deny statement on port 22 (SSH) was REMOVED
    Drift type: SCP_CONTENT_MISMATCH (manual edit detected outside Control Tower)
  AWSControlTowerGuardrailRootMfaEnabled: Content matches baseline

Config recorder status (all managed accounts): ENABLED, recording: true
AWSControlTowerExecutionRole: Present in all managed accounts
Account Factory baseline stacks (AWSControlTowerBP): All deployed, no drift
