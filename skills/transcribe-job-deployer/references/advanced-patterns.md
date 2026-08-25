# Advanced Patterns — Transcribe Job Deployer

Edge-case catalog and recent-feature notes moved verbatim from SKILL.md. Loaded on demand.

## Step 1 — Supported audio formats

**Supported audio formats:**

| Format | Extension | Notes |
|---|---|---|
| FLAC | .flac | Lossless, preferred for accuracy |
| MP3 | .mp3 | Compressed, widely used |
| MP4 | .mp4 | Video container (audio extracted) |
| WAV | .wav | Uncompressed |
| WebM | .webm | Web container |
| AMR | .amr | Telephony |
| OGG | .ogg | Compressed |
| M4A | .m4a | Apple audio |

## Step 2 — Auto-identify caveats

**Auto-identify caveats:**
- Adds processing time.
- May pick the wrong language for short clips or mixed-language
  audio.
- Supports a defined set of languages (not all languages support
  auto-identify).
- Medical transcription does NOT support auto-identify.

## Step 7 — Medical transcription

| Feature | Standard Transcription | Medical Transcription |
|---|---|---|
| API | `start-transcription-job` | `start-medical-transcription-job` |
| Model | General-purpose | Medical-specialty (PrimaryCare, etc.) |
| Auto-language-identify | Supported | NOT supported |
| Custom language model | Supported | NOT supported |
| PII redaction | Supported | Supported (PHI-specific) |
| Output formats | JSON, TXT, SRT, VTT | JSON only |

```bash
# Start a medical transcription job
aws transcribe start-medical-transcription-job \
  --medical-transcription-job-name my-medical-job \
  --media MediaFileUri=s3://bucket/medical-dictation.wav \
  --language-code en-US \
  --specialty PRIMARYCARE \
  --type DICTATION \
  --output-bucket-name my-output-bucket \
  --region us-east-1
```

**Specialty options:** `PRIMARYCARE`, `CARDIOLOGY`, `NEUROLOGY`,
`ONCOLOGY`, `RADIOLOGY`, `UROLOGY`.

**Type options:** `DICTATION` (physician dictation) or
`CONVERSATION` (physician-patient conversation).

## Step 13 — Recent features

**Recent AWS features (2023-2026):**

- **Custom language model v2 (2024-2025):** Improved training
  pipeline with better convergence and support for larger training
  corpora. Faster training times and higher accuracy gains for
  domain-specific terminology.

- **PII redaction entity expansion (2023-2024):** Additional PII
  entity types supported for content redaction, including
  PASSPORT_NUMBER and expanded ADDRESS variants for international
  compliance.

- **Subtitle generation for all job types (2023-2024):** SRT and
  VTT subtitle output now available for all batch transcription
  jobs, not just standard transcription.

- **Medical transcription specialty expansion (2023-2024):**
  Additional medical specialties supported, including enhanced
  accuracy for clinical conversation (physician-patient dialogue)
  beyond traditional dictation.

- **CloudWatch per-feature dimensions (2024-2025):** Granular
  metrics by transcription type (standard, medical, streaming) and
  by feature (diarization, CLM) for precise cost attribution.

- **Auto-language-identify accuracy improvements (2024-2025):**
  Expanded language coverage and improved accuracy for mixed-
  language audio in auto-identify mode.
