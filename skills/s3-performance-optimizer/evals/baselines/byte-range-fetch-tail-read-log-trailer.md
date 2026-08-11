# Baseline (no-skill) response: byte-range-fetch-tail-read-log-trailer

---

Reading the tail of large S3 objects is slow. Try:

1. Reduce the file size if possible (rotate logs more frequently).
2. Compress the log files before storing in S3.
3. Consider caching the trailer locally after the first read.
4. Use a different storage format that includes an index at the
   beginning.

The 40-second read time is expected for a 5 GB download over a single
TCP connection.
