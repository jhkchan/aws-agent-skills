# Diagnostic Commands — Verified Permissions Policy Auditor

Pre-flight and diagnostic command listings moved out of the SKILL.md body. Loaded on demand.

## Live-account pre-flight checks (policy store metadata gate)

1. Verify the caller's identity can run `verifiedpermissions:UpdatePolicy`
   if remediation is intended — most read-only auditor roles CANNOT.
2. Snapshot `aws verifiedpermissions list-policies --policy-store-id <id>`
   (paged, max 100 per page via `--next-token`) BEFORE any edit — policy
   stores are not versioned; there is no automatic rollback.
3. Confirm the schema is retrieved via `get-schema`, NOT inferred from
   policies — a policy may reference entities not in the schema, and the
   schema is the source of truth for consistency checks.
