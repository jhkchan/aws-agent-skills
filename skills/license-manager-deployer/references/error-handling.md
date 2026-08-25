# Error handling — license-manager-deployer

Error-handling deep dives, moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Error handling (moved from SKILL.md)

### License configuration creation fails with validation error
- Verify `--license-counting-type` is one of `vCPU`, `Instance`, `Core`.
  Verify `--license-count` is a positive integer. Verify `--license-rules`
  syntax matches the vendor rule format.

### Cross-account sharing fails
- Verify Organizations is all-features enabled. Verify License Manager
  is a trusted service. Verify the target account/OU exists in the Org.

### SSM discovery not finding on-premises resources
- Verify the server is an active SSM managed instance. Verify the SSM
  inventory association includes `Aws:SoftwareInventory`. Verify
  `EnableIntegration=true` in discovery settings.

### Violations not being alerted
- Verify `LicenseRulesEnforce=true`. Verify the EventBridge rule matches
  `aws.license-manager` source. Verify the SNS topic policy allows
  EventBridge to publish.

### License consumption not updating
- Verify the configuration is associated with running resources. For
  EC2, verify the association via launch template. For SSM, verify
  inventory is collecting.
