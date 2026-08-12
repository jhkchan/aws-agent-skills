# Eval: api-asset-live-access

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — API asset accessed live (NOT exported to S3), authentication via Data Exchange signing keys, rate-limiting noted

## Prompt

Access API asset from Data Exchange data set ds-api456.
Subscription sub-api789 is ACTIVE. The latest revision
r-api111 has an API asset (REST endpoint at
https://api.provider.com/v1/marketdata). The API provides
real-time market data. Authentication is via Data Exchange
signing keys. Tags: Environment=production, AccessMode=live.
