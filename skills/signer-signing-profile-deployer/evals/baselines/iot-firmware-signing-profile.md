# Baseline (no-skill) — iot-firmware-signing-profile

> This is the response a model produces **without** the skill
> definition. It creates the profile without flagging that AWSIoT is
> NOT valid for Lambda CSC, omits the OTA consumption flow, and does
> not emit the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Sure, here's the profile:

```bash
aws signer put-signing-profile \
  --profile-name iot-firmware-prod \
  --platform-id AWSIoT
```

You can probably add this to your Lambda CSC too if you want code
signing.
