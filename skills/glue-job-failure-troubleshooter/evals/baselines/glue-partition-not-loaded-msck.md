# Baseline (no-skill) response: glue-partition-not-loaded-msck

---

Your Glue job is reading 0 records from the Data Catalog table even
though S3 has data. The table might be pointing to the wrong S3 path.
Check the StorageDescriptor.Location to make sure it matches where
your data actually lives.

You could also try running a Glue crawler on the S3 path to update the
table schema. If the data was written by Firehose, the format might
not match what the table expects.
