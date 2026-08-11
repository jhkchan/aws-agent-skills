# Baseline (no-skill) response: email-campaign-full-security

This file captures what a generic assistant produces WITHOUT the
pinpoint-campaign-deployer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated PRE_CHECKS,
specific STEPS with exact CLIs, expert knowledge of SES verification,
segment resolution, quiet time timezone, A/B holdout percentage
arithmetic, and event stream IAM role requirements).

---

Here's how to set up a Pinpoint email campaign with an A/B test:

1. Make sure your Pinpoint project is set up.
2. Configure the email channel with your SES identity.
3. Create a segment for your premium iOS users.
4. Create two email templates for the A/B test.
5. Create the campaign with the A/B test configuration.

Commands:

```
aws pinpoint create-email-template --email-template-request '{"TemplateName":"subject-a","Subject":"Special offer","HtmlPart":"..."}'
aws pinpoint create-campaign --application-id app-abc123 --write-campaign-request '{"Name":"promo","SegmentId":"seg-premium"}'
```

For the A/B test, you can add multiple treatments in the console. Set
the holdout to 10% and split the rest between your two subject lines.

You should also set up quiet time so you don't send emails at night.

Let me know if you need help with the segment dimensions.
