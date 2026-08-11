# Baseline (no-skill) response: user-notifications-chat

This file captures what a generic assistant produces WITHOUT the
health-event-automator skill loaded.

---

AWS User Notifications is a managed service that delivers Health events
to Slack, Chime, and Teams without custom Lambda code. You can create a
notification configuration that matches aws.health events and routes
them to your Slack channel.

For more complex automation like DR failover, you can still use
EventBridge with a Lambda function that invokes your DR Step Functions
state machine when an issue event fires.

---

Notes on what the baseline misses:

- No mention of gating the DR trigger behind an impact evaluation — any
  issue event (including single-host degradation) would trigger failover.
- No affected-entity enrichment before the DR trigger.
- No DLQ on the Lambda target.
- No mention that User Notifications delivery lag (~30s) is higher than
  EventBridge direct (~5s).
- No idempotency mechanism.
- No replay testing.
