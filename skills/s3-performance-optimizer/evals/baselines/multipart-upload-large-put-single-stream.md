# Baseline (no-skill) response: multipart-upload-large-put-single-stream

---

Your S3 upload is slow because of the large file size. Try these steps:

1. Check your network bandwidth to confirm 500 Mbps is achievable.
2. Consider compressing the file before upload.
3. Use multipart upload — the AWS SDK usually does this automatically.
4. If possible, upload from an EC2 instance in the same region.

The 80-second transfer time for a 5 GB file at 500 Mbps is close to
the theoretical limit for a single connection.
