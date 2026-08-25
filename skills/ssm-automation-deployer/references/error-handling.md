# Error Handling — SSM Automation Deployer

Execution-failure deep dives moved from SKILL.md. Load when an automation execution fails or matches one of these signatures.

## Error-handling deep dives (moved from SKILL.md)

### Automation execution fails with "AccessDenied"
- The execution role lacks permissions. Review role policy against
  every step's API call. Common missing: `iam:PassRole`.

### Automation fails with "InvalidAssumeRole"
- Trust policy does not allow `ssm.amazonaws.com`. Verify trust
  policy includes the SSM service principal.

### aws:branch evaluates wrong condition
- Condition syntax: `{{ StepName.OutputName == 'value' }}`. Verify
  output variable names match outputs defined in prior steps.

### No targets matched
- Resource group or tag query returned zero resources. Verify group
  has members. Use `aws resource-groups get-group-query-results`.

### Rate control throttling
- MaxConcurrency exceeds quota (default 10). Request increase or
  reduce concurrency.
