# Error Handling — Amazon MQ Broker Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Error handling

| Error | Cause | Fix |
|---|---|---|
| `BrokerAlreadyExists` | Broker name in use | `describe-broker` — if config matches, emit READY_TO_DEPLOY; if differs, modify (mutable: instance type, SG, logs) or create NEW broker |
| `Subnet does not span multiple AZs` | All subnets in one AZ | Add subnets in different AZs; verify with `describe-subnets` |
| `IAM authentication requires RabbitMQ engine` | IAM auth on ActiveMQ | Use LDAP/basic for ActiveMQ; IAM is RabbitMQ-only and creation-time |
| `Configuration revision not compatible` | Engine-type/version mismatch | Create new configuration with correct engine-type + version |
| Broker stuck in `REBOOT_IN_PROGRESS` | Modify triggered reboot | Wait for `RUNNING` via `describe-broker --query 'BrokerState'` |
