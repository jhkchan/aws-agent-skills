# Eval prompt: flat-org-no-scp

Validate this existing AWS organization governance posture. Emit the
standard GOVERNANCE block.

Current state:
- Org: all-features, 12 member accounts, all under root (flat, no OUs)
- SCPs: none attached at root or any OU
- GuardDuty: running from the management account (NOT delegated to an
  audit account)
- Security Hub: not enabled
- Config aggregator: not configured (no centralized compliance view)
- CloudTrail: per-account trails (no org trail — duplicate events,
  double storage cost)
- IAM Identity Center: not configured (cross-account assume-role only,
  no IdP federation)
- No break-glass path documented
- RAM shares: 3 shares with allow-external-principals=true (could be
  accepted by unintended external principals)
- Resource Explorer: not configured

Expected: MANUAL_STEP_REQUIRED. The skill must flag multiple CRITICAL
gaps:
1. No deny-leave-org SCP — any member can call
   organizations:LeaveOrganization to escape SCP governance entirely.
2. Flat OU structure — blast radius equals the management account for
   all 12 members.
3. GuardDuty in management account — couples security to the most
   privileged account.
4. No Config aggregator — compliance status of member accounts is
   invisible from a central view.
5. No IAM Identity Center — not scalable, no IdP federation.
6. RAM shares with allow-external-principals=true — unintended
   principals can accept.
