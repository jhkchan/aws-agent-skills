# Advanced Patterns — Audit Manager Assessment Auditor

Load-on-demand deep dives moved verbatim from SKILL.md: Step-0 expert knowledge, edge cases, remediation playbooks, operational gotchas, recent features.

## Step 0: Expert knowledge — non-obvious Audit Manager behaviours that change classification

These behaviours are easy to misjudge without operational Audit Manager
experience. Each changes a verdict if ignored.

- **`NOT_ASSESSED` is a collection signal, not a failure signal.** A
  control in `NOT_ASSESSED` means Audit Manager never evaluated it — the
  data source (Config or CloudTrail) did not produce the inputs the
  control's evidence finder expects. Treating `NOT_ASSESSED` the same as
  `FAIL` produces a LOW_COMPLIANCE verdict and prescribes "fix the failing
  control," when the correct remediation is "repair the data source." The
  30% threshold on NOT_ASSESSED (Step 1b) exists to route these cases to
  INCOMPLETE_EVIDENCE instead.

- **Audit Manager cannot collect without AWS Config recording in EVERY
  in-scope account × region.** Config-based controls read configuration
  snapshots from the Config recorder. If the recorder is `OFF` or
  `notRecording` in any account listed in `scope.awsAccounts`, every
  Config-based control in that account returns `NOT_ASSESSED`. The
  assessment remains `ACTIVE` — there is no alarm. Recorders are also
  per-region: Audit Manager does not auto-fan-out across regions, so
  every region in the compliance perimeter must have its own recorder
  `recording: true`, or regional controls silently return `NOT_ASSESSED`.
  Verify with `aws configservice describe-configuration-recorder-status`
  per account × region.

- **CloudTrail management events are the second silent dependency.**
  API-based controls read CloudTrail management events. A trail that logs
  only data events (S3/Lambda), or a trail that was deleted, produces
  `NOT_ASSESSED` for every API-based control. Management-event logging
  must be ON. Verify with `aws cloudtrail describe-trails` and confirm
  `IncludeManagementEvents: true` on at least one active trail per region
  in scope. For org-scoped assessments, only a trail with
  `IsOrganizationTrail: true` delivers management events to member
  accounts — a per-account trail in the management account does NOT
  satisfy the dependency for delegated members.

- **Cross-account delegations silently stall when the member account has
  not enabled Audit Manager.** `list-delegations` returning
  `IN_PROGRESS` for more than 7 days almost always means the delegated
  account has not registered with Audit Manager (no
  `AWSServiceRoleForAuditManager` service-linked role) or has been
  removed from the organization. A delegation cannot be force-completed
  from the administrator side — remediation is "fix the member account",
  not "retry the API". Treat a stalled delegation older than the
  assessment's `creationTime` as evidence of a missing-member break.

- **Compliance % is `PASS / total controls` (NOT_ASSESSED counts against
  you).** The Audit Manager console computes compliance as the fraction of
  controls with response `PASS` over the total control count. Controls in
  `NOT_ASSESSED`, `UNDER_REVIEW`, `MANUAL`, and `FAIL` all count as
  non-compliant in the denominator. A 50% compliance score may mean "50%
  FAIL, 50% PASS" (a real LOW_COMPLIANCE case) OR "50% PASS, 50%
  NOT_ASSESSED" (a data-source break). Read the response distribution,
  not just the percentage.

- **`MANUAL` controls require human attestation and never auto-resolve.**
  A control with response `MANUAL` is non-automatable — a human must
  upload evidence and mark it PASS/FAIL. If the assessment has many
  `MANUAL` controls in `UNDER_REVIEW`, the compliance % is structurally
  capped until a human acts. A high `MANUAL` + `UNDER_REVIEW` count with
  no `defaultProcessOwners` configured is a CONFIG_GAP (no one is
  designated to close them).

- **An INACTIVE (stopped) assessment retains its evidence but freezes its
  compliance score.** `status: INACTIVE` means Audit Manager stopped
  collecting. The last compliance % is preserved in the metadata and
  still displayed. `lastUpdated` stops advancing. An operator reading the
  dashboard sees a number and may treat it as live. The remedy is either
  reactivate (`update-assessment-status --status ACTIVE`) or formally
  retire the assessment and start a new one — never report against a
  frozen score.

