---
name: transcribe-job-deployer
description: 'Deploys Amazon Transcribe configurations with production defaults: transcription job types (batch from S3 via start-transcription-job async, real-time streaming), language identification vs specified language, custom vocabulary (custom word pronunciation), vocabulary filter (mask/remove unwanted words), speaker identification (diarization), channel identification (stereo), medical transcription (MedicalTranscriptionJob), custom language model (domain-specific accuracy boost), content identification and redaction (PII masking), output formats (JSON, TXT, SRT, VTT) to S3, CloudWatch metrics monitoring, and pricing per second of audio. Emits a READY_TO_DEPLOY checklist with verification commands. Use when configuring Amazon Transcribe, transcribing audio from S3, enabling. Triggers: start transcription job, transcribe audio to text, speaker diarization, custom vocabulary transcribe, vocabulary filter, medical transcription job, transcribe pii redaction, custom language model, transcribe pricing per second.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with transcribe access and s3 read on input bucket + s3 PutObject on output bucket. Works with Terraform aws_transcribe_* resources and CloudFormation custom resources for Transcribe configurations.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AI/ML
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, transcribe, stt, cloudops, deploy, ai-ml, provisioning, diarization, vocabulary, pii-redaction, medical-transcription
  dependencies: aws-orchestrator
  keywords: aws, transcribe, speech to text, transcription, diarization, cloudops, deploy, provisioning, custom vocabulary, vocabulary filter, medical transcription, pii redaction, custom language model, pricing per second
  when_to_use: Invoke when the user wants to configure Amazon Transcribe for speech-to-text transcription, run batch transcription jobs from S3, enable speaker diarization, create custom vocabularies for domain-specific terms, filter unwanted words, redact PII from transcripts, run medical transcription, deploy custom language models for improved accuracy, or select output formats (JSON, TXT, SRT, VTT). Do NOT invoke for Amazon Polly (text-to-speech), Amazon Lex (conversational bots), or Amazon Comprehend (NLP text analysis).
---

# Transcribe Job Deployer

An AWS CloudOps agent skill that deploys Amazon Transcribe speech-
to-text configurations with correct defaults. The skill walks the
operator through batch transcription (start-transcription-job from
S3) vs real-time streaming, language identification vs specified
language, custom vocabulary creation and application, vocabulary
filtering (mask/remove), speaker diarization, channel
identification for stereo audio, medical transcription, custom
language models for domain-specific accuracy, content
identification and redaction (PII), output format selection (JSON,
TXT, SRT, VTT), CloudWatch monitoring, and pricing per second of
audio, captures all transcription parameters, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

start transcription job, transcribe audio to text, speaker
diarization, custom vocabulary transcribe, vocabulary filter,
medical transcription job, transcribe PII redaction, custom
language model, transcribe pricing per second.

## STRICT output contract

