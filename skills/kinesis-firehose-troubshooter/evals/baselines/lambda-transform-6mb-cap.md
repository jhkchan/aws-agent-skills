# Baseline (no-skill) response: lambda-transform-6mb-cap

This file captures what a generic assistant produces WITHOUT the
kinesis-firehose-troubleshooter skill loaded - the contrast that
proves the skill adds structure (5-layer health check,
deterministic VERDICT, fix CLI, verification step).

---

Your Lambda transform is dropping batches because the response
payload is too large. The Firehose log shows "Response payload
exceeds 6 MB." This happens because the enrichment is expanding
each record significantly.

You should reduce the buffer size in the Firehose processing
configuration so fewer records are batched per Lambda
invocation, or compress / trim the records in the handler.
