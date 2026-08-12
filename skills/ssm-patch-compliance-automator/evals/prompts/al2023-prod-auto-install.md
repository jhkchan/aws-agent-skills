# Eval prompt: al2023-prod-auto-install

Design a patch-compliance automation workflow for the following EC2
fleet. Emit the standard PATCH block (BASELINE, PATCH_GROUP,
MAINTENANCE_WINDOW, COMPLIANCE_MONITORING, SAFETY, REBOOT, VERDICT,
TEMPLATE).

Design reference: al2023-prod-auto-install
Account: 111111111111
Region: us-east-1

Fleet: 120 Amazon Linux 2023 instances (prod environment)
All instances tagged: "Patch Group" = "al2023-prod"
SSM agent: all instances Online (verified via describe-instance-information)
Existing baseline: al2023-prod-baseline (pb-0abc123def)
  - Critical/Important: ApproveAfterDays 0
  - Medium: ApproveAfterDays 7
Maintenance window: weekly Saturday 02:00 UTC, 4 hours, cutoff 1 hour
Pre-patch snapshot: enabled (aws:createImage)
SNS notification: arn:aws:sns:us-east-1:111111111111:patch-notify
Pre-prod validation: canary cycle completed (3 instances, all Compliant).
RebootOption: RebootIfNeeded
