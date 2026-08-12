# Baseline (no-skill) — vocabulary-and-filter

> This is the response a model produces **without** the skill
> definition. It applies the custom vocabulary but misses the
> vocabulary filter (or applies only one), does not verify both
> are in READY state, and does not specify the filter mode. Also
> omits the READY_TO_DEPLOY checklist format. Generated for with-
> skill-vs-baseline comparison.

---

Here's the transcription with vocabulary:

```bash
aws transcribe start-transcription-job \
  --transcription-job-name call-001 \
  --media MediaFileUri=s3://calls-input/recordings/call-001.flac \
  --language-code en-US \
  --settings VocabularyName=support-terms \
  --output-bucket-name calls-output
```

You can add a filter too if needed.
