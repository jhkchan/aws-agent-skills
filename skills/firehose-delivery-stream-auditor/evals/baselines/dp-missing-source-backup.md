# Baseline (no-skill) response: dp-missing-source-backup

This file captures what a generic assistant produces WITHOUT the
firehose-delivery-stream-auditor skill loaded.

---

Dynamic partitioning is enabled with a JQ expression extracting the
`.tenant` field, with errors routed to a dedicated ErrorOutputPrefix.
Encryption is KMS-based and buffering is at 64 MiB.

The stream is using `S3BackupMode: Disabled` which is fine if you're
confident in the JQ expression. You could add a source backup for
defensive purposes but it's not strictly required.
