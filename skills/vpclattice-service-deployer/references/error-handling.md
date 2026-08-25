# Error Handling — VPC Lattice Service Deployer

Deep reference content moved verbatim from `vpclattice-service-deployer/SKILL.md`. Loaded on demand;
see SKILL.md for the condensed core and its quick navigation.

## Error handling deep dives

### Service returns 503 (no healthy targets)
- All targets in the target group are failing health checks. Verify
  health check path, port, and matcher. Check that targets are running
  and responding on the health check path. Use `list-targets` to see
  health status and reasons.

### Cross-account invocation fails with AccessDenied
- Either the RAM resource share was not accepted, the VPC association
  was not created in the consumer account, or the resource-based service
  policy does not include the consumer account principal. Verify all
  three: RAM, association, service policy.

### Custom domain does not resolve
- The Route 53 record may not point to the service DNS name. Or the ACM
  certificate is not in us-east-1. Verify the cert ARN region and DNS
  record target.

### VPC instances cannot reach the Lattice service
- The VPC may not be associated with the service network. Verify the VPC
  association status is ACTIVE. Without association, Lattice DNS names
  do not resolve within the VPC.

### Auth policy not enforcing
- The service auth type may not be set to AWS_IAM. The auth policy only
  takes effect when the service auth type is AWS_IAM. Use
  `update-service --body '{"authType":"AWS_IAM"}'` to set it.
