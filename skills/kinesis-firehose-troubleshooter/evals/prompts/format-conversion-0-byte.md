# Eval prompt: format-conversion-0-byte

Diagnose the following Firehose data format conversion failure. Emit
the standard DIAGNOSIS block.

Diagnosis reference: format-conversion-0-byte
Account: 111111111111
Region: us-east-1
Delivery-stream-name: prod-events-parquet
Destination: s3 (extended, with format conversion)
Glue database: prod_db, table: events
Symptom: FormatConversionFails

Recent diagnostic output:
- DeliveryToS3.Success: 100% (objects landing)
- aws s3api head-object on the latest 5 objects:
  ContentLength: 0 for all 5
- Athena query on the table returns 0 rows
- aws glue get-table prod_db events: columns show
  userId, eventType, requestTime (CamelCase)
- Sample input record (from S3 error backup):
  {"user_id":"u123","event_type":"click","request_time":"2026-08-10T10:00:00Z"}
  (snake_case keys)
- DataFormatConversionConfiguration: Enabled=true,
  InputFormatConfiguration.Deserializer=OpenXJsonSerDe
  (CaseInsensitive NOT set)

Emit the standard DIAGNOSIS block. Identify the root cause via
Step 5 (FormatConversionFails).
