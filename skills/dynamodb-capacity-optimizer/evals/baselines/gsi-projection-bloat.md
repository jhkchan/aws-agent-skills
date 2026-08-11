# Baseline (no-skill) response: gsi-projection-bloat

This file captures what a generic assistant produces WITHOUT the
dynamodb-capacity-optimizer skill loaded.

---

You have 3 GSIs all using ALL projection, which means every attribute
is duplicated in each index. That's 300 GB of extra storage. You can
reduce this by changing the projection type.

Since gsi-by-category and gsi-by-date are rarely queried (200 and 50
queries per day), you might want to consider dropping them or changing
them to KEYS_ONLY projection. gsi-by-status is used more frequently so
you might want INCLUDE projection with just the attributes you need.

You'll need to delete and recreate the GSIs with the new projection
type since DynamoDB doesn't let you modify an existing GSI's projection.
