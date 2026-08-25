# Error Handling — Personalize Campaign Deployer

Provisioning failure modes and fixes. Loaded on demand by the skill.

## Error handling

- **Solution version CREATE_FAILED:** insufficient training data (fewer
  than ~1000 interactions). Add more data and re-import. Check the
  error message for specifics.
- **Campaign CREATE_PENDING:** the solution version is not yet ACTIVE.
  Wait for training (`describe-solution-version`), then create.
- **InvalidInputException on import job:** CSV headers do not match the
  schema, or a column has the wrong type. Validate before importing.
- **ResourceNotFoundException on PutEvents:** the tracking ID is wrong,
  or the event tracker was recreated. Update the client.
- **Filter InvalidFilterExpression:** the expression has a syntax error
  or references a column not in the dataset.
- **Campaign UPDATE_PENDING:** the campaign is updating to a new
  solution version. Wait ~15 minutes; GetRecommendations continues
  serving the previous version during the update.
- **High bill:** minProvisionedTPS is set higher than needed. Reduce
  via `update-campaign --min-provisioned-tps`.

