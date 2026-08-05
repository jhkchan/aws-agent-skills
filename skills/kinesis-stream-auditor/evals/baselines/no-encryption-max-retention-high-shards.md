# Baseline (no-skill) response: no-encryption-max-retention-high-shards

This file captures what a generic assistant produces WITHOUT the
kinesis-stream-auditor skill loaded.

---

This stream has several issues. First, it is not encrypted — EncryptionType
is NONE. Second, the retention period is 8760 hours (365 days), which is
the maximum. With 50 shards, this is going to be very expensive. Third,
at 50 shards you are approaching the account-level shard quota of 500.

You should enable encryption and reduce the retention period. The 365-day
retention on 50 shards will incur significant extended-retention charges.

The enhanced monitoring looks good with all key metrics enabled. There is
1 consumer attached.
