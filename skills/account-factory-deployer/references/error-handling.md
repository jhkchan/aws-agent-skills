# Error Handling — AWS Control Tower Account Factory Deployer

Load-on-demand error-handling detail moved verbatim from SKILL.md.

## Error handling

### Account provisioning stuck in CREATE_IN_PROGRESS
- Account creation takes 5-30 minutes. If it exceeds 30 minutes, check
  the Service Catalog provisioning status for errors. Common causes:
  duplicate email, OU not registered, or IAM permission issues in the
  management account.

### Baseline StackSet deployment failed
- Check the StackSet operation status in the management account. Common
  causes: missing `AWSControlTowerExecutionRole` in the target account,
  conflicting resources (e.g., an existing CloudTrail), or IAM
  permission issues. Re-run the StackSet after fixing the root cause.

### SSO permission set not available in the account
- The permission set was assigned but not provisioned. Run
  `provision-permission-set` to push the permission set to the account.
  Also verify the account is enrolled in the Identity Center.

### Account has no Guardrails despite being in an OU
- The OU is NOT registered with Control Tower. Only registered OUs get
  Guardrails. Register the OU via the Control Tower console or verify
  the OU's registration status. If the account was in the OU before
  registration, it may need to be re-enrolled.

### Alternate contacts not set
- The contacts were not set during provisioning. They are per-account
  and NOT inherited from the OU. Set them manually via
  `put-alternate-contact` or automate via a custom StackSet in the
  account customization pipeline.
