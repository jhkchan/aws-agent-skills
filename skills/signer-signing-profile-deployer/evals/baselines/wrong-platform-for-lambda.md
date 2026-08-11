# Baseline (no-skill) — wrong-platform-for-lambda

> This is the response a model produces **without** the skill
> definition. It creates the AWSIoT-platform profile and adds it to
> the Lambda CSC without flagging that Lambda's verifier expects the
> AWSLambda-SHA384-ECDSA platform. Does not emit a
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-baseline
> comparison.

---

Sure:

```bash
aws signer put-signing-profile \
  --profile-name lambda-iot-wrong \
  --platform-id AWSIoT

aws lambda update-code-signing-config \
  --code-signing-config-arn arn:aws:lambda:us-east-1:111122223333:code-signing-config:csc-aaa111222 \
  --allowed-publishers AllowedPublishingProfiles=arn:aws:signer:us-east-1:111122223333:/signing-profiles/lambda-iot-wrong
```

Done.
