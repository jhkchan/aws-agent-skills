# Worked Examples — Redshift Query Troubleshooter

Secondary worked examples (WLM queue timeout, COPY data format error), the Step 12 INSUFFICIENT_DATA template, and the malformed-input output moved verbatim from SKILL.md. Loaded on demand.

## Pre-flight — INSUFFICIENT_DATA output for malformed input

```text
TARGET: <cluster-id or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context -- at minimum a symptom
  description (the error string or observed behaviour) and either the
  cluster identifier or the query text.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact error message
  or observed symptom, (2) the cluster identifier and database name,
  (3) the query text or query ID, and (4) the table definitions
  (distribution style, sort key) for the tables involved.
```


## Step 12 — INSUFFICIENT_DATA output template

```text
TARGET: <cluster-id>
VERDICT: INSUFFICIENT_DATA
REASON: The available evidence does not conclusively identify a
  single root cause from the diagnostic tree. List the probes already
  executed and their results, and request additional context.
LAYER: UNKNOWN
EVIDENCE:
  - <probes executed and results>
  - <missing information needed>
REMEDIATION: Provide (1) the EXPLAIN output for the failing query,
  (2) the SVV_TABLE_INFO for the tables involved, (3) the
  STL_WLM_QUERY entry for the query, and (4) the exact error message
  from STL_ERROR or the client.
```


## Worked example — WLM queue timeout

```text
TARGET: prod-analytics-cluster, query 67890
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The query was cancelled after waiting 240 seconds in WLM
  service class 8 (Batch queue). The queue has 2 slots and 5
  concurrent queries were submitted simultaneously; only 2 could
  execute. The query's queue_time (240s) exceeds the queue's
  max_execution_time threshold.
LAYER: WLM_QUEUE_TIMEOUT
EVIDENCE:
  - Symptom: query cancelled with "Query 67890 cancelled due to
    queue timeout."
  - Probe: STL_WLM_QUERY shows queue_time = 240s, exec_time = 0s
    (never started executing), state = "cancelled".
  - Probe: STV_WLM_SERVICE_CLASS_CONFIG shows service_class 8 with
    num_query_tasks = 2, max_execution_time = 240000000 (240s).
  - Passing: EXPLAIN plan for the query is optimal (DS_DIST_NONE,
    sort key leveraged); no table locks; the query itself runs in
    3 seconds when it reaches the front of the queue.
REMEDIATION:
  1. Increase the Batch queue slots from 2 to 4:
     (via wlm_json_configuration parameter group update)
  2. Or route heavy analytical queries to a dedicated queue with
    more slots and a higher timeout.
  3. Verify by re-running the batch and checking STL_WLM_QUERY
    queue_time drops below 60s.
CONFIRM: Before modifying WLM config, emit and await:
  "CONFIRM: About to update WLM configuration on
   prod-analytics-cluster. Proceed? (yes/no)"
```


## Worked example — COPY data format error

```text
TARGET: prod-analytics-cluster, COPY command at 14:23 UTC
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The COPY from s3://etl-bucket/daily/orders.csv failed.
  STL_LOAD_ERRORS shows errcode 1204 "Delimiter not found" at line
  1. The data file is pipe-delimited (|) but the COPY command
  specifies DELIMITER ','.
LAYER: COPY_DATA_FORMAT
EVIDENCE:
  - Symptom: COPY returns "stl_load_errors: Delimiter not found"
  - Probe: STL_LOAD_ERRORS shows raw_line =
    "1001|2024-01-15|450.00|shipped", errcode = 1204.
  - Probe: File header confirms pipe delimiter:
    order_id|order_date|amount|status
  - Passing: IAM role has s3:GetObject on the bucket (COPY_IAM_ROLE
    ruled out); file exists and is readable.
REMEDIATION:
  1. Update the COPY command delimiter:
     COPY orders FROM 's3://etl-bucket/daily/orders.csv'
       IAM_ROLE 'arn:aws:iam::111111111111:role/RedshiftETLRole'
       DELIMITER '|' FORMAT CSV;
  2. Or convert the data to comma-delimited before COPY.
  3. Verify by re-running COPY and checking STL_COMMUNICATIONS for
    successful load completion.
```
