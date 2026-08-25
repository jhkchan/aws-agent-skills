# Error Handling — Organizations Account Deployer

Provisioning API error table. Loaded on demand by the skill.

## Error handling

| Error | Cause | Fix |
|---|---|---|
| `Account already exists in the organization` | Email or name collision | `list-accounts`; use a new email or remove the conflicting account |
| `You have exceeded the number of accounts` | Account quota hit (default 4-100k by tier) | Request a quota increase via AWS Support |
| `The requested email address is already associated with an AWS account` | Email reused across AWS | Use a unique distribution list email |
| `CreateAccountStatus: FAILED` | IAM role name invalid, email invalid, SCP blocking | `describe-create-account-status` — read `FailureReason`; fix root cause |
| `AccessDeniedException` on `attach-policy` | SCP / tag policy type not enabled on root | `enable-policy-type --root-id <root> --policy-type SERVICE_CONTROL_POLICY` |
| New account not inheriting org trail | Trail created after the account, or not an org trail | Verify `IsOrganizationTrail=true`; recreate trail as org trail |
| SSO permission set assignment fails | Identity Center not enabled, or principal ID wrong | `sso-admin list-instances`; confirm principal ID is a group in the store |

