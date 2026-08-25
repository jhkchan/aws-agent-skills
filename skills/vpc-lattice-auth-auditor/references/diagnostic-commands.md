# Diagnostic Commands — VPC Lattice Auth Auditor

Deep reference content moved verbatim from `vpc-lattice-auth-auditor/SKILL.md`. Loaded on demand;
see SKILL.md for the condensed core and its quick navigation.

## Live-account pre-flight checks (run before auth-policy classification)

**Live-account pre-flight checks (skip if doing offline policy-doc audit):**
1. Verify the caller can run `vpc-lattice:GetAuthPolicy` — most read-only
   auditor roles CAN, but remediation (`PutAuthPolicy`) requires
   `vpc-lattice:PutAuthPolicy`. Surface access gaps BEFORE the operator
   approves a change.
2. Enumerate ALL services in the network
   (`aws vpc-lattice list-services --service-network-identifier <id>`).
   Each service MAY have its own auth policy that overrides the network's.
   A network-level audit that skips service-level policies misses silent
   bypasses.
3. Check RAM resource shares
   (`aws ram list-resources --resource-owner SELF --resource-arn <sn-arn>`).
   A service network shared cross-account via RAM grants the consumer
   account visibility. If no auth policy gates the share, consumer VPC
   resources can invoke services.
4. **Enumerate the caller's IAM identity-based policy.** For each principal
   granted Invoke in the auth policy, run
   `aws iam list-attached-role-policies --role-name <role>` and
   `aws iam list-inline-role-policies --role-name <role>` to confirm the
   intersection model actually permits invocation. An auth-policy Allow
   without a corresponding IAM Allow means cross-account callers CANNOT
   invoke (but same-account callers still can via union).
5. **Handle pagination on all list-* calls.** `list-services`,
   `list-target-groups`, and `list-resource-shares` may paginate. Use
   `--no-paginate` or loop on `--starting-token` until `NextToken` is null.
   Missing paginated results means missed services, missed target groups,
   and a false OK verdict.
6. **After any PutAuthPolicy remediation, wait for eventual consistency.**
   Re-run `get-auth-policy` after 10 seconds to confirm the new policy is
   `ACTIVE` — the API is eventually consistent and may return stale results
   immediately after a write.
