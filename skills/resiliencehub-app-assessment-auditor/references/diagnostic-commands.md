# Diagnostic Commands — Resilience Hub App Assessment Auditor

Pre-flight and pre-remediation command listings moved out of the SKILL.md body. Loaded on demand.


## Live-account pre-flight checks

1. Verify the caller's identity can run
   `resiliencehub:StartAppAssessment` if remediation is intended — most
   read-only auditor roles CANNOT, and re-assessment commands will fail
   with `AccessDeniedException`. Surface this BEFORE the operator approves
   a re-run.
2. Confirm the app version is published
   (`aws resiliencehub describe-app --app-arn <arn>` shows `appVersion`).
   An app with draft changes has unpublished resources; the assessment
   covers only the last published version, not the draft.
3. Snapshot the current assessment list BEFORE any change:
   `aws resiliencehub list-app-assessments --app-arn <arn> --output json >
   /tmp/<app>-assessments-backup-$(date +%s).json`. Assessments are
   immutable once complete, but the "latest" pointer moves when a new
   assessment runs — capture the baseline first.


## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`start-app-assessment`, `publish-app-version`, `put-app-policy`,
  `delete-app-assessment`), the auditor MUST emit:
  `CONFIRM: About to <action> on app <arn> (version <v>). This affects
  <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. This gate
  prevents automated pipelines from silently triggering assessments or
  publishing versions.
- Confirm the app exists and is accessible:
  `aws resiliencehub describe-app --app-arn <arn> --profile <p>` — fail
  closed (skip remediation) if it returns an error.
- Before starting a new assessment, verify the app version is current:
  `aws resiliencehub describe-app --app-arn <arn>` — if
  `evaluationLimitExceeded` is true, resolve the limit before assessing.
- Before publishing a new version, confirm no other version is mid-publish:
  check `describe-app` for `status: Administering`. Publishing over an
  in-flight publish can corrupt the version state.
- Capture the current assessment list for rollback:
  `aws resiliencehub list-app-assessments --app-arn <arn> --output json >
  /tmp/<app>-assessments-$(date +%s).json` BEFORE triggering a new
  assessment. The "latest" pointer moves irreversibly when a new
  assessment starts.
- Prefer additive changes (implement an alarm recommendation) over
  destructive changes (delete an old assessment). Deleting an assessment
  removes historical compliance context — keep old assessments for trend
  analysis.
