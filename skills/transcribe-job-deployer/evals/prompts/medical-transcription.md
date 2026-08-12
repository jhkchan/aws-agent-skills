# Eval: medical-transcription

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — medical batch via start-medical-transcription-job, cardiology specialty, DICTATION type, specified language (no auto-identify), medical pricing

## Prompt

Configure Amazon Transcribe Medical to transcribe a physician
dictation audio file from
s3://medical-input/dictations/cardiology-note.wav. Language:
en-US (medical does not support auto-identify). Specialty:
CARDIOLOGY. Type: DICTATION. Output to s3://medical-output.
Region us-east-1. Tags: Environment=production,
UseCase=clinical-dictation, Compliance=HIPAA.