When this skill is invoked with a Transcribe deployment request
(start a transcription job, configure diarization, create a
custom vocabulary, set up PII redaction, run medical
transcription, deploy a custom language model, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `TRANSCRIBE_JOB:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of
the response. This contract is what assertion-based evals and
downstream deployment pipelines rely on; deviating from the
literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before deployment |
| Step 1 — Batch transcription (start-transcription-job) | Async S3-based transcription |
| Step 2 — Language: identification vs specified | Language handling |
| Step 3 — Custom vocabulary | Domain-specific terms |
| Step 4 — Vocabulary filter | Unwanted word handling |
| Step 5 — Speaker identification (diarization) | Multi-speaker audio |
| Step 6 — Channel identification (stereo) | Multi-channel audio |
| Step 7 — Medical transcription | Clinical content |
| Step 8 — Custom language model | Domain accuracy boost |
| Step 9 — Content identification and redaction (PII) | Compliance / privacy |
| Step 10 — Output formats (JSON, TXT, SRT, VTT) | Transcript encoding |
| Step 11 — CloudWatch metrics | Monitoring |
| Step 12 — Pricing per second of audio | Cost budgeting |
| Step 13 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/vocabulary-and-filtering.md | Vocabulary + filter detail |
| references/diarization-and-redaction.md | Diarization + redaction detail |

## Mindset

**One-line takeaway:** Amazon Transcribe converts speech to text.
Batch jobs read audio from S3 and write transcripts to S3
asynchronously. Speaker diarization separates speakers in the
output. Custom language models improve accuracy for domain-specific
vocabulary but add cost. Content redaction masks PII before the
transcript is written — the PII never appears in the output.

Three misconceptions dominate Transcribe misdeployment at
provisioning time:

- **"Custom vocabulary and custom language model are the same
  thing."** They are not. A custom vocabulary tells Transcribe how
  to pronounce and render specific words (acronyms, domain terms).
  A custom language model is an ML model trained on domain-specific
  text that improves overall transcription accuracy. Custom
  vocabularies are free to apply; custom language models require
  training data, training time, and add cost per minute of audio.

- **"Speaker diarization and channel identification are
  interchangeable."** They are not. Speaker diarization uses ML to
  identify and label different speakers in a mono audio stream
  (speaker 0, speaker 1, etc.). Channel identification assumes the
  audio is stereo (two channels) and labels each channel separately
  (ch_0, ch_1). Diarization is approximate (ML-based); channel
  identification is exact (hardware-based). Use channel
  identification when the audio is stereo and channel-separated.

- **"PII redaction removes PII from the transcript after
  transcription."** It does not. PII redaction is applied DURING
  transcription — the identified PII is masked (replaced with
  `[PII]`) before the transcript is written to S3. The original PII
  never appears in the output. This is critical for compliance
  (HIPAA, GDPR) because the unredacted transcript is never created.

## Configuration dependency graph (novel heuristic)

Transcribe configurations are NOT independent. Language must be
specified or auto-identified. Custom vocabularies must be created
before the job references them. Diarization and channel
identification are mutually exclusive. Medical transcription uses
a separate API. Custom language models must be trained before use.
PII redaction must be configured at job creation time. Use this
graph to sequence deployment.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Input S3 audio | bucket exists, Transcribe has ReadS3 access | job fails if audio not accessible or wrong format | the transcription |
| Language | must specify LanguageCode OR set IdentifyLanguage | auto-identify adds latency and may pick wrong language if audio is mixed | transcription accuracy |
| Custom vocabulary | vocabulary must be READY status (created + processed) | referencing a non-ready vocabulary → job fails | domain term accuracy |
| Vocabulary filter | filter must be READY status | filter mode (mask/remove/tag) determines behavior | unwanted word handling |
| Speaker diarization | job must set ShowSpeakerLabels=true | CANNOT combine with channel identification (mutually exclusive) | speaker-separated output |
| Channel identification | audio must be stereo (2 channels) | CANNOT combine with diarization; fails on mono audio | channel-separated output |
| Medical transcription | uses start-medical-transcription-job (separate API) | only supports specified language (no auto-identify); limited output formats | clinical transcription |
| Custom language model | model must be TRAINED (requires BaseModelName + training data S3 URI) | adds cost per minute; only for standard (non-medical) jobs | domain accuracy boost |
| PII redaction | set at job creation (ContentIdentificationTypes / ContentRedactionType) | applied DURING transcription — PII never appears in output | compliance |
| Output format | set OutputBucketName on the job | output written as JSON + requested formats (TXT, SRT, VTT) | transcript encoding |

**The diarization-vs-channel-identification mutual exclusion is
the one a baseline model misses.** These two features CANNOT be
used together. Speaker diarization is for mono audio where speakers
are not pre-separated. Channel identification is for stereo audio
where each channel is a separate speaker. A naive configuration
enabling both will fail or silently produce unexpected output.

**Cross-dependency gotchas:**
- Custom vocabulary and vocabulary filter are independent features.
  A vocabulary boosts desired terms; a filter suppresses unwanted
  terms. Both can be used simultaneously.
- PII redaction is set at job creation time. It CANNOT be applied
  retroactively to an existing transcript. The redaction happens
  during transcription.
- Medical transcription uses `start-medical-transcription-job`, a
  SEPARATE API from `start-transcription-job`. It does not support
  auto-language-identification or all output formats.
- Custom language models are language-specific. A model trained for
  en-US cannot be used with en-GB or other languages.
- The output is always written as a JSON file (the full transcript
  with timestamps). Additional formats (TXT, SRT, VTT) are
  generated if requested via `Subtitles` or the output format
  settings.

## Expert heuristic: batch vs real-time transcription

A baseline model says "use Transcribe." The correct heuristic
chooses between batch (async, from S3) and real-time (streaming).

```text
Transcription mode:
  ├── Audio file in S3 (batch processing acceptable)?
  │     → start-transcription-job (async, writes transcript to S3)
  │        Job status: QUEUED → IN_PROGRESS → COMPLETED | FAILED
  │        Check: get-transcription-job --transcription-job-name <name>
  ├── Real-time streaming (live audio, captions, live transcription)?
  │     → Transcribe Streaming (WebSocket or HTTP/2 stream)
  │        Uses transcribe-streaming-service (different API surface)
  ├── Audio is very long (>4 hours)?
  │     → Batch (streaming has session duration limits)
  └── Need immediate results for short clips?
        → Batch is still preferred for files — streaming is for live audio
```

**Key implication:** batch transcription from S3 is the standard
deployment pattern. Real-time streaming is a separate API and
runtime model. Most production use cases (call center recording
analysis, meeting transcription, content indexing) use batch.

## Expert heuristic: custom vocabulary vs custom language model

Both improve accuracy but work differently and have different
costs.

```text
Accuracy improvement options:
  ├── Few specific terms (company names, acronyms, product names)?
  │     → Custom Vocabulary (free to apply, just upload a vocabulary file)
  │        Boosts recognition of specific words
  │        No training data needed — just a word list with optional pronunciations
  │
  ├── Broader domain vocabulary (medical, legal, technical)?
  │     → Custom Language Model (requires training text, adds cost per minute)
  │        Improves OVERALL accuracy by training on domain-specific text
  │        Requires: 1,000 - 100,000 training sentences in a text file on S3
  │        Choose BaseModelName: NarrowBand (phone audio, 8kHz) or WideBand (high-quality, 16kHz+)
  │
  └── Both can be used simultaneously
        → Custom vocabulary for specific terms + CLM for overall accuracy
```

**Key implication:** start with a custom vocabulary (free, simple).
If accuracy is still insufficient, add a custom language model
(requires training data, adds ~$0.00075/second additional cost).

## Expert heuristic: diarization vs channel identification

```text
Speaker separation:
  ├── Mono audio (single channel, multiple speakers talking together)?
  │     → Speaker Diarization (ShowSpeakerLabels=true)
  │        ML-based speaker identification
  │        Labels: spk_0, spk_1, spk_2, ...
  │        Accuracy depends on audio quality and speaker overlap
  │        CANNOT be combined with channel identification
  │
  ├── Stereo audio (2 channels, each channel is one speaker)?
  │     → Channel Identification (ChannelIdentification=true)
  │        Hardware-based: each channel is labeled exactly
  │        Labels: ch_0, ch_1
  │        Exact separation — no ML ambiguity
  │        CANNOT be combined with diarization
  │
  └── Don't know the audio format?
        → Check: ffprobe -i audio.mp3 -show_channels
        → Mono (1 channel) → diarization
        → Stereo (2 channels) → channel identification
```

**Key implication:** channel identification is always preferred
when stereo audio is available because it is exact. Diarization is
the fallback for mono audio where channels are not pre-separated.

## Prerequisites (verify before deployment)

Before emitting deployment commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Input audio in S3 | Batch jobs read from S3 | `aws s3 ls s3://<bucket>/audio.wav` |
| S3 read permissions for Transcribe | Transcribe needs `s3:GetObject` on input | Verify IAM policy or bucket policy |
| S3 write permissions for Transcribe | Transcribe writes output to S3 | Verify `s3:PutObject` on output bucket |
| Audio format supported | flac, mp3, mp4, wav, WebM, amr, ogg, m4a | Verify file extension and codec |
| Language decision | Must specify OR enable auto-identify | Decide: specify LanguageCode or IdentifyLanguage=true |
| Custom vocabulary READY (if referenced) | Vocabulary must be processed before use | `aws transcribe get-vocabulary --vocabulary-name <name>` |
| Vocabulary filter READY (if referenced) | Filter must be processed before use | `aws transcribe get-vocabulary-filter --vocabulary-filter-name <name>` |
| Custom language model TRAINED (if referenced) | CLM must be trained before use | `aws transcribe describe-language-model --model-name <name>` |
| Diarization vs channel decision | Mutually exclusive features | Decide based on mono vs stereo audio |
| PII redaction decision | Must be set at job creation time | Decide if PII redaction is needed and which entity types |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Batch transcription (start-transcription-job)

The primary Transcribe API for batch processing. Reads audio from
S3, processes asynchronously, and writes the transcript to S3.

```bash
# Basic batch transcription job
aws transcribe start-transcription-job \
  --transcription-job-name my-transcription-001 \
  --media MediaFileUri=s3://my-input-bucket/audio/meeting.wav \
  --language-code en-US \
  --output-bucket-name my-output-bucket \
  --region us-east-1

# Check job status
aws transcribe get-transcription-job \
  --transcription-job-name my-transcription-001 \
  --query 'TranscriptionJob.TranscriptionJobStatus' --output text

# List all jobs
aws transcribe list-transcription-jobs \
  --query 'TranscriptionJobSummaries[*].{Name:TranscriptionJobName,Status:TranscriptionJobStatus}' \
  --output table
```

**Job lifecycle:**
- `QUEUED` → `IN_PROGRESS` → `COMPLETED` | `FAILED`
- On completion, transcript is at:
  `s3://<output-bucket>/<job-name>.json`
- Additional formats (if requested) at the same prefix.

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

## Step 2 — Language: identification vs specified

Transcribe can either use a specified language or auto-identify the
language from the audio.

| Mode | Parameter | Use when |
|---|---|---|
| Specified language | `--language-code en-US` | Language is known |
| Auto-identify | `--identify-language` | Language is unknown or mixed |

```bash
# Specified language (faster, more accurate for known language)
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --language-code en-US \
  --output-bucket-name my-output-bucket

# Auto-identify language (adds latency, may pick wrong for mixed audio)
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --identify-language \
  --output-bucket-name my-output-bucket
```

**Auto-identify caveats:**
- Adds processing time.
- May pick the wrong language for short clips or mixed-language
  audio.
- Supports a defined set of languages (not all languages support
  auto-identify).
- Medical transcription does NOT support auto-identify.

## Step 3 — Custom vocabulary

A custom vocabulary tells Transcribe how to handle specific words
(acronyms, domain terms, product names). It improves recognition
of those terms.

**Create a custom vocabulary from a list:**

```bash
# Create vocabulary from a simple phrase list
aws transcribe create-vocabulary \
  --vocabulary-name company-terms \
  --language-code en-US \
  --phrases "AWS" "EC2" "S3" "DynamoDB" "Lambda"

# Create vocabulary from a file (for complex entries with pronunciations)
aws transcribe create-vocabulary \
  --vocabulary-name medical-terms \
  --language-code en-US \
  --vocabulary-file-uri s3://my-vocab-bucket/medical-terms.txt
```

**Vocabulary file format (table-style, tab-delimited):**

```
Phrase\tSoundsLike\tIPA\tDisplayAs
Aortic stenosis\taortic stenosis\t\tAS
Myocardial infarction\tmyocardial infarction\t\tMI
```

**Apply a custom vocabulary to a job:**

```bash
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --language-code en-US \
  --settings VocabularyName=company-terms \
  --output-bucket-name my-output-bucket
```

**Check vocabulary status:**

```bash
aws transcribe get-vocabulary \
  --vocabulary-name company-terms \
  --query 'VocabularyState' --output text
# Must be READY before referencing in a job
```

## Step 4 — Vocabulary filter

A vocabulary filter suppresses unwanted words (profanity, brand
names of competitors, confidential terms) using three modes.

| Filter mode | Behavior |
|---|---|
| `mask` | Replaces filtered words with `***` |
| `remove` | Removes filtered words entirely |
| `tag` | Tags filtered words with metadata (for post-processing) |

```bash
# Create a vocabulary filter
aws transcribe create-vocabulary-filter \
  --vocabulary-filter-name profanity-filter \
  --language-code en-US \
  --words "word1" "word2" "word3"

# Apply filter to a job with mask mode
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --language-code en-US \
  --settings VocabularyFilterName=profanity-filter,VocabularyFilterMethod=mask \
  --output-bucket-name my-output-bucket
```

## Step 5 — Speaker identification (diarization)

Speaker diarization identifies and labels different speakers in
the audio. The output transcript includes speaker labels (spk_0,
spk_1, etc.).

```bash
# Enable speaker diarization
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --language-code en-US \
  --show-speaker-labels \
  --output-bucket-name my-output-bucket
```

**Diarization output (in JSON transcript):**

```json
{
  "speaker_labels": {
    "speakers": 2,
    "segments": [
      {
        "start_time": "0.00",
        "speaker_label": "spk_0",
        "end_time": "2.50",
        "items": [...]
      },
      {
        "start_time": "2.60",
        "speaker_label": "spk_1",
        "end_time": "5.00",
        "items": [...]
      }
    ]
  }
}
```

**Constraints:**
- Diarization CANNOT be combined with channel identification.
- Best for mono audio where speakers are not pre-separated.
- ML-based: accuracy depends on audio quality and speaker overlap.
- You can set the max number of speakers (up to 10) via the API.

## Step 6 — Channel identification (stereo)

Channel identification labels each audio channel separately. Use
for stereo audio where each channel is a distinct speaker (e.g.,
call center recordings with agent on one channel, caller on the
other).

```bash
# Enable channel identification
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/stereo-audio.wav \
  --language-code en-US \
  --channel-identification \
  --output-bucket-name my-output-bucket
```

**Constraints:**
- Audio MUST be stereo (2 channels).
- CANNOT be combined with speaker diarization.
- Exact separation (hardware-based, not ML).
- Labels: `ch_0`, `ch_1`.

## Step 7 — Medical transcription

Medical transcription uses a separate API (`start-medical-
transcription-job`) with specialized models for clinical content.

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

## Step 8 — Custom language model

A custom language model (CLM) improves overall transcription
accuracy by training on domain-specific text. It is especially
effective for specialized vocabulary that a custom vocabulary
alone cannot capture.

**Create a custom language model:**

```bash
# Training data must be a text file on S3 (1,000-100,000 sentences)
aws transcribe create-language-model \
  --model-name my-domain-model \
  --language-code en-US \
  --base-model-name WideBand \
  --input-data-uri s3://my-training-bucket/training-corpus.txt
```

**Base model selection:**

| Base model | Audio quality | Sample rate |
|---|---|---|
| `NarrowBand` | Telephone, low-quality | 8 kHz |
| `WideBand` | High-quality, studio | 16 kHz+ |

**Apply a custom language model to a job:**

```bash
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --language-code en-US \
  --model-settings LanguageModelName=my-domain-model \
  --output-bucket-name my-output-bucket
```

**Check model training status:**

```bash
aws transcribe describe-language-model \
  --model-name my-domain-model \
  --query 'ModelStatus' --output text
# Must be TRAINED before referencing in a job
```

**CLM constraints:**
- Training data must be 1,000 to 100,000 sentences of domain text.
- Training takes 30 minutes to several hours depending on data size.
- Adds ~$0.00075 per second of audio to the standard transcription cost.
- Language-specific: a model trained for en-US cannot be used for
  other languages.
- NOT supported for medical transcription jobs.

## Step 9 — Content identification and redaction (PII)

PII redaction masks sensitive information DURING transcription.
The PII is replaced with `[PII]` before the transcript is written
to S3. The unredacted transcript is never created.

**Content identification (tag PII without removing):**

```bash
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --language-code en-US \
  --content-identification-types PII \
  --output-bucket-name my-output-bucket
```

**Content redaction (mask PII):**

```bash
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --language-code en-US \
  --content-redaction-type PII \
  --redaction-output redacted \
  --pii-entity-types "NAME,SSN,EMAIL,PHONE,ADDRESS,BANK_ACCOUNT_NUMBER,BANK_ROUTING,DEBIT_CARD_NUMBER,CREDIT_CARD_NUMBER,PIN,DATE_TIME" \
  --output-bucket-name my-output-bucket
```

**Redaction output options:**
- `redacted`: only the redacted transcript is written to S3.
- `redacted_and_unredacted`: both versions are written (for
  compliance review). Requires elevated IAM permissions.

**PII entity types:**

| Category | Entity types |
|---|---|
| Personal | NAME, EMAIL, PHONE, ADDRESS, DATE_TIME |
| Financial | BANK_ACCOUNT_NUMBER, BANK_ROUTING, CREDIT_CARD_NUMBER, DEBIT_CARD_NUMBER, PIN |
| Government | SSN, PASSPORT_NUMBER |

**Critical:** PII redaction must be configured at job creation time.
It CANNOT be applied retroactively. The redaction happens during
the transcription process — the PII is identified and masked before
the transcript is written.

## Step 10 — Output formats (JSON, TXT, SRT, VTT)

The primary transcript output is always a JSON file containing the
full transcript with word-level timestamps and confidence scores.
Additional formats can be requested.

| Format | Description | How to enable |
|---|---|---|
| JSON | Full transcript with timestamps, confidence, speaker labels | Always generated |
| TXT | Plain text transcript (no timestamps) | Generated automatically alongside JSON |
| SRT | SubRip subtitles (timestamped) | `--subtitles Formats=srt` |
| VTT | Web Video Text Tracks (web subtitles) | `--subtitles Formats=vtt` |

```bash
# Request subtitles (SRT + VTT)
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --language-code en-US \
  --subtitles Formats=srt,vtt \
  --output-bucket-name my-output-bucket
```

**Output location:**
- JSON: `s3://<output-bucket>/<job-name>.json`
- TXT: `s3://<output-bucket>/<job-name>.txt`
- SRT: `s3://<output-bucket>/<job-name>.srt`
- VTT: `s3://<output-bucket>/<job-name>.vtt`

## Step 11 — CloudWatch metrics

Transcribe publishes metrics to CloudWatch for monitoring job
volume, duration, and errors.

| Metric | Description |
|---|---|
| `AudioDuration` | Total audio seconds processed (for billing) |
| `JobDuration` | Total processing time |
| `ThrottledCount` | Throttled requests |
| `JobFailureCount` | Failed jobs |

```bash
# Monitor audio duration processed (for cost tracking)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Transcribe \
  --metric-name AudioDuration \
  --start-time 2026-08-01T00:00:00Z \
  --end-time 2026-08-11T00:00:00Z \
  --period 86400 \
  --statistics Sum \
  --dimensions Name=TranscriptionJob,Value=Batch

# Set a billing alarm for audio duration
aws cloudwatch put-metric-alarm \
  --alarm-name transcribe-duration-budget \
  --namespace AWS/Transcribe \
  --metric-name AudioDuration \
  --statistic Sum \
  --period 86400 \
  --threshold 288000 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

## Step 12 — Pricing per second of audio

Transcribe pricing is per second of audio processed. The rate
depends on the transcription type and features.

| Transcription type | Price per second (us-east-1) | Notes |
|---|---|---|
| Standard batch | $0.024/sec ($1.44/min) | General-purpose |
| Medical batch | $0.0276/sec ($1.66/min) | Clinical content |
| + Custom language model | +$0.00075/sec (+$0.045/min) | Additional CLM cost |
| Real-time streaming | $0.024/sec ($1.44/min) | Live transcription |
| Medical real-time | $0.0276/sec ($1.66/min) | Live clinical |

```bash
# Estimate cost for 1 hour of standard audio
python3 -c "print(f'1hr standard: \${3600 * 0.024:.2f}')"
# Output: 1hr standard: $86.40

# Estimate cost for 1 hour of medical audio
python3 -c "print(f'1hr medical: \${3600 * 0.0276:.2f}')"
# Output: 1hr medical: $99.36

# Estimate cost for 1 hour with custom language model
python3 -c "print(f'1hr standard+CLM: \${3600 * (0.024 + 0.00075):.2f}')"
# Output: 1hr standard+CLM: $89.10
```

**Free tier:** 60 minutes per month for standard batch
transcription (first 12 months).

**Cost optimization:** Custom vocabularies and vocabulary filters
are FREE to apply. Custom language models add cost. Use custom
vocabularies first before resorting to CLM.

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

## NEVER do these things

1. **NEVER combine speaker diarization with channel identification.**
   These are mutually exclusive. Diarization is for mono audio (ML-
   based speaker separation). Channel identification is for stereo
   audio (hardware-based channel separation). Choose one based on
   audio format.

2. **NEVER apply PII redaction retroactively.** PII redaction must
   be configured at job creation time. It is applied DURING
   transcription — the PII is masked before the transcript is
   written. There is no way to redact an existing transcript. Re-run
   the job with redaction enabled.

3. **NEVER use medical transcription API for non-medical content.**
   Medical transcription costs more and uses specialized models
   optimized for clinical terminology. For general content, use
   the standard API. Medical transcription does not support auto-
   language-identify, CLM, or all output formats.

4. **NEVER reference a custom vocabulary or CLM before it is READY.**
   Vocabularies must be in READY state and language models in
   TRAINED state before referencing them in a job. Otherwise the
   job fails. Always check status with `get-vocabulary` or
   `describe-language-model`.

5. **NEVER assume auto-language-identify is always accurate.** For
   short clips or mixed-language audio, auto-identify may pick the
   wrong language. If the language is known, specify it explicitly
   with `--language-code` for better accuracy and lower latency.

6. **NEVER use a custom language model trained for one language on
   a different language.** CLMs are language-specific. An en-US
   model cannot be used with en-GB or es-US. Train a separate model
   for each language.

7. **NEVER forget to verify S3 permissions for both input and
   output.** Transcribe needs `s3:GetObject` on the input audio
   and `s3:PutObject` on the output bucket. Missing either causes
   the job to fail.

8. **NEVER assume the JSON transcript is the only output.** The
   JSON is always generated, but TXT, SRT, and VTT are only
   generated if explicitly requested via `--subtitles` or output
   settings. Plan output format requirements before starting the
   job.

9. **NEVER mix NarrowBand and WideBand custom language models.**
   The base model must match the audio quality. NarrowBand is for
   telephone audio (8 kHz). WideBand is for high-quality audio
   (16 kHz+). Mismatching degrades accuracy.

10. **NEVER forget that custom vocabularies are free but custom
    language models add cost.** Always try a custom vocabulary
    first. If accuracy is still insufficient, then add a CLM.
    Budget for the additional $0.00075/second.

## Output format

```text
TRANSCRIBE_JOB: <job-name> (<transcription-type>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Transcription type: standard batch | medical batch
  [✓|✗] Input audio: s3://<bucket>/<file> (<format>)
  [✓|✗] Output bucket: s3://<bucket> (Transcribe has PutObject)
  [✓|✗] Language: <code> (specified) | auto-identify enabled
  [✓|✗] Custom vocabulary: <name> — READY | not referenced
  [✓|✗] Vocabulary filter: <name> (<mode>) | not referenced
  [✓|✗] Speaker separation: diarization (mono) | channel identification (stereo) | none
  [✓|✗] Custom language model: <name> — TRAINED | not referenced
  [✓|✗] PII redaction: <type> (<entity-types>) — redacted | not required
  [✓|✗] Output formats: JSON (+ TXT, SRT, VTT if requested)
  [✓|✗] Estimated cost: $<amount> (<duration> seconds × $<rate>/sec)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws transcribe get-transcription-job --transcription-job-name <job-name>
  aws transcribe get-vocabulary --vocabulary-name <vocab-name>
  aws transcribe describe-language-model --model-name <model-name>
```

### Worked example — batch transcription with diarization and custom vocabulary

```text
TRANSCRIBE_JOB: meeting-transcription-001 (standard batch)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Transcription type: standard batch
  [✓] Input audio: s3://my-input-bucket/audio/meeting.wav (WAV)
  [✓] Output bucket: s3://my-output-bucket (Transcribe has PutObject)
  [✓] Language: en-US (specified)
  [✓] Custom vocabulary: company-terms — READY
  [✓] Vocabulary filter: not referenced
  [✓] Speaker separation: diarization (mono audio, 3 expected speakers)
  [✓] Custom language model: not referenced
  [✓] PII redaction: not required
  [✓] Output formats: JSON + SRT + VTT
  [✓] Estimated cost: $86.40 (3600 seconds × $0.024/sec)
  [✓] Tags: Environment=production, UseCase=meeting-transcription
VERIFICATION_COMMANDS:
  aws transcribe get-transcription-job --transcription-job-name meeting-transcription-001
  aws transcribe get-vocabulary --vocabulary-name company-terms
```

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

## Domain

AWS CloudOps / Amazon Transcribe Speech-to-Text Configuration &
Transcription Job Deployment.

## AWS documentation

- **Amazon Transcribe Developer Guide** — https://docs.aws.amazon.com/transcribe/latest/dg/what-is.html
- **Start transcription job** — https://docs.aws.amazon.com/transcribe/latest/APIReference/API_StartTranscriptionJob.html
- **Start medical transcription job** — https://docs.aws.amazon.com/transcribe/latest/APIReference/API_StartMedicalTranscriptionJob.html
- **Custom vocabulary** — https://docs.aws.amazon.com/transcribe/latest/dg/how-vocabulary.html
- **Vocabulary filter** — https://docs.aws.amazon.com/transcribe/latest/dg/how-vocabulary-filter.html
- **Speaker diarization** — https://docs.aws.amazon.com/transcribe/latest/dg/diarization.html
- **Channel identification** — https://docs.aws.amazon.com/transcribe/latest/dg/channel-id.html
- **Custom language model** — https://docs.aws.amazon.com/transcribe/latest/dg/custom-language-models.html
- **Content redaction** — https://docs.aws.amazon.com/transcribe/latest/dg/content-redaction.html
- **Output formats** — https://docs.aws.amazon.com/transcribe/latest/dg/how-input.html#how-output
- **Pricing** — https://aws.amazon.com/transcribe/pricing/
- **CloudWatch metrics** — https://docs.aws.amazon.com/transcribe/latest/dg/cloudwatch-monitoring.html
