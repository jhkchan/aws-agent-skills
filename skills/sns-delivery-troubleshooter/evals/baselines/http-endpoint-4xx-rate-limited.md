# Baseline (no-skill) response: http-endpoint-4xx-rate-limited

---

Your endpoint is returning 429 errors which means it's getting too
many requests. SNS will retry failed deliveries, but if the endpoint
keeps returning errors, some messages will be dropped.

Try increasing the endpoint's rate limit or scaling the endpoint to
handle more concurrent requests. You could also look into batching or
reducing the publish rate from the SNS topic.
