# Advanced Patterns — Clean Rooms Collaboration Auditor

Load-on-demand deep dives moved verbatim from SKILL.md.

## Mindset — the three structural facts (full detail)

- **Membership activation gates every query.** A member in `INVITED` state
  has not accepted the collaboration — they cannot create analysis
  templates, run protected queries, or contribute their configured table.
  The collaboration looks healthy in `get-collaboration` but is
  operationally stalled until every intended member transitions to `ACTIVE`.
- **Differential privacy is a per-member, per-collaboration epsilon
  budget.** Epsilon does NOT renew automatically; it monotonically
  decreases as protected queries execute. A collaboration with epsilon
  spent is not "low risk" — it is **privacy-exhausted**, and any further
  queries run without DP noise would leak row-level signal.
- **Analysis templates are owned per-member, not per-collaboration.** The
  collaboration references them, but only the owning member can update the
  SQL. A template that references a configured-table alias the owner
  removed is a runtime defect that surfaces only at query time — there is
  no live SQL validator on the service side.

## Step 0 — expert knowledge (full catalog of non-obvious behaviors)

- **Membership status is perspective-relative.** `ListMembers` returns the
  collaboration's view of members; `GetMembership` returns the caller's
  view of their own membership. A collaboration can show a member as
  `ACTIVE` from the creator's perspective while the member sees their
  own status as `LEFT` (they self-removed). Always cross-reference both
  views in a multi-party audit; a member listed as ACTIVE who has LEFT is
  a silent MEMBERSHIP_GAP that surfaces only when their queries fail with
  `AccessDeniedException`.

- **Epsilon is per-member, not per-collaboration.** Each member who runs
  protected queries has their OWN epsilon budget contributed to the
  collaboration's total spend. A collaboration where one member has spent
  95% of their budget and another has spent 5% is NOT uniformly healthy —
  the high-spend member is the bottleneck. Report per-member epsilon
  posture, not just the collaboration aggregate.

- **`differentialPrivacyConfig.enabled: true` is not the same as "DP is
  applied."** Differential privacy in Clean Rooms is enforced via the
  `additionalAnalyses` field on each protected query, with the member's
  epsilon contribution specified. A collaboration with DP "enabled" but
  whose protected queries pass `additionalAnalyses: 0.0` (or omit it) is
  running WITHOUT DP noise. The config-level `enabled` flag is the
  capability gate; the per-query epsilon is the enforcement. Always audit
  the most recent protected query's `additionalAnalyses` value, not just
  the collaboration-level flag.

- **Aggregate constraints (MIN/MAX) apply to query OUTPUT rows, not input
  rows.** A constraint of `MIN=10` means the query result must contain at
  least 10 rows per group — it is a privacy check preventing singleton
  re-identification. A configured table with NO aggregate constraints
  means ANY query can return singleton rows — there is no privacy floor.
  Treat the absence of `aggregateConstraints` as a HIGH-severity privacy
  gap regardless of DP status.

- **Analysis templates are SQL-with-parameters, not free SQL.** The
  service validates the SQL at template-creation time against the
  configured tables, BUT it cannot validate runtime parameter values. A
  template with `${dt}` substituted by the caller with a literal that
  matches no rows is a silent query-no-op. Parameter type validation is
  the caller's responsibility — there is no server-side type check.

- **Configured tables are owned per-member and the alias is the join
  key.** The collaboration references configured tables by alias; the
  underlying Glue table can change ARN (account, database, name) without
  the alias changing. If a member removes their configured table but the
  template still references the alias, the next protected query fails
  with `ResourceNotFoundException` at runtime — there is no live validator
  that catches the dangling alias.

- **Configured audiences live in a different API service
  (`cleanroomsml`), not `cleanrooms`.** Audience activation is a
  collaboration-level toggle, but the trained audience model is a
  `cleanroomsml` resource. A collaboration with
  `configuredAudienceModelArn` set to an ARN in CREATE_IN_PROGRESS or
  CREATE_FAILED state will fail at audience-activation time with no
  collaboration-level warning. Always fetch the audience-model state from
  `cleanroomsml get-configured-audience-model` separately — the
  collaboration config shows only the ARN.

- **Protected queries return S3 result locations, not result rows.** The
  protected-query API returns a `outputConfiguration.S3.destination`
  prefix per member; the actual rows are written to S3 in Parquet. An
  audit that checks only the query status (`SUCCEEDED`) without
  verifying the S3 bucket policy on the destination is incomplete — a
  bucket that allows cross-account reads silently widens the audience
  for the (differentiated, noised) result set.

