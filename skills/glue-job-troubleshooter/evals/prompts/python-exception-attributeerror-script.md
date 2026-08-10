# Eval prompt: python-exception-attributeerror-script

Diagnose the Glue job failure. Walk the seven-category diagnostic tree
and emit the standard diagnostic block (TARGET, VERDICT, REASON,
CATEGORY, EVIDENCE, REMEDIATION).

JobName: nightly-sales-aggregation
  (case python-exception-attributeerror-script)
RunId: jr_abc123def456
Region: us-east-1
GlueVersion: 4.0
WorkerType: G.1X
NumberOfWorkers: 5
Timeout: 60

get-job-run output:
  State: FAILED
  ExecutionTime: 42
  ErrorMessage: "No ErrorReason"

CloudWatch Logs filter (filter-pattern "Traceback"):
  Traceback (most recent call last):
    File "tmp/script.py", line 47, in <module>
      df = df.withColumn('revenue', col('price') * col('qty'))
    AttributeError: 'NoneType' object has no attribute '_jvc'

Source: Glue Data Catalog table analytics_prod.sales_raw.
Last crawler run: 6 hours ago. Table row count in S3: 0.
