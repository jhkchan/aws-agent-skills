# Advanced Patterns (load on demand) — CloudFormation StackSet Deployer

Mindset framing, expert-knowledge heuristics, dependency-graph gotchas, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Mindset — three misconceptions (moved from SKILL.md)

**One-line takeaway:** A StackSet deploys ONE CloudFormation
template across MANY accounts and/or regions from ONE
administrator account. SERVICE_MANAGED integrates with AWS
Organizations for automatic future-account inclusion; SELF_MANAGED
requires explicit account lists and IAM role handshakes per target
account. Operation preferences control blast radius — failure
tolerance + max concurrency are the two dials.

Three misconceptions dominate StackSet misdesign:

- **"StackSets and nested stacks are interchangeable."** A nested
  stack is a child inside ONE parent stack in ONE account/region.
  A StackSet is a multi-account/multi-region deployment wrapper.
  Use nested stacks for decomposition within one stack; use
  StackSets for fan-out across accounts/regions.

- **"SELF_MANAGED is simpler."** It is not, for any org with more
  than a few accounts. SELF_MANAGED requires an administration role
  in the admin account AND an execution role (with matching trust
  policy) in EVERY target account. New accounts are NOT auto-
  included. SERVICE_MANAGED leverages Organizations trusted access —
  no per-account role setup and new accounts in targeted OUs are
  included automatically.

- **"Default operation preferences are fine."** Defaults
  (`FailureToleranceCount=0`, `MaxConcurrentCount=1`) are too
  conservative for large fan-outs. Tune failure tolerance so a
  single account failure does not halt the deployment, and tune
  max concurrency to control the parallel blast radius.
## Dependency graph takeaways and cross-dependency gotchas (moved from SKILL.md)

**The immutable rows are the ones a baseline model misses.** The
permission model is set at StackSet creation and CANNOT be changed
without deleting and recreating the StackSet. The administration
role name is similarly immutable. The procedure below forces an
explicit decision on each before the `create-stack-set` call.

**Cross-dependency gotchas:**
- SELF_MANAGED cannot be "upgraded" to SERVICE_MANAGED — must
  delete and recreate.
- SERVICE_MANAGED always skips the management (formerly "master")
  account. Use a SELF_MANAGED StackSet or standalone stack for it.
- Regions × accounts = cartesian product. N accounts × M regions =
  N×M stack instances.
- Disabling Organizations trusted access after a SERVICE_MANAGED
  StackSet exists breaks all future operations on that StackSet.
## Recent AWS features 2023-2026 (moved from SKILL.md Step 9)

**Recent AWS features (2023-2026):**

- **StackSet-level drift detection (2023-2024):** StackSets expose
  `DriftStatus` at the StackSet level (aggregated from instances).
  Combined with managed execution, drift is detected continuously
  and reconciled automatically on updates.

- **Managed execution for SERVICE_MANAGED (2023-2024):**
  `ManagedExecution.Active=true` enables continuous drift detection
  AND automatic reconciliation of account-targeting changes (when
  accounts join/leave a targeted OU, instances are created/deleted
  automatically).

- **Detailed status for stack instances (2023-2024):**
  `StackInstance.ComprehensiveStatus` exposes granular status
  (`PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`,
  `INOPERABLE`, `OUTDATED`) per instance.

- **AccountFilterType for SERVICE_MANAGED (2023-2024):**
  `INTERSECTION` (default), `DIFFERENCE`, `TARGET`, `UNION` —
  enables fine-grained targeting within an OU (e.g., "deploy to OU
  but exclude sandbox accounts").

- **CloudFormation IaC generator (2023-2025):** Generates
  CloudFormation templates from existing AWS resources. Use
  `create-generated-template` to scan resources and produce a
  template deployable via StackSets. Useful for "lift and shift"
  of existing resources into a StackSet-managed baseline.

- **Per-resource drift detail (2024-2025):** `detect-stack-resource-
  drift` now surfaces the specific resource that drifted, not just
  the instance-level status.

- **RegionConcurrencyType PARALLEL (2024-2025):** Operation
  preferences support `RegionConcurrencyType=PARALLEL` for faster
  multi-region deployments.
