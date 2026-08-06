# Eval prompt: disabled-mandatory-control

Audit the following Control Tower configuration. Emit the standard VERDICT
block (LANDING_ZONE, OU, VERDICT, REASON, FINDINGS, REMEDIATION).

Audit target OU: arn:aws:organizations::111111111111:ou/o-abcd/ou-disabled-mandatory-control

Landing zone version: 3.3
Landing zone state: ACTIVE
Landing zone drift status: NOT_DETECTED

Enabled controls (list-enabled-controls):
  1. arn:aws:controltower:us-east-1::control/AWS-GR_RESTRICTED_COMMON_PORTS
     Type: PREVENTIVE | Category: MANDATORY | Status: SUCCEEDED
  2. arn:aws:controltower:us-east-1::control/AWS-GR_DISABLE_ROOT_ACCESS_KEYS_NO_HSM
     Type: PREVENTIVE | Category: MANDATORY | Status: FAILED
     Last operation: ENABLE | Result: FAILED
     Status reason: SCP deployment failed — CloudFormation stack rollback
  3. arn:aws:controltower:us-east-1::control/AWS-GR_ROOT_MFA_ENABLED
     Type: DETECTIVE | Category: MANDATORY | Status: SUCCEEDED
  4. arn:aws:controltower:us-east-1::control/AWS-GR_AUDIT_BUCKET_REGION
     Type: PREVENTIVE | Category: MANDATORY | Status: SUCCEEDED

SCP verification:
  AWSControlTowerGuardrailRestrictedCommonPorts: Content matches baseline
  AWSControlTowerGuardrailDisableRootAccessKeys: NOT ATTACHED to OU
    (enable-control operation FAILED — SCP was never deployed)
  AWSControlTowerGuardrailRootMfaEnabled: Content matches baseline

Config recorder status (all managed accounts): ENABLED, recording: true
AWSControlTowerExecutionRole: Present in all managed accounts
Account Factory baseline stacks (AWSControlTowerBP): All deployed, no drift
