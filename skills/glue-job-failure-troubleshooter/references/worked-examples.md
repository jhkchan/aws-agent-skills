# Worked Examples — Glue Job Failure Troubleshooter

Secondary worked examples moved verbatim from SKILL.md (progressive disclosure — load on demand).

## Worked example — Bookmark partition-key mismatch

```text
TARGET: etl-hourly-events (JobRunId: jr_def456)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The job has --job-bookmark-option=job-bookmark-enable but
  reprocesses all data on every run. The script was updated 3 days ago
  to change partition_keys from ["event_date"] to
  ["event_date","event_hour"]. The bookmark state references the old
  single-key schema and cannot compare; the job treats every run as a
  full reload (Step 6).
LAYER: GLUE_BOOKMARK_CORRUPTED
EVIDENCE:
  - Symptom: CloudWatch Logs show "Processing 2,400,000 records" on
    every run; the source grows by ~100,000/hour, so a bookmarked run
    should process ~100,000, not 2.4M.
  - Probe: aws glue get-job-run returns
    Arguments["--job-bookmark-option"]="job-bookmark-enable".
  - Probe: the script uses partition_keys=["event_date","event_hour"];
    get-job-bookmark references only "event_date".
  - Passing: table exists; partitions loaded; G.2X workers (not memory).
REMEDIATION:
  1. Reset the bookmark: aws glue reset-job-bookmark --job-name etl-hourly-events
  2. Re-run with --job-bookmark-option=job-bookmark-enable (first run
     after reset reprocesses all — expected).
  3. Verify the second run processes only ~100,000 new records.
CONFIRM: Before resetting: "CONFIRM: About to reset the bookmark for
  etl-hourly-events. The next run will reprocess all data. Proceed?"
```

