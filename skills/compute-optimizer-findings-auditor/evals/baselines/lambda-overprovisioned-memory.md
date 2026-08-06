# Baseline (no-skill) response: lambda-overprovisioned-memory

---

This Lambda function has 2560 MB of memory allocated but is only using
about 400 MB on average. Compute Optimizer recommends reducing to 1280 MB
which would save about $80 per month.

You should reduce the memory allocation to save costs. The function has
plenty of headroom at the current memory level so reducing to 1280 MB
should still give enough room.
