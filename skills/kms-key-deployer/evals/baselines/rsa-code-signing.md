# Baseline (no-skill) — rsa-code-signing

> This is the response a model produces **without** the skill definition.
> It creates the RSA key without flagging that asymmetric keys cannot
> auto-rotate, and may forget to scope the key users to Sign/Verify
> only (often granting Encrypt/Decrypt which the key cannot do).

---

```bash
aws kms create-key \
  --key-spec RSA_4096 \
  --usage SIGN_VERIFY \
  --description "Code signing CMK" \
  --policy file://policy.json

aws kms create-alias \
  --alias-name alias/code-signing-cmk \
  --target-key-id <key-id>

aws kms enable-key-rotation --key-id <key-id>
```

Grant the signer-service role kms:Sign and kms:Verify.
