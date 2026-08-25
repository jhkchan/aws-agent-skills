# Error Handling — Firewall Manager Compliance Auditor

Error-branching and malformed-JSON recovery patterns, moved verbatim from SKILL.md. Load on demand.

## Error-code branching and malformed JSON recovery
### Error-code branching

| Error | Meaning | Auditor action |
|---|---|---|
| `AccessDeniedException` on `fms put-policy` | Caller is a member account, not the FMS admin. | Surface before remediation: only the delegated admin can remediate. |
| `ResourceNotFoundException` on `get-policy` | Policy was deleted between list and get (race). | Re-run `list-policies`; skip the stale id. |
| `InvalidOperationException` on `get-compliance-detail` | Policy is NOT_READY (no compliance data). | Confirm Step 1 finding; compliance count is not trustworthy. |
| `LimitExceededException` on `put-policy` | Org hit the 50-policy quota. | Delete unused policies before creating new ones; do NOT silently retry. |
| `InternalErrorException` | Transient FMS backend. | Retry with exponential backoff (max 3). |

### Malformed JSON recovery

When `get-policy` returns a policy with malformed `ManagedServiceData`
(the embedded WebACL/SG JSON inside
`SecurityServicePolicyData.ManagedServiceData`), classify the
dimensions you can (PolicyState, RemediationEnabled, scope) and emit
a CONFIG_GAP for the unvalidatable dimension:

**Detection steps:**
1. Parse `SecurityServicePolicyData.ManagedServiceData` as JSON. If it
   fails, the WebACL/SG baseline reference is unverifiable.
2. For WAFV2 policies, verify the parsed JSON contains a `webACLId`
   field. Empty or missing = CONFIG_GAP.
3. For SECURITY_GROUPS_COMMON, verify it contains a `defaultSecurityGroupId`.
   Empty or missing = CONFIG_GAP.
4. For NETWORK_FIREWALL, verify it contains a `firewallPolicyId`. Empty
   or missing = CONFIG_GAP.

```text
NOTE: ManagedServiceData JSON is malformed for policy <id> — cannot
validate the referenced WebACL/SG baseline. Re-fetch with `aws fms
get-policy --policy-id <id> --output json` and inspect
SecurityServicePolicyData.ManagedServiceData.
```

Do NOT silently mark the policy OK — the WebACL reference may be
broken, meaning FMS has nothing to apply even if RemediationEnabled is
true and PolicyState is READY.

