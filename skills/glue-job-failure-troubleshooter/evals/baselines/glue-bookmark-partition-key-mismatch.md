# Baseline (no-skill) response: glue-bookmark-partition-key-mismatch

---

Your Glue job is reprocessing all data every run even though
bookmarking is enabled. This is a common issue with Glue bookmarks.
Try disabling and re-enabling the bookmark option. You can also try
setting --job-bookmark-option to job-bookmark-pause and then back to
job-bookmark-enable.

If that doesn't work, check whether the bookmark state was corrupted.
You might need to delete the bookmark table in DynamoDB (Glue stores
bookmark state internally) and start fresh.
