# Eval: ssml-break-on-neural

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — <break> and <emphasis> tags only work with standard engine; neural silently ignores them

## Prompt

Configure Amazon Polly neural voice synthesis with SSML. Use
voice Joanna (neural engine). The SSML includes
<break time="500ms"/> between sentences and
<emphasis level="strong"> on key terms. Output: MP3 at 24000 Hz.
Region us-east-1. Tags: Environment=production.
