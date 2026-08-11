# Eval: tape-gateway-vtl

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Tape Gateway, VTL with virtual tapes, Glacier tape pool with governance retention

## Prompt

Deploy a Tape Gateway in us-east-1. Gateway name:
backup-tape-gateway. Activation key: TAPEK-99999-VTLXX-88888-YYYYY.
Cache: 200 GB. Upload buffer: 400 GB. Create a tape pool named
GlacierPool with GLACIER storage class and 365-day governance
retention. Create 10 virtual tapes of 1 TB each with barcode prefix
TAPE. Tags: Environment=production, Purpose=backup.
