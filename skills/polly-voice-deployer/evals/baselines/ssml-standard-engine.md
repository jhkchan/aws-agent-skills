# Baseline (no-skill) — ssml-standard-engine

> This is the response a model produces **without** the skill
> definition. It provides the SSML synthesis command but does not
> verify that the standard engine is the correct choice for full
> SSML tag support (break, emphasis). A naive model might suggest
> neural instead, which would silently drop the break and emphasis
> tags. Also misses the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

Here's the SSML synthesis:

```bash
aws polly synthesize-speech \
  --voice-id Matthew \
  --output-format mp3 \
  --sample-rate 24000 \
  --text-type ssml \
  --text '<speak>Hello <break time="500ms"/> <emphasis level="strong">world</emphasis> <prosody rate="slow">slow text</prosody></speak>' \
  output.mp3
```

You could also use the neural engine for better quality.
