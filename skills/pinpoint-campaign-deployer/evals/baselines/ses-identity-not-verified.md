# Baseline (no-skill) response: ses-identity-not-verified

This file captures what a generic assistant produces WITHOUT the
pinpoint-campaign-deployer skill loaded — the contrast that proves
the skill catches the unverified SES identity (which would cause zero
sends silently) that a generic assistant would miss.

---

Here's your deployment plan for the Pinpoint email campaign:

1. Create the email template with your promo content.
2. Create the campaign targeting seg-all.
3. Schedule it for immediate send.

Commands:

```
aws pinpoint create-email-template --email-template-request '{"TemplateName":"promo-email","Subject":"Special Promo","HtmlPart":"..."}'
aws pinpoint create-campaign --application-id app-abc123 --write-campaign-request '{"Name":"promo","SegmentId":"seg-all","MessageConfiguration":{"EmailTemplate":{"Name":"promo-email"}},"Schedule":{"StartTime":"IMMEDIATE"}}'
```

The campaign should start sending right away. Since you have 50000
subscribers, it will take a few minutes to send all the emails.

Let me know if you need to adjust anything.