- **Deleting an assessment is NOT the same as stopping it.** A deleted
  assessment's evidence is permanently removed within 90 days. A stopped
  (INACTIVE) assessment's evidence is preserved. When an operator says
  "we stopped the assessment," verify whether `status: INACTIVE` (evidence
  safe) or the assessment is absent from `list-assessments` (evidence
  gone). Do not recommend deletion as remediation without confirming no
  compliance period depends on the retained evidence.

- **Delegations are per-assessment evidence-collection requests to linked
  accounts.** `list-delegations` returns delegations with `status`
  `IN_PROGRESS`, `COMPLETE`, or `FAILED`. A delegation `IN_PROGRESS` for
  more than 7 days on an otherwise-ACTIVE assessment means the delegated
  account has not returned evidence — a scoped INCOMPLETE_EVIDENCE
  condition. A `FAILED` delegation is an immediate collection break.

- **`defaultProcessOwners` is the human-review pipeline.** Audit Manager
  settings' `defaultProcessOwners` lists the IAM principals designated to
  review and approve `UNDER_REVIEW` evidence. When empty, `UNDER_REVIEW`
  controls accumulate with no owner — the assessment runs but its
  human-attested dimension stalls. This is a CONFIG_GAP, not a compliance
  finding.

- **`kmsKey` in settings encrypts assessment reports and evidence-finder
  data at rest.** When unset, Audit Manager falls back to AWS-owned keys
  — you lose customer-managed key control and break the encryption-
  ownership chain that most frameworks (SOC 2 CC6.1, PCI 3.5/3.6) require.
  This is a CONFIG_GAP.

- **`defaultAssessmentReportsDestination` gates report generation.**
  Without an S3 bucket + prefix in settings, `generate-assessment-report`
  fails. A compliance program that cannot produce reports is a CONFIG_GAP.

- **Assessment scope is `awsAccounts` × `awsServices`.** An empty
  `awsAccounts` means the assessment audits only the Audit Manager
  administrator account. An empty `awsServices` means all services (broad
  scope). For an Org-wide compliance program, `awsAccounts` must cover
  every member account; a subset produces an INCOMPLETE_EVIDENCE verdict
  because the compliance picture does not cover the estate.

- **`list-assessment-control-insights-by-control-domain` is the
  domain-level view.** When the per-control response distribution is not
  available in the snapshot, this API returns `controlInsights` per
  domain with `evidenceCount` and `complianceScore`. A domain with
  `evidenceCount: 0` on an ACTIVE assessment is a scoped
  INCOMPLETE_EVIDENCE signal for that domain.

- **Resolving conflicting conditions — the worst verdict wins, never
  average.** Multiple findings often co-occur (e.g., a stopped
  assessment that also has FAIL% > 25% AND a missing KMS key). The
  VERDICT line is the *single* highest-priority finding (Step 1 > 2 > 3 >
  4), never a blend. Report ALL findings; only the VERDICT collapses to
  the worst. Do NOT suppress a CONFIG_GAP finding because
  INCOMPLETE_EVIDENCE fired — the operator fixes both in one pass, and
  the settings gap will silently degrade the next period once the
  assessment is reactivated.

- **Audit Manager end-of-service lifecycle.** AWS has signalled Audit
  Manager end-of-service. An active assessment on a service in
  end-of-service still produces evidence today, but the compliance program
  must plan a migration path (manual evidence collection or an
  alternative). Flag lifecycle as advisory context in REMEDIATION; do NOT
  let it override the data-driven verdict.

## Edge-case handling

- **ACTIVE assessment created < 24 hours ago.** Evidence collection has
  not completed its first cycle. A high NOT_ASSESSED% here is EXPECTED,
  not a data-source break. Do NOT fire Step 1b if `creationTime` is less
  than 24 hours ago — emit an advisory note and skip to Step 3. The
  compliance number is not yet meaningful.

- **Mixed response distribution (borderline).** If PASS% is 58% (just
  under 60%) and NOT_ASSESSED% is 28% (just under 30%), both thresholds
  are narrowly missed. Classify as CONFIG_GAP only if a Step 3 setting is
  missing; otherwise classify as OK with a borderline advisory. Do NOT
  round into LOW_COMPLIANCE or INCOMPLETE_EVIDENCE — the thresholds are
  strict boundaries.

