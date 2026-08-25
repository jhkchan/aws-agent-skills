# Auto-Remediation Automator — Error Handling

Error-handling deep dives and API error tables moved from SKILL.md.
Load on demand when wiring or debugging a remediation configuration.


## SSM document parameter contract (moved from SKILL.md Step 3)

Document parameter contract — for
`AWS-DisableS3BucketPublicAccess`:

| Parameter | Type | Source |
|---|---|---|
| `S3BucketName` | String | `ResourceValue: RESOURCE_ID` (Config injects the bucket name) |
| `AutomationAssumeRole` | String | Static: the SSM service role ARN |

A remediation configuration without the right `ResourceValue` mapping
fails at execution. Always cross-reference the document's parameter
list with the remediation configuration.


## Common `put-remediation-configurations` errors and fixes (moved from SKILL.md Step 5)

Common errors and fixes:

| Error | Cause | Fix |
|---|---|---|
| `AccessDeniedException` | SSM service role missing or wrong ARN | Create `AWS-SSM-AutomationExecutionRole` via `iam create-role` with the `AmazonSSMAutomationRole` policy |
| `ValidationException: SSM document not found` | Wrong `TargetId` or document not in region | Verify with `ssm describe-document --name <name>` |
| `InvalidParameterValue` for parameters | Static value where dynamic expected, or vice versa | Cross-reference document parameter list |
| Remediation configured but no executions | Rule exists but no NEW evaluations since config was set | Call `start-remediation-execution` for existing NON_COMPLIANT resources |
