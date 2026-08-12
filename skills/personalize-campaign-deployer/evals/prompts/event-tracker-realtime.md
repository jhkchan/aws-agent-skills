# Eval: event-tracker-realtime

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — event tracker created, tracking-id, Lambda PutEvents handler, one-tracker-per-group constraint noted

## Prompt

Deploy an event tracker for the retail-recs dataset group in
us-east-1
(arn:aws:personalize:us-east-1:123456789012:dataset-group/retail). I
need a Lambda that calls PutEvents for click events on item pages.
Role arn:aws:iam::123456789012:role/PersonalizeEventLambdaRole.
