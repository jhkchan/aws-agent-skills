# Baseline (no-skill) response: concurrent-snapshot-automated-manual-collision

---

The `ConcurrentSnapshotExecutionException` means another snapshot
is already running when your manual job fires. OpenSearch only
allows one snapshot at a time per cluster. Try moving your manual
snapshot to a different time, or just retry it after the automated
snapshot finishes.

You can check `_snapshot/_status` to see if a snapshot is in
progress before starting yours.
