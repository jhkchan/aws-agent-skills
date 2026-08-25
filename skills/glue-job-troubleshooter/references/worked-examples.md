# Worked Examples — Glue Job Troubleshooter

Secondary worked examples moved verbatim from SKILL.md (progressive disclosure — load on demand).

## Worked example — JDBC VPC security group

```text
TARGET: orders-etl-job/jr_def789abc012
VERDICT: ROOT_CAUSE_FOUND
REASON: Glue connection nightly-rds-conn uses SG sg-glue123, but the
  database SG sg-rds456 lacks inbound on port 5432 from sg-glue123.
  The TCP SYN was dropped at the database SG.
CATEGORY: JDBC_VPC
EVIDENCE:
  - State=FAILED, ExecutionTime=18, ErrorMessage="VPC Connection error"
  - Failing probe:
    aws ec2 describe-security-groups --group-ids sg-rds456
    → IpPermissions lack port 5432 with sg-glue123 source
  - Passing probes: route table for Glue subnet reaches DB subnet;
    Glue SG has egress to 0.0.0.0/0 on 5432; last successful 3 days ago
REMEDIATION:
  1. Add inbound to database SG:
     aws ec2 authorize-security-group-ingress --group-id sg-rds456 \
       --ip-permissions IpProtocol=tcp,FromPort=5432,ToPort=5432,\
         UserIdGroupPairs=[{GroupId=sg-glue123}]
  2. Add self-referencing rule to Glue SG (idempotent):
     aws ec2 authorize-security-group-ingress --group-id sg-glue123 \
       --ip-permissions IpProtocol=-1,FromPort=-1,ToPort=-1,\
         UserIdGroupPairs=[{GroupId=sg-glue123}]
  3. Verify from a Glue dev endpoint in the same subnet:
     nc -vz orders-db.cluster-abc.us-east-1.rds.amazonaws.com 5432
  4. Re-run:
     aws glue start-job-run --job-name orders-etl-job
```

## Worked example — bookmark stall

```text
TARGET: hourly-events-rollup/jr_xyz987abc321
VERDICT: ROOT_CAUSE_FOUND
REASON: Source layout changed from year=/month= to dt= but the
  bookmark tracks (year, month). The bookmark cannot advance on the
  new layout, so the job reprocesses everything on every run.
CATEGORY: BOOKMARK_STALL
EVIDENCE:
  - Reprocessed_bytes near total source bytes on each run
  - Failing probe:
    aws glue get-job-bookmark --job-name hourly-events-rollup
    → bookmark Args partitionKeys == ["year","month"],
      but source layout is now dt=
  - Passing probes: IAM role has glue:UpdateJobBookmark (Allow);
    --job-bookmark-option=enable
REMEDIATION:
  1. Reset the bookmark (one-time; forces full reprocess once):
     aws glue reset-job-bookmark --job-name hourly-events-rollup
  2. Update the script to read from dt= and set partition_keys=["dt"].
  3. Re-crawl to register dt partitions:
     aws glue start-crawler --name events-crawler
  4. Verify subsequent runs skip processed dt partitions.
```

## Worked example — Spark OOM with data skew

```text
TARGET: big-join-batch/jr_oom456def789
VERDICT: ROOT_CAUSE_FOUND
REASON: Executor OOM in stage 7 (join on customer_id). Spark UI shows
  one task reading 380 GB vs median 1.2 GB — 316x skew. OOM is from
  shuffling the hot key, not DPU shortage.
CATEGORY: SPARK_OOM
EVIDENCE:
  - State=FAILED, ExecutionTime=23, ErrorMessage="Container killed by
    YARN for exceeding memory limits"
  - Failing probe: Spark UI stage 7 — min=12s, median=45s, max=2h17m;
    one task processed 380 GB (single customer_id "ACME-001")
  - Passing probes: NumberOfWorkers=10 (not DPU-starved);
    ExecutionTime=23 < Timeout=240; no Python traceback
REMEDIATION:
  1. Salt the skewed join key:
     hot="ACME-001"
     df_small = df_small.withColumn("join_key",
       when(col("customer_id")==hot,
         concat(col("customer_id"), lit("_"),
           (rand()*8).cast("int")))
       .otherwise(col("customer_id")))
     # Replicate df_big rows 8x for the hot key (see reference)
  2. Raise shuffle partitions before the join:
     spark.conf.set("spark.sql.shuffle.partitions", "2000")
  3. Re-run at the same DPU count (do NOT raise workers yet):
     aws glue start-job-run --job-name big-join-batch
```

## Worked example — NEED_MORE_INFO

```text
TARGET: long-running-extract/jr_qrs654tuv321
VERDICT: NEED_MORE_INFO
REASON: Job RUNNING for 90 minutes against a 60-min SLA, but Spark UI
  was not enabled for this run. Cannot determine whether slowness is
  skew, DPU starvation, or a stuck task.
CATEGORY: UNKNOWN
EVIDENCE:
  - State=RUNNING, ExecutionTime=90, Timeout=180
  - CloudWatch logs show normal progress, no errors
  - Spark UI event log path not configured
REMEDIATION:
  1. Let the current run finish (do NOT cancel; data may be valid).
  2. Enable Spark UI on the job:
     aws glue update-job --job-name long-running-extract \
       --job-update '{"DefaultArguments":{
         "--enable-spark-ui":"true",
         "--spark-event-logs-path":"s3://glue-spark-logs-us-east-1/long-running-extract/"}}'
  3. Add a bucket lifecycle policy on the Spark UI logs (30-day expiry).
  4. Re-run and re-invoke this skill with the new RunId.
```

