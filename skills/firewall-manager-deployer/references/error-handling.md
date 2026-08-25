# Error Handling — Firewall Manager Deployer

Error-handling deep dives, moved verbatim from SKILL.md § Error handling. Load on demand.

## Error handling
### AccessDeniedException on put-policy
- The calling account is not the delegated FMS administrator. Verify
  with `get-admin-account`. If no admin is delegated, run
  `associate-admin-account` from the Organizations management account.

### Resources show as "unknown" compliance
- AWS Config is not enabled in the member account. Enable Config in
  the member account, then wait for FMS to re-evaluate (can take up to
  15 minutes).

### Web ACL changes in member accounts are reverted
- This is expected behavior. FMS-managed Web ACLs are read-only in
  member accounts. All changes must go through the FMS policy in the
  admin account. Editing directly will be reverted on the next
  remediation cycle.

### Policy applies to unexpected accounts
- OU-based targeting auto-expands. New accounts moved into the OU are
  automatically in scope. Use exclude accounts or exclude tags to
  narrow scope. Verify with `list-apps-lists` or the FMS console.

### Policy does not apply to expected accounts (priority conflict)
- A higher-priority policy of the same type is covering the target
  accounts. Verify priority ordering. FMS evaluates first-match wins.

### Network Firewall policy deploys but no firewall is created
- Missing subnet mappings in target accounts. Network Firewall policies
  require firewall subnet mappings for firewall placement. Define
  subnet mappings in the policy or ensure subnets exist in target
  accounts.
