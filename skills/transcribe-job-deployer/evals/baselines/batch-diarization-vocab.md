# Baseline (no-skill) — batch-diarization-vocab

> This is the response a model produces **without** the skill
> definition. It provides the basic transcription command but
> misses the custom vocabulary status verification (must be READY
> before referencing), the diarization-specific parameter syntax,
> the SRT/VTT subtitle output flag, the per-second cost estimate,
> and the READY_TO_DEPLOY checklist format. Generated for with-
> skill-vs-baseline comparison.

---

Here's the transcription command:

```bash
aws transcribe start-transcription-job \
  --transcription-job-name meeting-transcription \
  --media MediaFileUri=s3://my-input-bucket/audio/meeting.wav \
  --language-code en-US \
  --output-bucket-name my-output-bucket
```

You can enable speaker labels and add the vocabulary.
