# Eval prompt: landing-zone-healthy-ok

Audit the following Control Tower configuration. Emit the standard VERDICT
block (LANDING_ZONE, OU, VERDICT, REASON, FINDINGS, REMEDIATION).

Audit target OU: arn:aws:organizations::111111111111:ou/o-abcd/ou-landing-zone-healthy-ok

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
  4. arn:aws:controltower:us-east-1::control/AWS-GR_AUDIT_BUCKET_REGION
     Type: PREVENTIVE | Category: MANDATORY | Status: SUCCEEDED

SCP verification:
  AWSControlTowerGuardrailRestrictedCommonPorts: Content matches baseline
  AWSControlTowerGuardrailDisableRootAccessKeys: Content matches baseline
  AWSControlTowerGuardrailRootMfaEnabled: Content matches baseline
  AWSControlTowerGuardrailAuditBucketRegion: Content matches baseline

Config recorder status (all managed accounts): ENABLED, recording: true
Config aggregation (audit account): Aggregator healthy, all accounts delivering
AWSControlTowerExecutionRole: Present in all managed accounts, trust policy correct
Account Factory baseline stacks (AWSControlTowerBP): All deployed, no drift
