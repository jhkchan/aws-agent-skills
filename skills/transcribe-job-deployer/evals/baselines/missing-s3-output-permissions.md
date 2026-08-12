# Baseline (no-skill) — missing-s3-output-permissions

> This is the response a model produces **without** the skill
> definition. It starts the transcription job without verifying S3
> output bucket permissions. The job will fail because Transcribe
> cannot write the transcript without s3:PutObject permission. Does
> not emit a PREREQUISITES_MISSING verdict. Generated for with-skill-
> vs-baseline comparison.

---

Here's the transcription command:

```bash
aws transcribe start-transcription-job \
  --transcription-job-name my-transcription \
  --media MediaFileUri=s3://input-bucket/audio.wav \
  --language-code en-US \
  --output-bucket-name output-bucket
```

The transcript should appear in the output bucket.
