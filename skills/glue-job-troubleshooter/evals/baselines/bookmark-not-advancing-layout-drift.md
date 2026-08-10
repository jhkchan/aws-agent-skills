# Baseline (no-skill) response: bookmark-not-advancing-layout-drift

This file captures what a generic assistant produces WITHOUT the
glue-job-troubleshooter skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT + CATEGORY, layout-drift
recognition, reset-job-bookmark one-time cost flag, IAM probe).

---

It sounds like your job is reprocessing data even though bookmarks are
enabled. You may need to reset the bookmark. Try running
`aws glue reset-job-bookmark --job-name hourly-events-rollup` and then
re-run the job. Bookmarks can get stuck sometimes.

Also verify that your job script is using the right partition columns.
