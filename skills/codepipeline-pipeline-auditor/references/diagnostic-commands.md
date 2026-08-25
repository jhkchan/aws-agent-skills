# Diagnostic Commands — CodePipeline Pipeline Auditor

Load-on-demand pre-flight and diagnostic CLI moved verbatim from SKILL.md.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`UpdatePipeline`, `DisableStageTransition`, `EnableStageTransition`,
  `DeletePipeline`), the auditor MUST emit:
  `CONFIRM: About to <action> on pipeline <name> in account <account>. This
  affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **Snapshot the pipeline before modification.** Capture the current
  definition for rollback:
  `aws codepipeline get-pipeline --name <name> --output json > /tmp/<name>-backup-$(date +%s).json`
  Pipeline definitions are not versioned — `UpdatePipeline` replaces the entire
  structure atomically with no undo.

- **Verify the pipeline exists and is accessible:**
  `aws codepipeline get-pipeline --name <name>` — fail closed (skip
  remediation) if it returns an error.

- **Before enabling a disabled transition**, confirm the operator understands
  that enabling the transition allows queued executions to advance
  immediately. If the stage was disabled during an incident, verify the
  incident is resolved before re-enabling.

- **Before adding a CMK to the artifact store**, verify the pipeline role has
  `kms:Encrypt`, `kms:Decrypt`, and `kms:GenerateDataKey` on the new key.
  Adding an encryptionKey without granting the pipeline role KMS permissions
  causes all executions to fail with `AccessDenied` at the first artifact
  staging step.

- Prefer additive changes (add an approval stage, add a CMK) over destructive
  changes (remove a stage, delete a pipeline) — additive changes are
  reversible and do not risk breaking existing deployment workflows.