- **A member with status `COLLABORATION_TIME`** is not a real status —
  the canonical states are `INVITED`, `ACTIVE`, `REMOVED`, `LEFT`. Any
  other status string indicates either a stale snapshot or a private
  preview feature. Surface as ERROR rather than guessing semantics.

- **Privacy budget "spend" is reported via the `epsilon` field on the
  protected-query result, not as a counter on the membership.** To audit
  historical spend, page `ListProtectedQueries` and sum the epsilon
  contributions per member. There is no `GetPrivacyBudget` API — the
  budget is a configured cap, and consumption is the integral of query
  epsilons.

- **Clean Rooms is REGION-scoped.** A collaboration in `us-east-1` cannot
  include members whose membership is in `eu-west-1`. Cross-region
  membership is not supported. Verify that every member's account and
  region are aligned with the collaboration's region — a member ARN with
  the wrong region silently fails to activate.

- **`queryLogStatus` is a one-way flag.** Once enabled, it cannot be
  disabled. A collaboration with `queryLogStatus: DISABLED` is a signal
  that logging was never turned on (it is OFF by default at creation);
  the operator must delete and recreate the collaboration to enable it
  post-hoc. Treat as a CONFIG_GAP note, not a privacy verdict.

- **DP noise scales with aggregate SENSITIVITY, not result row count.**
  The noise added per output row is proportional to the sensitivity of
  the underlying column (a column with 2 distinct values has lower
  sensitivity than one with 1M distinct values). This means a query
  that groups by a high-cardinality column (e.g., user_id) receives
  MORE noise per group than one grouping by a low-cardinality column
  (e.g., country). The practical consequence: a template that groups
  by user_id produces noisier results than the epsilon value alone
  suggests — the effective privacy protection is HIGHER than the
  epsilon spend indicates. Do not flag a high-cardinality grouping as
  a privacy weakness; the noise model already compensates.

- **Configured table analysis rules are versioned but queries in
  flight are NOT retroactively re-evaluated.** When a member updates
  their configured table's analysis rule (e.g., tightening
  `aggregateConstraints` from MIN=5 to MIN=10), queries already in
  `RUNNING` state continue under the OLD rule. Only queries
  SUBMITTED after the update pick up the new constraint. This creates
  a race window during remediation: an audit that recommends tightening
  a rule should note that in-flight queries may still produce results
  compliant with the old (weaker) rule.

- **The `CreateMembership` API is idempotent only within the
  invitation window (7 days).** If the invitee does not call
  `CreateMembership` within 7 days of `CreateCollaboration` (or
  `CreateInvitation`), the invitation EXPIRES and the member status
  transitions from `INVITED` to a terminal state that requires the
  creator to re-issue a fresh invitation. A member stuck in INVITED
  for >7 days is not merely "pending" — the invitation has lapsed and
  the creator must re-invite. This is why Rule M1 fires regardless of
  how long the member has been INVITED; the operator either accepts
  or re-invites, there is no "wait longer" option.

- **Configured table `allowedColumns` does NOT auto-sync with the
  underlying Glue Data Catalog.** When a column is dropped from the
  Glue table, the configured table still lists it in `allowedColumns`
  — queries selecting that column fail with `Column not found` at
  runtime, but the error message does not mention schema drift, it
  points at the template. Conversely, a column ADDED to the Glue
  table is invisible to the collaboration until explicitly added to
  `allowedColumns` via `UpdateConfiguredTable`. This creates a silent
  drift window. Always cross-reference the Glue table schema
  (`aws glue get-table`) against the configured table's
  `allowedColumns` during audit — any mismatch is a CONFIG_GAP.

- **A protected query with `additionalAnalyses` epsilon below ~0.1
  SUCCEEDS but produces statistically meaningless results.** The DP
  noise added at very low epsilon overwhelms the signal — the output
  rows are dominated by noise. The service provides no "low
  confidence" warning or quality flag; the analyst receives SUCCEEDED
  status with garbage data. This is a known DP property but the Clean
  Rooms operational impact is invisible: analysts silently trust
  low-epsilon results. Flag any member whose per-query epsilon
  contributions are consistently below 0.1 as a usability risk in
  FINDINGS, even though the verdict may be OK.

- **Clean Rooms charges compute for every configured table referenced
  in an analysis template's FROM/JOIN clauses, regardless of whether
  the WHERE filter eliminates rows from that table.** A template that
  JOINs 5 configured tables but only filters on 1 still incurs 5-table
  scan cost. This is not documented in the pricing page — it surfaces
  only in Cost Explorer under `CleanRooms` usage type. When auditing
  template SQL, flag multi-table JOINs as a cost finding alongside
  correctness — a template joining 4+ tables can cost 10x more than
  a single-table query for the same row count.

