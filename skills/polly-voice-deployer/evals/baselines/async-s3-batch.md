# Baseline (no-skill) — async-s3-batch

> This is the response a model produces **without** the skill
> definition. It provides the basic async synthesis command but
> misses the S3 IAM permissions verification (Polly needs
> s3:PutObject on the bucket), the task lifecycle monitoring
> (queued → inProgress → completed), the cost estimate for
> long-form pricing ($100/1M chars vs $16/1M for neural), and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

You can use the async API for long text:

```bash
aws polly start-speech-synthesis-task \
  --engine long-form \
  --voice-id Joanna \
  --output-format mp3 \
  --sample-rate 24000 \
  --output-s3-bucket-name my-polly-output \
  --text "$(cat article.txt)"
```

The output should appear in S3.
