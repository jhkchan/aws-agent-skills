# Eval: dynamodb-export-crawl

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — DynamoDB table exported to S3 in DYNAMODB_JSON format, crawler reads from S3 export path

## Prompt

Create a Glue Crawler for a DynamoDB table exported to S3.
The table UserEvents was exported to
s3://my-ddb-exports/dynamodb/UserEvents/ in DYNAMODB_JSON
format. Database dynamo_db. Full crawl. Weekly schedule.
Tags: Environment=production, Source=dynamodb.
