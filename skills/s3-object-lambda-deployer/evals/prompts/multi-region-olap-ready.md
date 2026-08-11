# Eval prompt: multi-region-olap-ready

Design a deployment plan for a multi-region S3 Object Lambda Access
Point. Emit the standard VERDICT block (OBJECT_LAMBDA_SPEC, VERDICT,
CHECKLIST, VERIFICATION_COMMANDS).

Requirements:

- OLAP name: global-pii-olap (one per region, same name)
- Regions: us-east-1, eu-west-1, ap-southeast-2
- Per-region source buckets: prod-data-us, prod-data-eu, prod-data-ap
  (all baseline healthy — BPA, SSE-KMS, versioning)
- Per-region standard APs: dlake-ap-us, dlake-ap-eu, dlake-ap-ap
  (all exist, each with AP policy allowing the region's Lambda role)
- Per-region IAM roles: olap-exec-us, olap-exec-eu, olap-exec-ap
  (all trust=s3-object-lambda.amazonaws.com, all include
  WriteGetObjectResponse)
- Per-region transform Lambdas: pii-redact-us, pii-redact-eu,
  pii-redact-ap (all python3.12, all use WriteGetObjectResponse)
- Reserved concurrency: 50 per region per Lambda
- Operations: GetObject + HeadObject
- Client routing: Route 53 latency-based routing across the 3 OLAP ARNs
- Account: 111111111111

Additional context: the team has users in North America, Europe, and
APAC. Each region has its own source bucket with region-local data.
Route 53 directs clients to the nearest OLAP. There is no cross-region
replication requirement — each OLAP transforms only its region's data.
