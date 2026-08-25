# Error Handling — Greengrass Component Deployer

Failure-mode detail moved verbatim from SKILL.md.

## Error handling — moved from SKILL.md

### Component stuck in ERRORED state
- The startup script is likely exiting immediately (one-shot script
  in startup hook). Move one-shot logic to the install hook, or make
  the startup hook a long-running process. Check device logs at
  `/greengrass/v2/logs/<component>.log`.

### Deployment not reaching the device
- The core device may be UNHEALTHY or offline. Check
  `aws greengrassv2 list-core-devices` for device status. Verify the
  device is in the target thing group. Check network connectivity
  from the device to AWS IoT.

### Artifacts not downloading
- The token exchange role may lack `s3:GetObject` on the artifact
  bucket. Verify the IAM policy attached to the token exchange role
  includes the artifact bucket ARN. Check device logs for S3 access
  errors.

### Configuration merge not taking effect
- The merge keys may not match the recipe's configuration schema.
  Configuration merge only works for keys defined in
  `ComponentConfiguration.DefaultConfiguration`. Verify the merge
  JSON keys match the recipe schema.

### Lambda component fails to start
- The `aws.lambda` component may not be deployed. Verify it is listed
  as a HARD dependency in the recipe and deployed alongside the
  Lambda component. Check that the Lambda runtime is compatible with
  the device architecture.

### Docker container fails to start
- Docker may not be installed or running on the device. Verify
  `docker ps` works on the device. Ensure
  `aws.greengrass.DockerApplicationManager` is deployed. For private
  registries, deploy `aws.docker.Login`.
