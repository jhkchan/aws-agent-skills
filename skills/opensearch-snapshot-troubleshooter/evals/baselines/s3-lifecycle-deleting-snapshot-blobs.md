# Baseline (no-skill) response: s3-lifecycle-deleting-snapshot-blobs

---

Your older snapshots are failing to restore because the snapshot
data is missing from S3. The `SnapshotMissingException` suggests
the snapshot files were deleted. Check whether anything is deleting
objects from the bucket — possibly a lifecycle rule or another
process.

You may need to take new snapshots going forward since the old ones
appear to be gone. Consider enabling versioning on the bucket to
protect against accidental deletes.
