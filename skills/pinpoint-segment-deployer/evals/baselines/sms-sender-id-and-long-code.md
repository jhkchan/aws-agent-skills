# Baseline (no-skill) — sms-sender-id-and-long-code

> This is the response a model produces **without** the skill
> definition. It recommends a sender ID for US SMS (sender IDs are NOT
> supported in the US), misses the 10DLC campaign-registry
> requirement for US long codes, and does not emit the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the SMS campaign:

```bash
aws pinpoint update-sms-channel \
  --application-id app-abc123 \
  --sms-channel-request ShortCode="MyBrand"
```

Then create the campaign targeting us-mobile-users.
