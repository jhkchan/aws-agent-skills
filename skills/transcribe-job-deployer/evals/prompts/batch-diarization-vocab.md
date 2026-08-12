# Eval: batch-diarization-vocab

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — standard batch job, mono WAV audio, speaker diarization (3 speakers), custom vocabulary company-terms (READY), SRT+VTT subtitles, cost estimate

## Prompt

Configure Amazon Transcribe to transcribe a 1-hour mono WAV
meeting recording from
s3://my-input-bucket/audio/meeting.wav. Language: en-US.
Enable speaker diarization (3 speakers). Use a custom vocabulary
named company-terms (already in READY state) for AWS service
names. Output to s3://my-output-bucket. Need SRT and VTT
subtitles. Region us-east-1. Tags: Environment=production,
UseCase=meeting-transcription.
