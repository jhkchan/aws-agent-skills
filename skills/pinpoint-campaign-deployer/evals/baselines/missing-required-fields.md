# Baseline (no-skill) response: missing-required-fields

This file captures what a generic assistant produces WITHOUT the
pinpoint-campaign-deployer skill loaded — the contrast that proves
the skill identifies missing required fields (project, channel,
segment, message) and emits a structured PREREQUISITES_MISSING verdict
rather than guessing.

---

Sure! To create a Pinpoint campaign called promo-blast:

1. Go to the Pinpoint console.
2. Select your project.
3. Click Create campaign.
4. Enter the name promo-blast.
5. Choose a channel (email is usually the default).
6. Select a segment.
7. Write your message.
8. Schedule it for immediate send.

Commands:

```
aws pinpoint create-campaign --application-id <your-project-id> --write-campaign-request '{"Name":"promo-blast"}'
```

You'll need to fill in the details like which segment to target and
what message to send. You can do this in the console or via the CLI.

Let me know what kind of promo you want to send and I can help you
write the message.
