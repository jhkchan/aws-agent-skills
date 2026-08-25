# Advanced Patterns (load on demand) — Detective Investigation Coverage Auditor

Step 0 expert-knowledge deep dive and Recent AWS features moved verbatim from SKILL.md.
The core classification steps, verdict matrix, NEVER list, and remediation guidance remain in SKILL.md.

---

## Step 0: Expert knowledge — non-obvious Detective behaviors (moved from SKILL.md)

These behaviors are easy to misjudge without operational Detective
experience. Each changes the verdict if ignored:

- **GuardDuty is the PRIMARY investigation trigger.** Detective ingests
  GuardDuty findings as its primary security-signal source. Without
  GuardDuty enabled in the same region, the behavior graph still ingests
  CloudTrail and VPC Flow Logs but has no security findings to pivot from.
  A graph without GuardDuty is a telemetry store, not an investigation
  tool. Always check GuardDuty detector status as part of the audit.

- **DETECTIVE_CORE is the mandatory data-source package.** Every member
  account must have `DETECTIVE_CORE` in `COLLECTING` state. EKS_AUDIT and
  EKS_RUNTIME are additive packages — if they are STOPPED, the core graph
  still functions but lacks EKS-specific telemetry. Treat a STOPPED
  DETECTIVE_CORE as a complete ingestion failure for that member.

- **Member invitation acceptance window is 50 days.** After 50 days, the
  invitation expires and must be re-sent. An account in `INVITED` state
  for > 50 days is effectively unmanaged — it never accepted, the
  invitation likely expired, and the account has zero coverage.

- **ACCEPTED_BUT_DISABLED is a silent failure.** A member account that
  was previously enabled and then disabled retains its invitation history
  but is not ingesting. This state is easy to miss because the account
  appears in the member list (not as a new invitation) but contributes
  zero data to the graph.

- **Data-source package states are per-member, not per-graph.**
  `batch-get-graph-member-datasources` returns the package state for each
  individual member account. A member can be ENABLED at the graph level
  but have DETECTIVE_CORE in STOPPED state — this is an ingestion gap,
  not a config gap. Always check per-member data-source states, not just
  the graph-level summary.

- **lastDataReceived is ingestion time, not processing time.** The
  timestamp reflects when data was last received from the member account,
  not when it was processed into the graph. Detective has an additional
  processing lag of up to 12 hours after ingestion. A
  `lastDataReceived` of 6 hours ago may mean the graph is actually
  18 hours behind real-time.

- **Deleting a behavior graph is irreversible.** When you delete a graph,
  all historical investigation data (entity profiles, behavior baselines,
  finding correlations) is permanently destroyed. Re-enabling Detective
  creates a fresh graph with no historical context. The investigation
  baseline starts from zero — it takes weeks to rebuild behavioral
  baselines. Treat graph deletion as a one-way door.

- **Organizations delegated admin enables auto-enrollment.** When a
  delegated admin account is configured, new member accounts added to the
  Organization are automatically invited to the Detective behavior graph.
  Without delegated admin, each new account requires a manual invitation —
  a process that is frequently forgotten, creating coverage gaps.

- **Detective pricing is per-GB-ingested, not per-account.** Large
  organizations with high CloudTrail volume can incur significant costs.
  A common pattern is enabling Detective in all regions and discovering
  unexpected charges. Check the data-ingestion volume before enabling in
  new regions. The DETECTIVE_CORE package is the primary cost driver;
  EKS packages add incremental volume.

- **VPC Flow Logs are auto-ingested; no manual configuration needed.**
  Detective automatically ingests VPC Flow Logs from member accounts —
  there is no separate enablement step. However, if VPC Flow Logs are
  disabled at the VPC level (not a Detective setting), the graph loses
  network-behavior telemetry. This is a VPC config issue, not a Detective
  config issue.

- **Cross-account investigation aggregates into ONE graph.** Detective's
  admin account sees data from ALL member accounts in a single unified
  graph. Member accounts see only their own data. For org-wide
  investigations, always work from the admin account — a member account
  cannot pivot across account boundaries.

- **Security Hub integration (ASFF_SECURITYHUB_FINDING) is bidirectional.**
  Detective can forward its own findings to Security Hub AND consume
  Security Hub findings as a data source. If the Detective-to-SecurityHub
  integration is disabled, Detective findings will not appear in Security
  Hub dashboards — this is a visibility gap, not an ingestion gap.

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **EKS Runtime data-source package (2024-2025):** Detective added the
  `EKS_RUNTIME` data-source package, providing container runtime telemetry
  for EKS clusters. Auditors should verify this package is enabled on
  member accounts running EKS workloads — it requires the EKS detector
  agent and is not enabled by default.
- **Security Hub ASFF integration (2024-2025):** Detective can now forward
  findings to Security Hub using the ASFF (AWS Security Finding Format).
  Auditors should verify the integration is enabled if the org uses
  Security Hub for centralized finding management.
- **Organizations auto-enrollment enhancements (2024):** Improved
  delegated-admin workflows allow automatic invitation of new member
  accounts. Auditors should verify `describe-organization-configuration`
  returns `autoEnable: true` — without it, new accounts are not invited.
- **Data-source package lifecycle APIs (2024):** New
  `batch-enable-disable-data-source-packages` API replaces the older
  per-member enable flow. Auditors should use the new API for
  programmatic enablement verification.
- **Detective pricing visibility (2024-2025):** Enhanced cost attribution
  per data-source package. Auditors should verify that the DETECTIVE_CORE
  ingestion volume is within budget — EKS packages add incremental cost
  and should be enabled selectively for accounts running EKS.
