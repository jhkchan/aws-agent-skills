# Baseline (no-skill) — phone-number-claim

> This is the response a model produces **without** the skill
> definition. It claims the phone number but does not verify the
> region matches the instance (a US toll-free number does not work
> in EU instances), does not check the per-instance phone-number
> quota, and does not emit the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Claim the number:

```bash
aws connect claim-phone-number \
  --instance-id inst-abc123 \
  --target-arn "arn:aws:connect:us-east-1:123456789012:instance/inst-abc123" \
  --phone-number +18005551234
```

Done.
