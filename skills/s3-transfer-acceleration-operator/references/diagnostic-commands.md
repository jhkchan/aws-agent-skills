# S3 Transfer Acceleration Operator — Diagnostic and Pre-flight Commands

Pre-flight safety checks run before any remediation CLI, moved verbatim from SKILL.md. See the SKILL.md pre-flight gate for the bucket-metadata commands.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any
  `put-bucket-accelerate-configuration` call, emit:
  `CONFIRM: About to <enable/disable> Transfer Acceleration on
  bucket <name> (region <region>). <Impact>. Proceed? (yes/no)`. Do
  NOT execute until the operator confirms.

- **Capture pre-state for audit.** Before any acceleration change:
  `aws s3api get-bucket-accelerate-configuration --bucket <name>
  --output json > /tmp/<name>-accel-pre-$(date +%s).json`.

- **Verify no in-flight multipart uploads (for disable).**
  `list-multipart-uploads --bucket <name>` must return 0 active
  uploads using the accelerate endpoint before disabling.

- **Verify DNS compatibility.** The bucket name must be
  DNS-compatible for the accelerate endpoint to work. Check for
  underscores, uppercase letters, or consecutive dots.

- **Verify cost acceptance.** Surface the estimated acceleration
  cost (per-GB rate x estimated volume) before enabling. Track
  actual cost via CloudWatch BytesUploaded and Cost Explorer.

- **Prefer multipart upload for large objects.** When acceleration
  is enabled, always use multipart upload for files > 100 MB.
  Parallel parts over accelerated connections maximize throughput.
  Use CRC32C checksums for end-to-end integrity.

