# Error Handling — Route 53 ARC Deployer

Error-handling deep dives moved out of the SKILL.md body. Loaded on demand.


## Error handling

### Cluster stuck in CREATING
- Recovery cluster creation takes 10-15 minutes. If it exceeds 20
  minutes, check IAM permissions and service-linked role creation.
  Do not create resources until the cluster is ACTIVE.

### Routing control toggle rejected
- A safety rule is preventing the toggle. Check which safety rule is
  blocking by reviewing the rule config. For OR rules, at least one
  other control must remain ON. For AND rules, the other control
  must be OFF first.

### Readiness check returns NOT_AUTHORIZED
- ARC lacks IAM permission to access the resource. Add the
  `route53-recovery-readiness` service-linked role or grant
  cross-account read permissions for resources in other accounts.

### Resource set type mismatch
- The resource was mapped with the wrong CloudFormation type. Delete
  the resource set entry and recreate with the correct type. Verify
  the resource type matches the actual AWS resource type.

### Routing control state stuck
- The cluster may have lost quorum. Check
  `describe-cluster` for quorum status. If fewer than 3 of 5 clusters
  are available, toggles will fail. This is extremely rare and
  typically resolves automatically.
