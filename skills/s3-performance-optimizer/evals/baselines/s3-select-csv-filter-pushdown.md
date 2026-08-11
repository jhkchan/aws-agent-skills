# Baseline (no-skill) response: s3-select-csv-filter-pushdown

---

Your CSV analytics job is slow. Try these steps:

1. Process the CSV in parallel chunks using multiple workers.
2. Convert the CSV to a columnar format like Parquet.
3. Consider using Amazon Athena for serverless querying.
4. Increase the EC2 instance size if the bottleneck is CPU.

The 3-hour runtime for a 100 GB scan is dominated by network transfer
of the full file.
