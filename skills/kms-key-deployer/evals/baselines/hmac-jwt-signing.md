# Baseline (no-skill) — hmac-jwt-signing

> This is the response a model produces **without** the skill definition.
> It creates the HMAC key without flagging that HMAC keys cannot
> auto-rotate, and may grant Encrypt/Decrypt (which an HMAC key cannot
> perform) instead of GenerateMac/VerifyMac.

---

```bash
aws kms create-key \
  --key-spec HMAC_256 \
  --description "JWT signing CMK" \
  --policy file://policy.json

aws kms create-alias \
  --alias-name alias/jwt-signing-cmk \
  --target-key-id <key-id>

aws kms enable-key-rotation --key-id <key-id>
```

Grant the auth-svc role kms:Encrypt, kms:Decrypt on the key.
