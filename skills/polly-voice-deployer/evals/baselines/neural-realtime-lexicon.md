# Baseline (no-skill) — neural-realtime-lexicon

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the lexicon
> verification step (lexicon must be uploaded before synthesis
> references it), the per-character cost estimate, the voice-
> engine compatibility check, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Here's the Polly synthesis command:

```bash
aws polly synthesize-speech \
  --engine neural \
  --voice-id Joanna \
  --output-format mp3 \
  --sample-rate 24000 \
  --text "Welcome to AWS. Your EC2 instance is ready." \
  output.mp3
```

That should give you the audio file.
