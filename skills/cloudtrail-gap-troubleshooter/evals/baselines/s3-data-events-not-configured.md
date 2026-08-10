# Baseline (no-skill) response: s3-data-events-not-configured

This file captures what a generic assistant produces WITHOUT the
cloudtrail-gap-troubleshooter skill loaded.

---

CloudTrail doesn't log S3 GetObject events by default. You need to
enable data events for S3. Go to the CloudTrail console, edit your
trail, and under "Data events" select S3 and choose the buckets you
want to log.

Note that enabling data events can increase your CloudTrail costs
significantly because of the volume of S3 API calls. You might want
to scope it to specific buckets.

After enabling, wait about 15 minutes and check if the events appear
in lookup-events or in the S3 bucket.
