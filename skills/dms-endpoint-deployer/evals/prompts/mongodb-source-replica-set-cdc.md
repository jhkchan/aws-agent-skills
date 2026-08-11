# Eval: mongodb-source-replica-set-cdc

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — MongoDB source with replica set requirement noted, change streams CDC, NestingLevel=ONE, ExtractDocId=true

## Prompt

Create a DMS source endpoint for MongoDB at
mongo-prod.example.com port 27017, us-east-1. Replica set
rs0. CDC via change streams. NestingLevel=ONE, ExtractDocId=true,
DocsToInvestigate=50. SSL mode require. Replication instance
rep-instance-prod. Tags: Environment=production, Engine=mongodb.
