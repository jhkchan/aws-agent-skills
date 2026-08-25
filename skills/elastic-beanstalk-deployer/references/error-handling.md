# Error Handling — Elastic Beanstalk Deployer

Deployment failure triage moved verbatim from SKILL.md. Loaded on demand.

## Error handling — deployment failure triage (from SKILL.md)

- **Environment stuck in "Launching"/"Pending":** IAM issue — verify
  instance profile S3 read. Check events via `describe-events`.
- **Deployment fails ("Failed to deploy application"):** check logs via
  `retrieve-environment-info`. Common causes: .ebextensions syntax
  error, failed `container_commands`, incompatible runtime.
- **Health "Red" after deploy:** ELB health check failing. Verify the
  health check path (`/health`) returns 200 OK.
- **CNAME swap fails:** both environments must be "Ready". Wait, retry.
- **Managed updates not applying:** suppressed during active
  deployments. Verify update level is `minor` or `patch`.
