# Baseline (no-skill) — pii-redaction

> This is the response a model produces **without** the skill
> definition. It starts the transcription job without enabling PII
> redaction, meaning the unredacted transcript (containing SSNs,
> credit card numbers, names) is written to S3 in clear text. This
> is a compliance violation. A naive model does not flag that PII
> redaction must be set at job creation time and cannot be applied
> retroactively. Also omits the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Here's the transcription:

```bash
aws transcribe start-transcription-job \
  --transcription-job-name customer-call \
  --media MediaFileUri=s3://fin-input/calls/customer-call.wav \
  --language-code en-US \
  --output-bucket-name fin-output
```

You can manually review the transcript for PII afterward.
