# Error handling — network-firewall-rule-auditor

Retry, throttling, and remediation error handling moved verbatim from SKILL.md (load on demand).

## Pagination retry / backoff

`describe-rule-group` is per-group and rate-limited. On `ThrottlingException`,
use exponential backoff with full jitter: base 1s, factor 2, cap 30s, max 5
retries per group. Do NOT parallelize `describe-rule-group` calls — the quota
is per-account and concurrent calls amplify throttling. Serialize with retry
and record any group that exhausted retries as `VERDICT: ERROR` with reason
`rule-group fetch throttled after N retries`.

`list-rule-groups --scope MANAGED` and `--scope CUSTOMER` are independent
paginations — both must be exhausted before the rule inventory is complete.
A policy can reference rule groups from either scope; missing one scope
silently undercounts the ruleset.

## Error handling during remediation

| Error | Cause | Action |
|---|---|---|
| `InsufficientCapacityException` | Rule group `ConsumedCapacity` would exceed `Capacity` after the proposed additive rule | Create a new rule group with higher capacity, migrate rules, re-attach to policy. Do NOT delete the old group until the new one is verified. |
| `InvalidTokenException` | `UpdateToken` was stale (another write occurred between fetch and mutation) | Re-fetch with `describe-firewall-policy` / `describe-rule-group`, retry the mutation with the fresh token. Never cache tokens across calls. |
| `AccessDeniedException` on `update-*` | The auditor's IAM role lacks `network-firewall:UpdateFirewallPolicy` or `UpdateRuleGroup` | Verify IAM permissions BEFORE emitting remediation CLI — surface the missing action to the operator rather than letting the command fail at runtime. |
| `InvalidOperationException` | Attempting to modify an AWS-managed rule group (`Type: MANAGED`) | Managed groups are not customer-editable. Detach the managed group and create a custom replacement if different behavior is needed. |
| `ThrottlingException` | Rate-limited on `describe-rule-group` during bulk audit (pagination) | Serialize calls (do NOT parallelize — the quota is per-account and concurrent calls amplify throttling). Exponential backoff with full jitter: base 1s, factor 2, cap 30s, max 5 retries per group. Record any group that exhausted retries as `VERDICT: ERROR` rather than silently skipping it. |