- **MANUAL-heavy framework.** Some frameworks (e.g., a custom GRC
  framework) may have > 50% MANUAL controls by design. These are
  structurally `UNDER_REVIEW` until a human attests. Do NOT treat
  UNDER_REVIEW as NOT_ASSESSED. If `defaultProcessOwners` is set and the
  MANUAL controls are recent, this is OK. If `defaultProcessOwners` is
  empty AND MANUAL/UNDER_REVIEW > 30%, classify as CONFIG_GAP (no review
  pipeline), not INCOMPLETE_EVIDENCE.

- **Settings vs assessment-level overrides.** An assessment may carry its
  own `assessmentReportsDestination` that overrides the settings default.
  Check BOTH — if settings has one but the assessment does not, the
  settings default applies (OK). If neither has one, it is a CONFIG_GAP.

- **Single-account Org.** If `scope.awsAccounts` has exactly one account
  and the org also has exactly one account (standalone, not Org-joined),
  there is no scope gap. Step 1d only fires when the scope is a strict
  subset of a multi-account org.

- **Delegation COMPLETE but evidenceInsufficient.** A delegation marked
  COMPLETE does not guarantee sufficient evidence — the delegated account
  may have returned partial data. If `evidenceCount` per domain is 0 on a
  COMPLETE delegation, treat as a scoped INCOMPLETE_EVIDENCE finding under
  Step 1c.

## Remediation guidance (playbooks per verdict)

### For INCOMPLETE_EVIDENCE — stopped assessment (Step 1a)

1. Determine whether the stop was intentional (e.g., framework retired) or
   accidental. Check `lastUpdated` age.
2. If unintentional, reactivate:
   `aws auditmanager update-assessment-status --assessment-id <id> --status ACTIVE --region <r>`.
3. After reactivation, wait one full collection cycle (~24h) before
   re-reading the compliance %. The first cycle repopulates evidence.
4. If the stop was intentional, retire the assessment formally and migrate
   to a new assessment with the current framework version.

### For INCOMPLETE_EVIDENCE — data-source break (Step 1b)

1. Verify AWS Config in EVERY in-scope account:
   `aws configservice describe-configuration-recorder-status`. If
   `recording: false`, restart:
   `aws configservice start-configuration-recorder --configuration-recorder-name default`.
2. Verify CloudTrail management-event logging in EVERY in-scope region:
   `aws cloudtrail describe-trails`. Confirm at least one trail has
   `IncludeManagementEvents: true` and is logging. If not, create or
   update a multi-region management-event trail.
3. After repair, wait one collection cycle (~24h) for Audit Manager to
   re-evaluate the NOT_ASSESSED controls. Re-run
   `aws auditmanager get-assessment --assessment-id <id>` and re-audit.

### For INCOMPLETE_EVIDENCE — outstanding delegation (Step 1c)

1. List delegations:
   `aws auditmanager list-delegations --assessment-id <id> --region <r>`.
2. For each `IN_PROGRESS` delegation older than 7 days, contact the
   delegated account owner. Re-send if needed:
   the delegation cannot be force-completed from the administrator side.
3. For `FAILED` delegations, review the failure reason and re-create the
   delegation after resolving the underlying permission/connectivity issue.

### For INCOMPLETE_EVIDENCE — scope gap (Step 1d)

1. Update the assessment scope to include all org member accounts:
   `aws auditmanager update-assessment --assessment-id <id> --scope
   awsAccounts='<json>'`. Use
   `aws organizations list-accounts` to enumerate the full membership.
2. Re-evaluate after the next collection cycle.

### For LOW_COMPLIANCE (Steps 2a/2b)

1. Identify the FAIL controls and their control domains. Use
   `aws auditmanager list-assessment-control-insights-by-control-domain
   --assessment-id <id>` to find the weakest domains.
2. For each FAIL control, review the collected evidence in the Audit
   Manager console and remediate the underlying AWS resource (e.g.,
   enable encryption, restrict a security group, add an IAM condition).
3. After remediation, wait for the next collection cycle to re-evaluate.
   Audit Manager will re-test the control and update the response.
4. For FAIL controls that are false positives (e.g., a control that tests
   for a setting that is enforced upstream), document the exception in the
   assessment report rather than suppressing the control.

### For CONFIG_GAP (Step 3)

1. Set KMS key (customer-managed):
   `aws auditmanager update-settings --kms-key arn:aws:kms:<region>:<acct>:key/<id>`.
2. Set SNS topic:
   `aws auditmanager update-settings --sns-topic arn:aws:sns:<region>:<acct>:<topic-name>`.
   Ensure the topic policy permits `auditmanager.amazonaws.com` to publish.
