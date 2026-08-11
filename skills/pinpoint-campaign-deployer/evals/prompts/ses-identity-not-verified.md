# Eval prompt: ses-identity-not-verified

Design a deployment plan for a Pinpoint email marketing campaign. Emit
the standard VERDICT block.

Requirements:

- Project: app-abc123 (prod-engagement)
- Channel: email (SES identity: marketing.example.com)
- Segment: seg-all (demographic — all subscribed users, 50000 endpoints)
- Template: promo-email (email, Liquid personalization)
- Schedule: IMMEDIATE
- Frequency cap: 3/day

Existing-account context: the SES identity marketing.example.com was
created 10 minutes ago. DNS verification records (TXT for domain
verification and three CNAME records for DKIM) have been added to
Route 53 but have not propagated yet. The identity status is PENDING.

`aws sesv2 get-email-identity --email-identity marketing.example.com`
returns VerificationStatus: PENDING.

The email channel on the Pinpoint project references this identity.
The operator wants to launch the campaign immediately and does not
realize the identity is not yet verified.
