# Baseline (no-skill) — speech-marks-lipsync

> This is the response a model produces **without** the skill
> definition. It provides the speech marks command but misses the
> critical insight that speech marks are a SEPARATE request from
> the audio (two calls needed), does not note that the marks and
> audio must use the same engine/voice/text/sample-rate for
> alignment, and omits the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Generate speech marks like this:

```bash
aws polly synthesize-speech \
  --engine neural \
  --voice-id Joanna \
  --output-format json \
  --speech-mark-types '["viseme","word"]' \
  --text "Hello world" \
  marks.json
```

And the audio:

```bash
aws polly synthesize-speech \
  --engine neural \
  --voice-id Joanna \
  --output-format mp3 \
  --text "Hello world" \
  output.mp3
```
