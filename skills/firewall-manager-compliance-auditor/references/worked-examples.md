# Worked Examples — Firewall Manager Compliance Auditor

Secondary worked examples, moved verbatim from SKILL.md. Load on demand.

### Worked example — malformed ManagedServiceData (WAFV2 with broken WebACL ref)
```text
POLICY: wafv2-broken-managed-data
POLICY_NAME: edge-waf-v2
POLICY_TYPE: WAFV2
VERDICT: CONFIG_GAP
REASON: ManagedServiceData JSON is malformed — the referenced WebACL
ARN cannot be validated (Step 6). PolicyState is READY and
RemediationEnabled is true, but FMS has nothing to apply.
FINDINGS:
  - [CONFIG_GAP] SecurityServicePolicyData.ManagedServiceData does not
    contain a valid webACLId — cannot confirm WebACL exists (Step 6)
  - [OK] PolicyState=READY (Step 1)
  - [OK] RemediationEnabled=true (Step 4)
REMEDIATION:
  1. Re-fetch canonical policy: `aws fms get-policy --policy-id <id>
     --output json`.
  2. Inspect SecurityServicePolicyData.ManagedServiceData — parse as
     JSON and verify webACLId is non-empty.
  3. If WebACL was deleted, recreate via `aws wafv2 create-web-acl`,
     then `aws fms put-policy` with corrected ManagedServiceData.
```
