# Error Handling — Pinpoint Journey Deployer

Error-handling deep dives moved out of the SKILL.md body. Loaded on demand.


## Error handling

### Journey participants not entering (event-based)
- The triggering event is not being recorded. Verify endpoints are
  calling `put-events` with the correct event type and that the event
  name in StartCondition matches exactly.

### Journey participants not entering (segment-based)
- The segment is empty at start time. Verify segment membership with
  `get-segment`. Segments are evaluated at StartTime.

### Conditional split never branches YES
- The event is not being recorded DURING the journey, or event
  attributes do not match the condition. Events before entry do not
  count.

### Messages held too long (quiet time)
- The quiet time window is too broad or the timezone is wrong. Verify
  quiet time hours and journey timezone.

### Custom channel Lambda fails
- The Lambda resource-based permission is missing or scoped to the
  wrong journey ARN. Verify with `aws lambda get-policy`. Check Lambda
  timeout (must complete within 15 seconds).

### Multivariate split percentages error
- Percentages do not sum to 100. Reconfigure branches to sum to 100.
