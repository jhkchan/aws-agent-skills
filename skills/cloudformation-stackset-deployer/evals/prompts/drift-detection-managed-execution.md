# Eval: drift-detection-managed-execution

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — managed execution Active=true, continuous drift detection, auto-deployment enabled

## Prompt

I have a SERVICE_MANAGED StackSet named guardduty-baseline
targeting ou-xyz-87654321 across us-east-1, us-east-2, and
us-west-2. Template at s3://templates/guardduty.yaml.
Organizations trusted access is enabled. I want managed
execution enabled with auto-deployment Enabled=true,
RetainStacksOnAccountRemoval=false. Enable continuous drift
detection. Capabilities: none. Account ID: 111111111111.
