# Error Handling — Polly Voice Deployer

Error-handling deep dives moved out of the SKILL.md body. Loaded on demand.


## Error handling

### Synthesis returns no pause despite `<break>` tag
- The engine is neural, long-form, or generative. `<break>` only
  works with the standard engine. Switch to standard engine, or
  remove `<break>` and use `<prosody rate="slow">` for timing
  adjustment on neural.

### Async task fails with S3 access denied
- Polly does not have `s3:PutObject` permission on the output
  bucket. Add a bucket policy granting Polly write access, or use
  the Polly service-linked role.

### Voice not found error
- The voice ID is not valid for the selected engine. Check
  `describe-voices --engine <engine>` to find supported voices.
  Some voices are standard-only.

### Lexicon not found error
- The lexicon was not uploaded in the current region, or the name
  is misspelled. Upload with `put-lexicon` and verify with
  `list-lexicons`.

### Speech marks are empty
- The `OutputFormat` was not set to `json`, or `SpeechMarkTypes`
  was not specified. Speech marks require a separate call with
  `OutputFormat=json` and at least one mark type.

### PCM output is garbled
- The sample rate may be incompatible with PCM. PCM only supports
  8000 and 16000 Hz. Switch to a supported rate or change the
  output format to mp3.
