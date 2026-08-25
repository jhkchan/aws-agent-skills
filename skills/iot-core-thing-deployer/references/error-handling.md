# Error handling — iot-core-thing-deployer

Per-symptom failure playbooks, moved verbatim from SKILL.md for progressive disclosure. Load on demand.


## Error handling (moved from SKILL.md)

### Device cannot connect (connection refused)
- Verify certificate is ACTIVE. Verify policy is attached to the
  CERTIFICATE (not the thing). Verify certificate is attached to the
  thing as a principal. Check `iot:Connect` resource matches client ID.

### Topic rule not triggering
- Verify SQL topic filter matches the MQTT topic. Check IAM role
  permissions. Look at the error action topic. Verify rule is enabled.

### Device shadow delta not clearing
- Device must update reported state to match desired. If device is
  offline, delta persists until reconnection and update.

### Job not reaching devices
- Verify things are in the target group. Check rollout rate. Verify
  job is IN_PROGRESS. For snapshot jobs, things added later do not
  receive the job.

### Custom authorizer errors
- Verify authorizer is ACTIVE. Check Lambda logs. Verify signing keys.
  Test with `iot test-invoke-authorizer`.
