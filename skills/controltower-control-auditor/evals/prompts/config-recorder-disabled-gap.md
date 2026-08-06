# Eval prompt: config-recorder-disabled-gap

Audit the following Control Tower configuration. Emit the standard VERDICT
block (LANDING_ZONE, OU, VERDICT, REASON, FINDINGS, REMEDIATION).

Audit target OU: arn:aws:organizations::111111111111:ou/o-abcd/ou-config-recorder-disabled-gap

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
  AWSControlTowerGuardrailRestrictedCommonPorts: Content matches baseline
  AWSControlTowerGuardrailDisableRootAccessKeys: Content matches baseline
  AWSControlTowerGuardrailRootMfaEnabled: Content matches baseline

Config recorder status (per account):
  Account 111111111112: ENABLED, recording: true
  Account 111111111113: ENABLED, recording: true
  Account 111111111115: DISABLED, recording: false
    (configservice describe-config-recorders: status.recording = false)

Config aggregation (audit account): Aggregator present but account
111111111115 is not delivering data (recorder off)

AWSControlTowerExecutionRole: Present in all managed accounts
Account Factory baseline stacks (AWSControlTowerBP): All deployed, no drift
