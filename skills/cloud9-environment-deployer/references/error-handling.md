# Error Handling — Cloud9 Environment Deployer

Load-on-demand error handling moved verbatim from SKILL.md.

## Error handling — symptom mappings

### Environment creation fails
- Verify the subnet exists and is in the same region. Verify the
  instance type is valid. Verify the instance profile exists and has
  the correct trust policy. For SSM mode, verify
  `AmazonSSMManagedInstanceCore` is attached.

### IDE fails to connect (SSM mode)
- Verify the instance profile has `AmazonSSMManagedInstanceCore`. Verify
  the SSM agent is running (check Systems Manager console). Verify
  outbound connectivity to SSM endpoints (NAT gateway, VPC endpoints,
  or IGW for public subnets).

### IDE fails to connect (SSH mode)
- Verify the key pair matches. Verify port 22 is allowed in the security
  group from the user's IP. Verify the instance is in a public subnet
  with an internet gateway route.

### Auto-hibernation not triggering
- Verify `--automatic-stop-time-minutes` is set (not 0). Note: the
  timer counts IDE inactivity, not EC2 CPU utilization. The IDE must
  be closed or idle (no active terminal sessions).

### Sharing not working for a user
- Verify the user's IAM identity is correct. Verify the user has
  `cloud9:GetUserPermissions` and `cloud9:DescribeEnvironmentMemberships`
  permissions. The user must open the environment from their own Cloud9
  console.

### EC2 instance stuck in stopped state
- If hibernated, opening the IDE should restart it. If it does not,
  manually start: `aws ec2 start-instances --instance-ids <i-id>`.
  Verify the instance is not in error state.
