# Baseline (no-skill) response: delivery-gap-bucket-deleted

---

The configuration recorder is running and looks healthy. The delivery
channel is configured but its status shows FAILURE with error
NO_SUCH_BUCKET, which means the S3 bucket it was pointing to has been
deleted.

You should either recreate the S3 bucket or update the delivery channel
to point to a different bucket that exists.

The Config rules and conformance pack look fine.
