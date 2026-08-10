# Eval prompt: spark-oom-stage-skew

Diagnose the Glue job failure. Walk the seven-category diagnostic tree
and emit the standard diagnostic block (TARGET, VERDICT, REASON,
CATEGORY, EVIDENCE, REMEDIATION).

JobName: big-join-batch (case spark-oom-stage-skew)
RunId: jr_oom456def789
Region: us-east-1
GlueVersion: 4.0
WorkerType: G.1X
NumberOfWorkers: 10
Timeout: 240

get-job-run output:
  State: FAILED
  ExecutionTime: 23
  ErrorMessage: "Container killed by YARN for exceeding memory limits"

Spark UI stage 7 (join on customer_id) task metrics:
  min=12s, median=45s, max=2h17m
  max/median task bytes ratio = 316x
  One task processed 380 GB (single customer_id "ACME-001")
  Median task processed 1.2 GB

No Python traceback in CloudWatch Logs.
