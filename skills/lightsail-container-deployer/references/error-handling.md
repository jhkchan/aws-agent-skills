# Error handling — lightsail-container-deployer

Error-handling deep dives, moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Error handling (moved from SKILL.md)

### Deployment stuck in PENDING
- Check if the container image is accessible. For ECR, verify the IAM
  access key has ECR read permissions and is not deactivated. For
  public images, verify the image exists and the tag is correct.

### Public endpoint returns 503
- Verify the container port is mapped and the container is running.
  The health check path must return HTTP 200. Check if the application
  has started successfully by viewing CloudWatch Logs.

### Health check failing
- The health check path must return HTTP 200 with the specified success
  codes. Verify the path exists and responds correctly. A path returning
  3xx (redirect) or 4xx (client error) will mark the endpoint unhealthy.

### Cannot pull from ECR
- Verify the IAM access key has `ecr:GetDownloadUrlForLayer`,
  `ecr:BatchGetImage`, and `ecr:GetAuthorizationToken` permissions.
  Check if the key has been rotated or deactivated.
