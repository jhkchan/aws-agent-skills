---
description: Provision an Amazon Pinpoint journey with production-grade defaults (event-based vs segment-based entry, conditional splits, multivariate A/B splits, wait activities, holdout, quiet time, journey limits, custom Lambda channel, schedule). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create pinpoint journey"
  - "deploy pinpoint journey"
  - "pinpoint journey"
  - "journey conditional split"
  - "journey multivariate split"
  - "journey wait activity"
  - "journey quiet time"
  - "journey holdout"
  - "journey schedule"
  - "journey limits"
  - "custom channel lambda"
  - "journey analytics"
  - "event-based journey"
  - "segment-based journey"
  - "ab test journey"
routes_to: pinpoint-journey-deployer
---

# /aws:deploy-pinpoint-journey

Activate the `pinpoint-journey-deployer` skill and provision an Amazon
Pinpoint journey with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Entry strategy (event-based vs segment-based)
2. Send message activities (email, SMS, push, in-app)
3. Conditional split (yes/no based on event attributes)
4. Multivariate split (random percentage for A/B testing)
5. Wait activity (duration or absolute time)
6. Holdout (control group suppression)
7. Journey schedule (start, end, timezone)
8. Quiet time (off-hours hold — NOT cancel)
9. Journey limits (dailyCap, maxEndpointSend, totalParticipantCap)
10. Rate limits and channel throughput
11. Custom channel (Lambda webhook)
12. Journey analytics and conversion tracking

## When to use

- You need to create a multi-step Pinpoint journey.
- You are building an abandoned cart recovery or onboarding flow.
- You need conditional splits based on user events.
- You want to A/B test message variants with a holdout.
- You need quiet time for off-hours suppression.
- You need journey limits for cost control.
- You need a custom Lambda channel for non-native destinations.

## When NOT to use

- **Single-message campaigns** — use `deploy-pinpoint-campaign` for
  one-shot broadcasts without multi-step flow.
- **Segment creation** — use `deploy-pinpoint-segment` to build the
  audience before referencing it in a journey.
- **Channel configuration** — email/SMS/push channel setup is project-
  level, not journey-level.

## How to invoke

### Slash command

```
/aws:deploy-pinpoint-journey
```

Then provide: project ID, journey name, entry strategy, activity list,
split conditions, wait durations, quiet time config, journey limits,
schedule, and channel details.

### Natural language

Any of these routes to the same skill:

- "create a Pinpoint journey for abandoned cart recovery"
- "set up a multi-step onboarding journey"
- "configure a conditional split in my journey"
- "add quiet time to my Pinpoint journey"
- "A/B test my journey with a holdout"
- "wire a custom Lambda channel to my journey"

### CLI routing

```bash
node cli/bin/cli.js route "create a pinpoint journey"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Pinpoint
journeys. The output checklist feeds into verification pipelines and
downstream analytics skills.

## Example

```
You: /aws:deploy-pinpoint-journey

     Create a Pinpoint journey named AbandonedCartRecovery in
     project app-xyz789. Event-based entry on cart_abandoned.
     Conditional split checking purchase_completed. Quiet time
     10pm-8am UTC. Daily cap 50000.

Skill:
  PINPOINT_JOURNEY: AbandonedCartRecovery (journey-abc123) | project: app-xyz789
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Entry strategy: Event-based (event: cart_abandoned)
    [✓] Conditional splits: CheckPurchase evaluating purchase_completed
    [✓] Quiet time: 22:00–08:00 MON-FRI (HOLDS, not cancels)
    [✓] Journey limits: dailyCap=50000, maxEndpointSend=3
  VERIFICATION_COMMANDS:
    aws pinpoint describe-journey --application-id app-xyz789 --journey-id journey-abc123
```

## References

- Skill definition: `skills/pinpoint-journey-deployer/SKILL.md`
- Activities and splits guide: `skills/pinpoint-journey-deployer/references/activities-and-splits.md`
- Schedule and limits guide: `skills/pinpoint-journey-deployer/references/schedule-and-limits.md`
- Eval suite: `skills/pinpoint-journey-deployer/evals/evals.json`
