# Error Handling — AppConfig Deployer

Error-handling remedies moved verbatim from the SKILL.md body for
progressive disclosure (agentskills.io). Loaded on demand by the skill.

---

## Error handling

- **Deployment blocked by validator:** the Lambda validator returned
  non-200. Check function logs, fix the config content, create a new
  version, and retry.
- **Deployment rolled back automatically:** a CloudWatch alarm fired
  during bake time. Check alarm metrics and logs, fix the config,
  create a new version, and retry.
- **Configuration version creation fails:** JSON schema validation
  failed at creation time. Ensure the config content conforms to the
  schema constraints.
- **Deployment stuck in BAKING:** the deployment is in the bake window
  monitoring alarms. Verify the strategy configuration and alarm
  thresholds if this persists.
- **Environment not found:** the environment ID does not exist within
  the application. Verify the application/environment ID pairing.
