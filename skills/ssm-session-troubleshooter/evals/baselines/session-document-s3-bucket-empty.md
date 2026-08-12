# Baseline (no-skill) response: session-document-s3-bucket-empty

---

Your sessions work but audit logs aren't showing up in S3. Check
the SSM-SessionManagerRunShell document — it probably doesn't have
the S3 bucket configured. You can update the document to point at
your `ssm-session-output-useast1` bucket.

Also verify the bucket policy allows the instance role to write.
Since CloudWatch Logs is receiving the stream, the session itself
is healthy, so the issue is just the S3 output configuration.
