# Batch Compute Environment Deployer — error-handling deep dives (RUNNABLE stuck, INVALID CE, spot interruption, Fargate)

Content moved verbatim from SKILL.md (progressive disclosure). Load on demand.

---

## Error handling (moved verbatim from SKILL.md)

### Jobs stuck in RUNNABLE
- Capacity starvation. Verify the job's vCPU/memory request fits the
  instance types. Check state=ENABLED, status=VALID. Check instance role
  trust policy, subnet IPs, and security group outbound 443.

### Compute environment INVALID
- Check `statusReason` in `describe-compute-environments`. Common causes:
  invalid instance role, missing subnets, insufficient permissions.

### Spot instances continuously interrupted
- Pool too narrow. Add more instance types. Verify
  SPOT_CAPACITY_OPTIMIZED. Consider an On-Demand fallback environment.

### Fargate jobs fail to start
- Verify subnets are in the same VPC as security groups. Ensure
  execution role has `ecs-tasks.amazonaws.com` trust and
  `AmazonECSTaskExecutionRolePolicy`.

