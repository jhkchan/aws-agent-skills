# Eval prompt: redshift-copy-column-mismatch

Diagnose the following Firehose to Redshift delivery failure. Emit
the standard DIAGNOSIS block.

Diagnosis reference: redshift-copy-column-mismatch
Account: 111111111111
Region: us-east-1
Delivery-stream-name: prod-events-to-redshift
Destination: redshift
Cluster: prod-redshift
Table: public.events
Symptom: RedshiftFails

Recent diagnostic output:
- DeliveryToRedshift.Success: 0% for the last 30 min
- Firehose log: COPY command failed
- Redshift stl_load_errors:
  query=12345, err_reason="Extra column(s) specified",
  colname="user_id, event_type, request_time, ip, ua"
  (5 columns in COPY)
- Redshift table public.events has 6 columns: user_id,
  event_type, request_time, ip, ua, processed_at
  (processed_at has DEFAULT CURRENT_TIMESTAMP)
- describe-delivery-stream RedshiftDestinationDescription:
  CopyCommand.DataTableColumns =
  "user_id,event_type,request_time,ip,ua"
- Staging bucket head-bucket: 200 (exists, correct region)
- Redshift cluster role has s3:GetObject on staging bucket

Emit the standard DIAGNOSIS block. Identify the root cause via
Step 7 (RedshiftFails).
