# Eval prompt: tag-key-drift

Diagnose and design a patch-compliance automation workflow for the
following fleet. The fleet appears correctly configured but no
instances are being patched. Emit the standard PATCH block and explain
the root cause.

Design reference: tag-key-drift
Account: 111111111111
Region: us-east-1

Fleet: 80 Amazon Linux 2023 instances
Instances tagged: "PatchGroup" = "al2023-prod" (note: NO space in key)
Baseline: al2023-prod-baseline exists and is registered for "al2023-prod"
Maintenance window: configured with targets Key=tag:Patch Group,Values=al2023-prod
SSM agent: all Online
describe-instance-patch-states: 0 instances returning patch state
