# Eval prompt: wlm-queue-timeout

Diagnose the Redshift query cancellation for the following cluster. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Redshift query was cancelled with "Query 67890 cancelled due
to queue timeout." The query was submitted to the Batch queue (service
class 8) along with 4 other queries simultaneously. Only 2 queries
could execute (2 slots); the rest waited. The query never started
executing before the 240-second timeout.

```text
Cluster: rs-redshift-wlm-queue
Database: analytics_db
Query ID: 67890
Queue: Batch (service_class 8)

STL_WLM_QUERY for query 67890:
  service_class: 8
  queue_time: 240000000 (240s)
  exec_time: 0
  state: cancelled

STV_WLM_SERVICE_CLASS_CONFIG (service_class 8):
  num_query_tasks: 2
  max_execution_time: 240000000 (240s)

The query itself runs in 3 seconds when it reaches the front of
the queue (verified on a separate run).
```

The query spent 240 seconds waiting in the queue and was cancelled
before it ever started executing (exec_time = 0). This is a WLM queue
contention problem, not a query performance problem.