- **`ListProtectedQueries` returns results in reverse chronological
  order and caps at 100 per page with NO total count field.** For
  high-traffic collaborations, summing epsilon from a single page
  UNDERCOUNTS actual spend — the API gives no indication how many
  pages remain. You must drain `nextToken` to `null` and sum across
  ALL pages. A collaboration with 500 queries requires 5 paginated
  calls; missing any page produces a false "epsilon healthy" verdict.
  This is the most common source of incorrect PRIVACY_RISK
  classifications in production audits.

- **Spark-engine collaborations (`analyticsEngine: SPARK`) use a
  separate execution role that lives on the MEMBERSHIP, not the
  collaboration.** The collaboration config does not show this role.
  The execution role requires `iam:PassRole` for the Clean Rooms
  service principal AND read access to the Glue Data Catalog. A
  misconfigured execution role produces a generic
  `AccessDeniedException` at query time that does NOT mention the
  role — engineers chase the S3 bucket policy when the actual blocker
  is the execution role's missing Glue `glue:GetTable` permission.
  Always audit the membership's execution role separately for SPARK
  collaborations.

- **`GetConfiguredTableAnalysisRule` returns DIFFERENT response shapes
  depending on `analysisRuleType`.** The `aggregateConstraints` field
  exists ONLY on `AGGREGATION`-type rules — a `LIST`-type rule
  response has no `aggregateConstraints` key at all. Naive auditors
  flag "missing aggregateConstraints" on LIST rules, which is expected
  behavior, not a defect. Only flag absent `aggregateConstraints` on
  rules of type `AGGREGATION` where the table is used in
  aggregation queries. Check `analysisRuleType` before evaluating
  constraint presence.

## Remediation guidance (ordering principle and per-verdict playbooks)

**Remediation ordering principle:** always prefer member-acceptance
flows and additive privacy controls over destructive membership
operations. Activate privacy controls (DP, aggregate constraints) BEFORE
revoking access — the safe sequence is: (1) snapshot state, (2) enable
DP / add constraints, (3) verify the controls are effective via a test
protected query, (4) only then remove a misconfigured member. This
prevents a window where neither the old nor new controls are in effect.

### For MEMBERSHIP_GAP — INVITED member (Rule M1)

1. Notify the member's account owner to accept the invitation:
   `aws cleanrooms create-membership --collaboration-arn <arn>
   --membership-display-name "<name>" --profile <member-profile>`.
2. If the member is no longer intended, revoke:
   `aws cleanrooms delete-membership --membership-identifier <arn>`.
3. Verify activation:
   `aws cleanrooms list-members --collaboration-id <id>` shows the
   member in `ACTIVE` state.

### For MEMBERSHIP_GAP — REMOVED/LEFT member (Rule M2)

1. Identify which analysis templates and configured tables referenced
   the removed member's data.
2. Either re-invite the member (`CreateMembership`) or update the
   templates to remove the dangling alias references.
3. Re-run the audit to verify no template references remain.

### For MEMBERSHIP_GAP — Solo collaboration (Rule M3)

1. Either invite the missing second party (`CreateMembership` invitation
   via the creator), or document the solo-collaboration as intentional
   (rare; usually indicates a stale proof of concept).
2. If the collaboration is no longer needed, delete it:
   `aws cleanrooms delete-collaboration --collaboration-id <id>`.

### For PRIVACY_RISK — DP disabled (Rule P1)

1. Enable differential privacy on the collaboration:
   `aws cleanrooms update-collaboration --collaboration-identifier <id>
   --differential-privacy-config enabled=true`.
2. Set a per-member epsilon budget appropriate to the collaboration
   lifetime (epsilon does NOT reset).
3. Verify on the next protected query: the response should include
   `additionalAnalyses` > 0.

### For PRIVACY_RISK — Epsilon near-exhausted (Rule P2)

1. Identify the high-spend member via per-member epsilon sum
   (ListProtectedQueries + sum epsilon per member).
2. Either (a) wait for the collaboration to be recreated with a higher
   budget, or (b) pause queries from the high-spend member until the
   collaboration is migrated.
3. CRITICAL — if queries are running with `additionalAnalyses: 0`
   despite DP being enabled, halt the queries immediately. This is an
   active privacy leak — rows are returning without noise.

### For PRIVACY_RISK — Aggregate constraints absent (Rule P3)

1. Add aggregate constraints to each configured table:
   `aws cleanrooms update-configured-table-analysis-rule
   --configured-table-id <id> --analysis-rule-type AGGREGATION
   --analysis-rule-aggregate-columns ...`.
2. Set MIN (typically 10+) and MAX as appropriate to the use case.
3. Verify via a test query that singleton-row returns are blocked.

### For CONFIG_GAP — Invalid analysis template (Rules A1-A4)

