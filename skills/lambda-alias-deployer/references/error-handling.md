# Error Handling — Lambda Alias Deployer

API error deep dives moved verbatim from SKILL.md.

## Error handling

### "InvalidParameterValueException: function version does not exist"
- The version number in `--function-version` does not exist. Verify
  with `aws lambda list-versions-by-function`. Publish a version
  first with `aws lambda publish-version`.

### "ResourceConflictException: alias already exists"
- Alias names are unique per function. Delete the existing alias
  (`aws lambda delete-alias`) before re-creating, or use
  `update-alias` to modify the existing one.

### Provisioned concurrency stuck in `PROGRESSING` or `FAILED`
- Verify the alias exists and points to a valid version. Check IAM
  permissions for the service-linked role. Verify the account's
  concurrent execution limit (`aws lambda get-account-settings`).

### Traffic shifting weight not changing
- Verify the version in `AdditionalVersionWeights` is a published
  version (not `$LATEST`). Verify the alias already points to the
  primary version. Weights must sum to 1.0 (100%).

### API Gateway invoking `$LATEST` instead of the alias
- The integration URI is missing the alias qualifier. Update the
  integration to include `:prod` (or the alias name). Re-deploy the
  API Gateway stage.

### SnapStart snapshot not created
- SnapStart was enabled AFTER the version was published. Enable
  SnapStart on the function first (`update-function-configuration`),
  then publish a new version. The new version will have the snapshot.
