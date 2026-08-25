# Error Handling — Elastic Beanstalk Environment Optimizer

Optimization failure triage moved verbatim from SKILL.md. Loaded on demand.

## Error handling — optimization failure triage (from SKILL.md)

### Environment update fails during topology change
- Ensure the instance type is compatible with the new topology. Single-
  instance requires a single instance type; load-balanced requires the
  auto-scaling group config.
- Check IAM permissions for `elasticbeanstalk:UpdateEnvironment`.

### Instance replacement after instance type change
- Changing the instance type triggers instance replacement. For single-
  instance environments, this causes brief downtime. For load-balanced,
  instances are replaced one at a time.

### NAT Gateway deletion leaves instances without internet
- Verify the instance has a public IP and the route table has an IGW
  route for 0.0.0.0/0 BEFORE deleting the NAT Gateway.
- If instances are in a private subnet, move them to a public subnet
  first or keep the NAT Gateway.

### Managed update breaks application
- If a managed update breaks the application, roll back by changing the
  platform version to the previous one.
- Disable managed updates until the compatibility issue is resolved.