3. Set assessment reports destination:
   `aws auditmanager update-settings --default-assessment-reports-destination
   s3://<bucket>/<prefix>`. Ensure the bucket policy permits Audit Manager
   to write.
4. Set default process owners:
   `aws auditmanager update-settings --default-process-owners
   roleArns=<arn1>,<arn2>`. Designate at least one reviewer principal.

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit (monthly) to catch Config/CloudTrail
   regressions before they invalidate a compliance period.
3. Recommend generating an assessment report at the close of each
   compliance period to formalise the evidence.

## Reference — operational gotchas (NOT in AWS docs)

Deep expert detail referenced from [Step 0b](#step-0b-operational-gotchas-summary--full-detail-in-reference).
These are silent failure modes, API quirks, and cost traps encountered in
production Audit Manager estates.

- **`AWSServiceRoleForAuditManager` SLR is auto-created ONLY at account
  registration, never re-created by the service.** If an admin manually
  deletes the SLR from a member account (e.g., via IAM console cleanup),
  every subsequent delegation to that member silently stalls at
  `IN_PROGRESS` — there is no alarm, no event, and the administrator-side
  API cannot force completion. Verify with
  `aws iam get-role --role-name AWSServiceRoleForAuditManager --profile
  <member>` BEFORE re-sending a delegation; absence explains 7-day+
  stalls. Re-create with
  `aws iam create-service-linked-role --aws-service-name auditmanager.amazonaws.com`.

- **`complianceScore` from the insights API uses a DIFFERENT denominator
  than the console's overall compliance %.**
  `list-assessment-control-insights-by-control-domain` returns a 0-100
  `complianceScore` that EXCLUDES `MANUAL` and `UNDER_REVIEW` controls
  from the denominator, while the assessment's overall compliance %
  (computed from `controlSets[].controls[].response`) INCLUDES them. The
  two can disagree by 10-20 points on MANUAL-heavy frameworks (ISO 27001,
  custom GRC). Always recompute compliance% from the raw response
  distribution; never cross-multiply or substitute the insights score.

- **Framework version immutability — assessments pin at creation time.**
  An assessment captures the framework's control sets at the moment of
  creation; subsequent edits to the parent framework do NOT propagate. A
  compliance program that updated its framework to add new controls will
  see existing assessments continue to audit the OLD control set. Detect
  by diffing the assessment's `framework.id` against the current
  framework revision. Re-baselining requires creating a new assessment
  and migrating the compliance period — there is no in-place upgrade.

- **Evidence storage cost trap — INACTIVE does not mean free.** Audit
  Manager stores collected evidence in a service-managed S3 bucket;
  storage charges accrue per GB-month and continue even when the
  assessment is `INACTIVE`. Only `delete-assessment` stops the storage
  charge, and deletion is irreversible after 90 days. A quarterly review
  of `INACTIVE` assessments older than two compliance periods should flag
  them as deletion candidates. This is an OPEX finding — surface it in
  REMEDIATION, not in VERDICT.

- **`assessment.state` is deprecated but still returned by older SDK
  versions.** Always read `status`. If the snapshot only carries `state`,
  map `state: ACTIVE → status: ACTIVE` and emit a deprecation note in
  FINDINGS — never silently trust `state` for irreversible decisions.

- **API quirk — `get-assessment` and the insights API report different
  control counts.** `get-assessment` returns the authoritative
  `controlSets[].controls[]` array; the insights API aggregates by domain
  and may omit controls whose `response` is `NOT_ASSESSED` (they appear
  as `evidenceCount: 0`). When computing NOT_ASSESSED% for Step 1b,
  ALWAYS use `get-assessment`'s raw distribution — the insights API
  understates the denominator and can mask a Step 1b break.

- **Cross-service latency — Config changes take 5-25 minutes to
  propagate to Audit Manager control evaluation.** After repairing a
  stopped Config recorder, the affected controls do NOT flip from
  `NOT_ASSESSED` to `PASS/FAIL` immediately. The next Audit Manager
  collection cycle runs on its scheduled interval (default ~24h). Wait
  one full cycle before re-reading compliance% — re-auditing during the
  propagation window produces a false `INCOMPLETE_EVIDENCE`.

## Recent AWS features (2024-2026)

No significant recent feature launches affecting the audit surface as of 2026-08. Audit Manager's core functionality (assessments, frameworks, delegations, evidence collection) has been stable with no new configuration fields or security settings that change the audit logic.
