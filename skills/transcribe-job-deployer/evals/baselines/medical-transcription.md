# Baseline (no-skill) — medical-transcription

> This is the response a model produces **without** the skill
> definition. It uses the standard transcription API instead of the
> separate medical API (start-medical-transcription-job), misses
> the specialty and type parameters, and does not flag that medical
> transcription does not support auto-language-identify. Also omits
> the READY_TO_DEPLOY checklist format. Generated for with-skill-
> vs-baseline comparison.

---

Transcribe the dictation:

```bash
aws transcribe start-transcription-job \
  --transcription-job-name cardiology-note \
  --media MediaFileUri=s3://medical-input/dictations/cardiology-note.wav \
  --language-code en-US \
  --output-bucket-name medical-output
```

That should handle the medical content.
