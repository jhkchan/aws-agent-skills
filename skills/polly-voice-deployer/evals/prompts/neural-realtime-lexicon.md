# Eval: neural-realtime-lexicon

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — neural engine, voice Joanna en-US, MP3 24000 Hz, lexicon company-terms referenced, real-time synthesize-speech mode, per-character cost estimate

## Prompt

Configure Amazon Polly to synthesize a greeting message using
the neural engine. Voice: Joanna (en-US, Female). Output format:
MP3 at 24000 Hz. Use a lexicon named company-terms (already
uploaded) so that "AWS" and "EC2" are pronounced correctly.
The text is: "Welcome to AWS. Your EC2 instance is ready."
This is a real-time synthesis for a web application. Region
us-east-1. Tags: Environment=production, UseCase=greeting.
