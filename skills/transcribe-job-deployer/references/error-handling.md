# Error Handling — Transcribe Job Deployer

Failure deep dives moved verbatim from SKILL.md. Loaded on demand.

## Error handling

### Job fails with S3 access denied
- Transcribe does not have permission to read the input audio or
  write to the output bucket. Verify the IAM role or bucket policy
  grants `s3:GetObject` on input and `s3:PutObject` on output.

### Job fails with unsupported audio format
- The audio file is not in a supported format. Convert to FLAC,
  MP3, WAV, or another supported format before uploading.

### Custom vocabulary not found
- The vocabulary was not created or is not in READY state. Create
  the vocabulary and wait for it to reach READY before referencing
  it in a job.

### Diarization and channel identification both enabled
- These are mutually exclusive. Choose diarization for mono audio
  or channel identification for stereo audio. Remove one from the
  configuration.

### PII redaction not working
- PII redaction must be set at job creation time. If the job was
  already started without redaction, the transcript contains PII.
  Re-run the job with `--content-redaction-type PII` enabled.

### Medical transcription fails with auto-identify
- Medical transcription does NOT support auto-language-identify.
  Specify the language explicitly with `--language-code`.

### Custom language model not improving accuracy
- The base model (NarrowBand vs WideBand) may not match the audio
  quality. Ensure NarrowBand is used for telephone audio and
  WideBand for high-quality audio. Also verify the training data
  is representative of the domain.
