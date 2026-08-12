# Eval: s3-export-lake-formation

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — S3_SNAPSHOT export to subscriber bucket, Lake Formation registration, Data Catalog table creation, IAM role with s3:PutObject

## Prompt

Subscribe to Data Exchange data set ds-abc12345
(S3_SNAPSHOT type, CSV market data). Subscription sub-def67890
is ACTIVE. The latest revision r-ghi11122 is FINALIZED with
5 assets. Export to S3 bucket my-analytics-bucket in us-east-1.
IAM role dx-export-role has s3:PutObject on the bucket.
Integrate with Lake Formation: register the S3 location and
create Data Catalog table market_data in database
data_exchange_db. Tags: Environment=production,
DataSource=market-data.
