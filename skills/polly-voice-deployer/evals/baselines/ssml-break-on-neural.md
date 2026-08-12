# Baseline (no-skill) — ssml-break-on-neural

> This is the response a model produces **without** the skill
> definition. It synthesizes with neural engine and SSML break/
> emphasis tags without flagging that these tags are silently
> ignored by the neural engine. The synthesis succeeds but the
> pauses and emphasis do not appear in the output audio. Does not
> emit a PREREQUISITES_MISSING verdict. Generated for with-skill-
> vs-baseline comparison.

---

Here's the neural synthesis with SSML:

```bash
aws polly synthesize-speech \
  --engine neural \
  --voice-id Joanna \
  --output-format mp3 \
  --sample-rate 24000 \
  --text-type ssml \
  --text '<speak>Welcome. <break time="500ms"/> This is <emphasis level="strong">important</emphasis>.</speak>' \
  output.mp3
```

Neural gives you the best quality.
