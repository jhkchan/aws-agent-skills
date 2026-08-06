# Eval prompt: landing-zone-modified-drift

Audit the following Control Tower configuration. Emit the standard VERDICT
block (LANDING_ZONE, OU, VERDICT, REASON, FINDINGS, REMEDIATION).

Audit target: Landing zone "production-landing-zone-modified-drift"

Landing zone version: 3.3
Landing zone state: ACTIVE
Landing zone drift status: DRIFTED

Landing zone drift details (CloudFormation detect-stack-set-drift):
  StackSet: AWSControlTowerBP
    Drifted stack instances: 3 of 10
    Drift type: TEMPLATE_MISMATCH — StackSet template was modified outside Control Tower
    Affected accounts: 111111111115, 111111111116, 111111111117

  StackSet: AWSControlTowerSecurityResources
    Drifted stack instances: 1 of 10
    Drift type: PARAMETER_MISMATCH — Lambda function code hash differs from baseline

Enabled controls (list-enabled-controls) on root OU:
  1. arn:aws:controltower:us-east-1::control/AWS-GR_RESTRICTED_COMMON_PORTS
     Type: PREVENTIVE | Category: MANDATORY | Status: SUCCEEDED
  2. arn:aws:controltower:us-east-1::control/AWS-GR_DISABLE_ROOT_ACCESS_KEYS_NO_HSM
     Type: PREVENTIVE | Category: MANDATORY | Status: SUCCEEDED

SCP verification: SCPs match baseline content
Config recorder status (all managed accounts): ENABLED, recording: true
AWSControlTowerExecutionRole: Present in all managed accounts
