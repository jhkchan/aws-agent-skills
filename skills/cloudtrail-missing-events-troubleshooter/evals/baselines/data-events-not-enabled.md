# Baseline (no-skill) response: data-events-not-enabled

---

You're missing S3 GetObject events from CloudTrail. By default
CloudTrail only captures management events — data events like
GetObject are not included. You need to add a data event selector
for S3 objects.

Run `put-event-selectors` with `DataResources` configured for
`AWS::S3::Object`.
