# Error Handling — FIS Template Deployer

Error-handling deep dives moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Error handling (moved from SKILL.md)

### Experiment fails to start: permission denied
- The IAM role is missing a required permission. Verify the role has
  the action-specific permission (e.g., `ec2:StopInstances`) AND the
  trust policy allows `fis.amazonaws.com`. IAM propagation can take
  up to 30 seconds.

### Experiment targets zero resources
- The target filter (resource tags) does not match any resources.
  Verify the tags are applied: `aws ec2 describe-instances --filters
  Name=tag:FIS_Target,Values=enabled`. Check that `selectionMode` is
  not `COUNT(0)`.

### Stop condition does not fire
- The CloudWatch alarm is not in ALARM state. Stop conditions trigger
  ONLY when the alarm transitions to ALARM. Verify the alarm threshold
  and that the metric is breaching. Also verify the alarm ARN in the
  template matches the actual alarm ARN.

### Network disruption action fails
- `aws:network:disrupt-connectivity` requires the FIS network agent
  IAM role and additional networking permissions
  (`ec2:CreateNetworkInterface`, etc.). Verify the role includes these.

### Experiment stuck in pending
- FIS may be waiting for the IAM role to propagate, or the target
  resources may be in a state that prevents the action (e.g., already
  stopped). Check the experiment state and action state via
  `get-experiment`.