1. Identify the specific defect (unresolved parameter, dangling alias,
  invalid column).
2. Recreate the template with the corrected body:
   `aws cleanrooms create-analysis-template --collaboration-id <id>
   --name <new-name> --template-body <corrected-sql>`. Templates are
   immutable — you cannot edit in place.
3. Update any downstream references to the new template.

### For CONFIG_GAP — Output configuration missing (Rule Q1)

1. Configure the protected-query output:
   `aws cleanrooms update-protected-query --output-configuration
   s3={destination=<bucket-prefix>}`.
2. Verify the S3 bucket policy allows the Clean Rooms service principal
   to PutObject for the collaboration's members only.

### For CONFIG_GAP — Untrained configured audience (Rules C1-C3)

1. Fetch the audience-model state:
   `aws cleanroomsml get-configured-audience-model
   --configured-audience-model-arn <arn>`.
2. If `CREATE_FAILED`, inspect the training job logs and recreate:
   `aws cleanroomsml create-configured-audience-model ...`.
3. If `CREATE_IN_PROGRESS`, wait for training completion before
   activating audiences.
4. If the model is `INACTIVE` (training data expired), retrain with
   fresh data.

### For OK

1. No remediation required for the current posture.
2. Recommend enabling `queryLogStatus` if not already enabled (note:
   requires recreation — set at collaboration creation).
3. Recommend periodic re-audit, especially after any member
   transitions to REMOVED or LEFT state.
4. Verify the configured-audience model retraining cadence aligns with
   the source data refresh interval.

## Condition strength reference (Clean Rooms-specific)

| Privacy control | Strength | Reason |
|---|---|---|
| Differential privacy (epsilon > 0) | STRONG | Cryptographic noise added per-query; cumulative budget enforced server-side. Bypassable only by collusion across multiple queries below the noise floor. |
| Aggregate constraints (MIN >= 10) | STRONG | Server-enforced floor on output rows per group. Prevents singleton re-identification regardless of DP. |
| Aggregate constraints (MIN 2-9) | MODERATE | Small MIN values provide weak k-anonymity; combined with DP they are acceptable, alone they are insufficient. |
| Join controls (allowed join columns) | MODERATE | Restricts which columns can be joined; does not directly add noise but limits the query surface. |
| Output controls (allowed output columns) | MODERATE | Restricts which columns can be returned; complements configured-table allowedColumns. |
| Per-query `additionalAnalyses: 0` | NONE | DP noise is OFF for this specific query even if collaboration-level DP is enabled. |
| Configured-table allowedColumns | STRUCTURAL | Not a privacy control per se; defines the column surface. A column not in allowedColumns cannot be selected. |

## Reference: Clean Rooms internals

### Configured table analysis rule types

| Rule type | Allows | Requires aggregateConstraints? |
|---|---|---|
| `LIST` | Row-selection queries only (no aggregation) | No |
| `AGGREGATION` | Aggregation queries (COUNT, SUM, etc.) | Yes (MIN/MAX) |
| `CUSTOM` | User-supplied SQL analysis rule | Depends on rule |

`CUSTOM` is the most flexible and the most privacy-risky — the
member-supplied rule is not validated against aggregate constraints by
default. Flag any `CUSTOM` rule as a review item during audit.

### Protected query lifecycle

`SUBMITTED` → `RUNNING` → `SUCCEEDED` (or `FAILED` / `CANCELLED`).
DP budget check happens at SUBMISSION; epsilon is charged at submission
time, not result materialization. If the per-query epsilon exceeds the
remaining budget, the query is REJECTED with
`ServiceQuotaExceededException`. Epsilon is consumed even for FAILED
queries if noise was added before the failure.

### Clean Rooms ML lifecycle

`CREATE_IN_PROGRESS` → `READY` (or `CREATE_FAILED`) → `INACTIVE`.
The collaboration config shows only the ARN; state is fetched
separately via `cleanroomsml get-configured-audience-model`.

## Recent AWS features (2024-2026)

- **ID mapping tables (2024-2025):** Clean Rooms now supports ID mapping tables for identity resolution across collaborators without exposing raw PII. Auditors should verify that ID mapping tables are properly configured and that the collaboration's privacy budget accounts for mapping queries.
- **Differential privacy enhancements (2024):** Expanded differential privacy controls with per-analysis epsilon tracking and aggregate constraints. Auditors should verify that epsilon budgets are appropriate for the collaboration's query volume and that epsilon spend is monitored.
- **ML model collaboration (2024-2025):** Clean Rooms now supports collaborative ML training. This adds a new audit dimension — verify that model training queries are bounded by the privacy budget and that model artifacts do not leak raw data.
