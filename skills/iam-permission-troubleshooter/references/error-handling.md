# Error Handling — IAM Permission Troubleshooter

Remediation guidance per deny type moved verbatim from SKILL.md. Loaded on demand.

## Remediation guidance (from SKILL.md § Remediation guidance)

### For implicit deny (most common)

1. Identify the specific missing action and resource ARN from
   `simulate-principal-policy` output.
2. Add the minimum-scope Allow statement to the identity-based policy:
   specific action, specific ARN, no wildcards.
3. For cross-account, also add the corresponding Allow on the
   resource-based policy.
4. Re-run the simulator. If the simulator now returns `allowed`, the
   fix is complete.
5. Apply the policy change via a new managed policy version (do not
   edit inline — preserve audit history).

### For explicit deny

1. Identify the Deny statement from CloudTrail `errorMessage` or
   simulator matched statements.
2. Determine whether the Deny SHOULD match this request:
   - If yes (the workload should be in scope of the deny): the workload
     must be re-architected (different region, different resource tag,
     different network path) — do not weaken the deny.
   - If no (the deny was written too broadly): scope the deny to
     exclude the workload via a `Condition` (e.g.,
     `StringNotEqualsIfExists: aws:ResourceTag/Allow: "true"`).
3. Apply the deny-policy change. Test that the previously-denied call
   now succeeds AND that the deny still blocks the calls it was
   designed to block (regression test).

### For SCP denies (escalation path)

1. Identify the SCP from `organizations list-policies-for-target`.
2. Read the SCP from the management account.
3. If the workload is genuinely in scope, no SCP change — the workload
   must comply. Output ESCALATE if the SCP is owned by a central team.
4. If the SCP was written too broadly (e.g., region restriction
   excludes a region the workload legitimately uses), request an
   exception or a scoped exclude condition.

### For KMS key policy denies

1. Identify the calling role ARN.
2. Add a statement to the KEY policy (resource-based) granting
   `kms:Decrypt` (and `kms:DescribeKey` if the workload needs it) to
   the calling role ARN.
3. ALSO verify the caller's identity-based policy has `kms:Decrypt` on
   the key ARN (cross-account intersection).
4. If the key has a grant-based access pattern, prefer
   `kms:CreateGrant` over editing the key policy.

### For trust-policy AssumeRole denies

1. Read the target role's `assumeRolePolicyDocument`.
2. Identify the missing principal, condition, or external ID.
3. Add the caller's ARN to the `Principal.AWS` list. If the caller is
   a service, use the service principal
   (`lambda.amazonaws.com`) AND the service-linked role ARN if
   applicable.
4. If `sts:ExternalId` is required, ensure the caller passes the
   correct external ID (configured on both sides).
