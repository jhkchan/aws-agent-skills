# Eval prompt: delivery-to-s3-kms-gap

Diagnose the following Kinesis Data Firehose delivery failure. Emit
the standard DIAGNOSIS block (SYMPTOM, ROOT_CAUSE, EVIDENCE,
LAYER_CHECK, FIX, VERIFICATION, VERDICT, NEXT_STEP,
ESCALATION_PATH).

Diagnosis reference: delivery-to-s3-kms-gap
Account: 111111111111
Region: us-east-1
Delivery-stream-name: prod-events-delivery
Destination: s3 (extended)
Symptom: DeliveryToS3Fails

Recent diagnostic output:
- CloudTrail PutObject events for the Firehose role show
  errorMessage: "AccessDenied: kms:GenerateDataKey on
  arn:aws:kms:us-east-1:111111111111:key/abc123"
- aws kms get-key-policy: Statement Principal =
  {"AWS": "arn:aws:iam::111111111111:root"} only
  (no firehose.amazonaws.com service principal)
- aws s3api head-bucket: returns 200 (bucket exists)
- aws s3api get-bucket-location: us-east-1 (matches Firehose region)
- CloudWatch DeliveryToS3.Success: 0% for the last 30 min
- CloudWatch logging: Enabled on the destination

Emit the standard DIAGNOSIS block.
