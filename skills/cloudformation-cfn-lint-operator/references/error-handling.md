# Error Handling — CloudFormation cfn-lint Operator

Load-on-demand error handling moved verbatim from SKILL.md.

## Error handling — symptom mappings

### cfn-lint fails with errors
- Fix structural/logical errors: correct `Ref` targets, resolve
  circular dependencies, add missing required properties.

### validate-template fails
- Invalid syntax or resource properties. Fix the template structure.
  Check the AWS resource specification for correct property names.

### cfn-nag finds CRITICAL findings
- Fix security anti-patterns: scope IAM policies, add encryption,
  restrict ingress. Suppress false positives with justification.

### ChangeSet shows unexpected Replacement: True
- An immutable property changed. Review the changed property. If
  unintentional, revert the change before executing the ChangeSet.

### Drift detection shows DRIFTED
- Resources modified outside CloudFormation. Update the template to
  match actual configuration, or revert out-of-band changes.

### Stack deployment fails (rollback)
- CloudFormation auto-rolls back to the previous known-good state.
  Review `describe-stack-events` for the cause. Fix and retry.
