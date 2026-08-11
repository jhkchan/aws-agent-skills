# Baseline (no-skill) response: journey-multistep-deploy

This file captures what a generic assistant produces WITHOUT the
pinpoint-campaign-deployer skill loaded — the contrast that proves
the skill adds structure (journey activity graph DAG validation,
CONDITIONAL_SPLIT true/false branching, WAIT activity ISO 8601
duration format, and END activity requirement).

---

To create a multi-step onboarding journey in Pinpoint:

1. Go to the Pinpoint console and select your project.
2. Navigate to Journeys and click Create journey.
3. Add the activities:
   - Send welcome email
   - Wait 24 hours
   - Check if user opened the app
   - If no, send a nudge email
4. Set the entry criteria to your new users segment.

Commands:

```
aws pinpoint create-journey --application-id app-abc123 --write-journey-request '{"Name":"onboarding-flow"}'
```

The journey can be configured in the console with the drag-and-drop
editor. Just add the steps and connect them. The wait step should be
set to 24 hours.

You can set the journey to DRAFT mode first and then enable it after
reviewing.
