# Eval: ssml-standard-engine

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — standard engine selected for full SSML support (break, emphasis, prosody, phoneme), voice Matthew en-US, MP3 24000 Hz

## Prompt

Configure Amazon Polly to synthesize speech using SSML. The SSML
uses <break time="500ms"/>, <emphasis level="strong">, and
<prosody rate="slow"> tags. Voice: Matthew (en-US). Output: MP3
at 24000 Hz. Text includes phoneme tags for IPA pronunciation.
Region us-east-1. Tags: Environment=production, UseCase=ivr.
