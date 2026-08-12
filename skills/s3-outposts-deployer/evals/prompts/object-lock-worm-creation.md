# Eval: object-lock-worm-creation

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — object lock enabled at creation, COMPLIANCE mode, WORM

## Prompt

Create an S3 bucket on Outpost op-0xyz789abc with object lock
enabled in COMPLIANCE mode. Bucket name: worm-outpost-bucket.
I need the endpoint in subnet subnet-xyz789 with SG sg-worm-s3.
Default retention 365 days. Account: 123456789012. Region
us-east-1. Tags: Compliance=SEC17.
