# Error Handling — VPC Lattice Auth Auditor

Deep reference content moved verbatim from `vpc-lattice-auth-auditor/SKILL.md`. Loaded on demand;
see SKILL.md for the condensed core and its quick navigation.

## Malformed auth-policy ERROR output (pre-flight gate)

**If the auth-policy JSON is malformed** (invalid JSON, missing `Statement`),
output:

```text
SERVICE NETWORK: <sn-id>
VERDICT: ERROR
REASON: Auth policy document is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical policy with aws vpc-lattice get-auth-policy --resource-arn <arn> --output json and re-audit.
```

## API errors during live-account audit

- **API errors during live-account audit.** If `get-auth-policy` returns
  `AccessDeniedException`, output VERDICT: ERROR with REMEDIATION noting the
  caller lacks `vpc-lattice:GetAuthPolicy`. If `ThrottlingException` occurs,
  retry with exponential backoff. If `ResourceNotFoundException`, the
  service network may have been deleted mid-audit — note and skip.

## CONFIG_GAP remediation ticket rule

- **All CONFIG_GAP findings require a remediation ticket within 24 hours.**
  Even scoped cross-account invoke is a fragile state — the auditor should
  recommend a concrete fix, never defer with "acceptable risk."
