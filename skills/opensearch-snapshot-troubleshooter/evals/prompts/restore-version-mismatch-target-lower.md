# Eval prompt: restore-version-mismatch-target-lower

Diagnose the OpenSearch snapshot restore failure. Walk the symptom-
driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: restore of snapshot `snap-2026-08-05` from repository
`dr-repo` into `dev-logs-cluster` returns 400 with
`version_not_supported`. The snapshot was created on a 2.13 domain;
the target domain is on 2.11.

```text
Source domain: prod-logs-cluster (OpenSearch_2.13)
Target domain: dev-logs-cluster (OpenSearch_2.11)
Repository: dr-repo (registered on both domains, same S3 bucket,
  same snapshot role)
Snapshot: snap-2026-08-05
Snapshot engine_version: 2.13.0 (read via
  _snapshot/dr-repo/snap-2026-08-05)

Restore command issued:
  curl -X POST
    "https://$DEV_ENDPOINT/_snapshot/dr-repo/snap-2026-08-05/_restore"
    -d '{"indices": "logs-*"}'

Restore response (400):
  {
    "error": {
      "type": "snapshot_restore_failure_exception",
      "reason": "version_not_supported: The snapshot was created
        with version [2.13.0] which is higher than this version
        [2.11.0]"
    }
  }

Target cluster state: green, has free disk space, no alias
  conflicts on logs-* indices.
```

Restore cannot proceed because the target engine version is lower
than the source. Identify the root-cause layer and the fix path.
