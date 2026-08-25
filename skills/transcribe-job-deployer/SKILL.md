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

start-transcription-job, get-transcription-job, list-transcription-jobs — moved verbatim.
Full detail: [Worked examples](references/worked-examples.md).

**Job lifecycle:**
- `QUEUED` → `IN_PROGRESS` → `COMPLETED` | `FAILED`
- On completion, transcript is at:
  `s3://<output-bucket>/<job-name>.json`
- Additional formats (if requested) at the same prefix.


## Step 2 — Language: identification vs specified

Transcribe can either use a specified language or auto-identify the
language from the audio.

| Mode | Parameter | Use when |
|---|---|---|
| Specified language | `--language-code en-US` | Language is known |
| Auto-identify | `--identify-language` | Language is unknown or mixed |

--language-code vs --identify-language — moved verbatim.
Full detail: [Worked examples](references/worked-examples.md).


## Step 3 — Custom vocabulary

A custom vocabulary tells Transcribe how to handle specific words
(acronyms, domain terms, product names). It improves recognition
of those terms.

create-vocabulary (phrases / file), table format, apply to job, READY check — moved verbatim.
Full detail: [Vocabulary and filtering](references/vocabulary-and-filtering.md).

## Step 4 — Vocabulary filter

A vocabulary filter suppresses unwanted words (profanity, brand
names of competitors, confidential terms) using three modes.

| Filter mode | Behavior |
|---|---|
| `mask` | Replaces filtered words with `***` |
| `remove` | Removes filtered words entirely |
| `tag` | Tags filtered words with metadata (for post-processing) |

create-vocabulary-filter, mask/remove/tag modes — moved verbatim.
Full detail: [Vocabulary and filtering](references/vocabulary-and-filtering.md).

## Step 5 — Speaker identification (diarization)

Speaker diarization identifies and labels different speakers in
the audio. The output transcript includes speaker labels (spk_0,
spk_1, etc.).

--show-speaker-labels, speaker_labels JSON, constraints — moved verbatim.
Full detail: [Diarization and redaction](references/diarization-and-redaction.md).

## Step 6 — Channel identification (stereo)

Channel identification labels each audio channel separately. Use
for stereo audio where each channel is a distinct speaker (e.g.,
call center recordings with agent on one channel, caller on the
other).

--channel-identification, stereo-only constraint — moved verbatim.
Full detail: [Diarization and redaction](references/diarization-and-redaction.md).

## Step 7 — Medical transcription

Medical transcription uses a separate API (`start-medical-
transcription-job`) with specialized models for clinical content.

standard-vs-medical comparison, start-medical-transcription-job, specialty/type options — moved verbatim.
Full detail: [Advanced patterns](references/advanced-patterns.md).

## Step 8 — Custom language model

A custom language model (CLM) improves overall transcription
accuracy by training on domain-specific text. It is especially
effective for specialized vocabulary that a custom vocabulary
alone cannot capture.

**Create a custom language model:**

create-language-model, apply to job, TRAINED check, CLM constraints — moved verbatim.
Full detail: [Vocabulary and filtering](references/vocabulary-and-filtering.md).

**Base model selection:**

| Base model | Audio quality | Sample rate |
|---|---|---|
| `NarrowBand` | Telephone, low-quality | 8 kHz |
| `WideBand` | High-quality, studio | 16 kHz+ |

**Apply a custom language model to a job:**



## Step 9 — Content identification and redaction (PII)

PII redaction masks sensitive information DURING transcription.
The PII is replaced with `[PII]` before the transcript is written
to S3. The unredacted transcript is never created.

content-identification, content-redaction, redaction-output options, PII entity types — moved verbatim.
Full detail: [Diarization and redaction](references/diarization-and-redaction.md).

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

--subtitles Formats=srt,vtt, output locations — moved verbatim.
Full detail: [Worked examples](references/worked-examples.md).

## Step 11 — CloudWatch metrics

AudioDuration / JobDuration / ThrottledCount / JobFailureCount, put-metric-alarm — moved verbatim.
Full detail: [Diagnostic commands](references/diagnostic-commands.md).

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

1-hour standard / medical / +CLM estimates — moved verbatim.
Full detail: [Worked examples](references/worked-examples.md).

**Free tier:** 60 minutes per month for standard batch
transcription (first 12 months).

**Cost optimization:** Custom vocabularies and vocabulary filters
are FREE to apply. Custom language models add cost. Use custom
vocabularies first before resorting to CLM.

## Step 13 — Recent features

CLM v2, PII entity expansion, subtitles, medical specialties, metric dimensions — moved verbatim.
Full detail: [Advanced patterns](references/advanced-patterns.md).

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

S3 access denied, unsupported format, vocabulary not READY, diarization+channel conflict, PII not applied, medical auto-identify, CLM accuracy — moved verbatim.
Full detail: [Error handling](references/error-handling.md).

## References (load on demand)

- [Vocabulary and filtering](references/vocabulary-and-filtering.md) — custom vocabularies, vocabulary filters, vocabulary-vs-CLM heuristic, CLM training and constraints
- [Diarization and redaction](references/diarization-and-redaction.md) — diarization-vs-channel heuristic, diarization/channel CLI and output, PII redaction, entity types
- [Worked examples](references/worked-examples.md) — batch / language / subtitle CLI walkthroughs, cost estimation
- [Diagnostic commands](references/diagnostic-commands.md) — CloudWatch metrics and billing alarms
- [Advanced patterns](references/advanced-patterns.md) — audio format catalog, auto-identify caveats, medical transcription, recent features
- [Error handling](references/error-handling.md) — S3 access, formats, vocabulary states, mutual exclusion, CLM issues

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
