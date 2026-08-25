# Error Handling — QuickSight Dashboard Deployer

Error-handling deep dives moved out of the SKILL.md body. Loaded on demand.


## Error handling

### Data source creation fails with connectivity error
- For private data stores, verify the VPC connection is AVAILABLE and
  the security group allows inbound from QuickSight. For public
  sources, verify the endpoint is reachable.

### SPICE ingestion fails
- Check SPICE capacity: `describe-account-settings`. Verify the SQL
  query is valid and the source is accessible. Check ingestion status
  with `list-ingestions`.

### Dashboard creation fails with schema mismatch
- If creating from a template, the target dataset schema must match
  the source schema. Verify column names and types match.

### RLS not filtering correctly
- Verify the RLS rules dataset maps the correct user ARN/email to the
  correct column values. Check that RLS is ENABLED on the dataset.

### VPC connection stuck in CREATING
- The IAM role must have permissions to create network interfaces.
  Check the role's permissions for `ec2:CreateNetworkInterface`.

### User cannot view shared dashboard
- Verify the user is registered: `describe-user`. Verify the
  dashboard permission grants the reader's principal ARN.
