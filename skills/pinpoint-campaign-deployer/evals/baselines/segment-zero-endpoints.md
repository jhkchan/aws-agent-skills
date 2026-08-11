# Baseline (no-skill) response: segment-zero-endpoints

This file captures what a generic assistant produces WITHOUT the
pinpoint-campaign-deployer skill loaded — the contrast that proves
the skill catches the 0-endpoint segment resolution (which would cause
zero sends silently) that a generic assistant would miss.

---

Here's how to set up your SMS promotional campaign:

1. Make sure the SMS channel is configured with your origination
   number.
2. Create the SMS template.
3. Create the campaign targeting your VIP Android segment.

Commands:

```
aws pinpoint create-sms-template --sms-template-request '{"TemplateName":"vip-promo-sms","Body":"Hi {{UserAttributes.FirstName}}, special VIP offer!"}'
aws pinpoint create-campaign --application-id app-abc123 --write-campaign-request '{"Name":"vip-promo","SegmentId":"seg-vip-android-users","MessageConfiguration":{"SMSMessage":{"MessageBody":"VIP offer"}},"Schedule":{"StartTime":"IMMEDIATE"}}'
```

The campaign will send SMS messages to all your VIP Android users in
the AP Southeast region. Make sure your spend limit is high enough for
the number of messages.

Let me know if you need help with anything.
