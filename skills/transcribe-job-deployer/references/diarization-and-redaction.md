# Speaker Diarization and Content Redaction — Transcribe Job Deployer

Deep reference on speaker diarization (ML-based speaker
identification for mono audio), channel identification (hardware-
based channel separation for stereo audio), the mutual exclusion
between the two, content identification and redaction (PII masking
during transcription), entity types, and the redacted output
options. Loaded on demand by the skill — kept out of the main
SKILL.md body so the deployment procedure stays scannable.

## Speaker diarization

### What diarization does

Speaker diarization uses machine learning to identify distinct
speakers in an audio stream and label each segment of the
transcript with the speaker who spoke it. This is essential for
multi-speaker audio such as meetings, interviews, and podcasts.

```bash
# Enable diarization
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/meeting.wav \
  --language-code en-US \
  --show-speaker-labels \
  --output-bucket-name my-output-bucket
```

### Diarization output structure

The JSON transcript includes a `speaker_labels` section:

```json
{
  "speaker_labels": {
    "channel": false,
    "speakers": 2,
    "segments": [
      {
        "start_time": "0.00",
        "end_time": "3.24",
        "speaker_label": "spk_0",
        "items": [
          { "start_time": "0.00", "end_time": "0.52" },
          { "start_time": "0.62", "end_time": "1.10" }
        ]
      },
      {
        "start_time": "3.30",
        "end_time": "7.45",
        "speaker_label": "spk_1",
        "items": [...]
      }
    ]
  },
  "transcripts": [...]
}
```

Each word in the `items` array of the transcript is associated
with a `speaker_label` (e.g., `spk_0`, `spk_1`).

### Diarization constraints

- **Mono audio only (in practice):** while technically possible
  with any audio, diarization is designed for mono audio where
  speakers are mixed into a single channel.
- **Mutually exclusive with channel identification:** you CANNOT
  use both `--show-speaker-labels` and `--channel-identification`
  in the same job.
- **ML-based accuracy:** diarization is approximate. Accuracy
  depends on audio quality, speaker overlap, and speaker count.
  Best results when speakers take turns with minimal overlap.
- **Speaker count:** Transcribe automatically detects the number
  of speakers (up to 10). You can hint the expected count via the
  API.
- **Additional cost:** no additional cost beyond standard
  transcription pricing.

### When to use diarization

```text
Audio format check:
  ├── ffprobe -i audio.wav -show_channels
  ├── Mono (1 channel)?
  │     → Use speaker diarization (--show-speaker-labels)
  │        ML identifies and labels speakers (spk_0, spk_1, ...)
  │
  └── Stereo (2 channels)?
        → Use channel identification (--channel-identification)
           Each channel is labeled exactly (ch_0, ch_1)
           Preferred when stereo is available — exact separation
```

## Channel identification

### What channel identification does

Channel identification labels each audio channel separately. This
is for stereo audio where each channel represents a distinct
speaker (e.g., call center recordings with agent on channel 0 and
caller on channel 1).

```bash
# Enable channel identification
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/stereo-call.wav \
  --language-code en-US \
  --channel-identification \
  --output-bucket-name my-output-bucket
```

### Channel identification output

The transcript is separated by channel. Each channel produces its
own transcript segments labeled `ch_0` and `ch_1`:

```json
{
  "channel_labels": {
    "channels": [
      {
        "channel_label": "ch_0",
        "items": [...],
        "transcript": "Hello, thank you for calling..."
      },
      {
        "channel_label": "ch_1",
        "items": [...],
        "transcript": "Hi, I need help with..."
      }
    ]
  }
}
```

### Channel identification constraints

- Audio MUST be stereo (2 channels).
- Mutually exclusive with speaker diarization.
- Exact separation (no ML ambiguity).
- Each channel is transcribed independently.

## Diarization vs channel identification decision matrix

| Feature | Diarization | Channel Identification |
|---|---|---|
| Audio type | Mono | Stereo (2 channels) |
| Separation method | ML-based (approximate) | Hardware-based (exact) |
| Labels | spk_0, spk_1, ... | ch_0, ch_1 |
| Max speakers/channels | 10 speakers | 2 channels |
| Mutual exclusion | Cannot combine with channel ID | Cannot combine with diarization |
| Additional cost | None | None |
| Accuracy | Depends on audio quality and overlap | Exact (per-channel) |
| Best for | Meetings, interviews, podcasts (mono) | Call center recordings (stereo) |

## Content identification and redaction (PII)

### How PII redaction works

PII redaction is applied DURING transcription. As Transcribe
processes the audio, it identifies PII entities and masks them
(replaces with `[PII]`) BEFORE the transcript is written to S3.
The unredacted transcript is never created.

```text
Audio → Transcribe engine → PII detection → Mask PII → Write redacted transcript to S3
                                            ↓
                                   [PII] replaces NAME, SSN, etc.
                                   Original PII never persisted
```

### Content identification (tag, not remove)

Content identification tags PII in the transcript metadata without
removing it from the text:

```bash
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --language-code en-US \
  --content-identification-types PII \
  --output-bucket-name my-output-bucket
```

The transcript text includes the PII, but each PII entity is tagged
with its type for downstream processing.

### Content redaction (mask)

Content redaction masks PII in the transcript output:

```bash
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --language-code en-US \
  --content-redaction-type PII \
  --redaction-output redacted \
  --pii-entity-types "NAME,SSN,EMAIL,PHONE,ADDRESS,BANK_ACCOUNT_NUMBER,CREDIT_CARD_NUMBER" \
  --output-bucket-name my-output-bucket
```

### Redaction output options

| `--redaction-output` | Behavior |
|---|---|
| `redacted` | Only the redacted transcript is written to S3 |
| `redacted_and_unredacted` | Both redacted and unredacted versions are written (requires elevated IAM permissions; for compliance review) |

### PII entity types

| Category | Entity types |
|---|---|
| Personal identification | `NAME`, `EMAIL`, `PHONE`, `ADDRESS`, `DATE_TIME` |
| Financial | `BANK_ACCOUNT_NUMBER`, `BANK_ROUTING`, `CREDIT_CARD_NUMBER`, `DEBIT_CARD_NUMBER`, `PIN` |
| Government | `SSN`, `PASSPORT_NUMBER` |
| All | `ALL` (redacts all supported entity types) |

### Redaction constraints

- Must be set at job creation time. CANNOT be applied retroactively.
- Only supports English (`en-US`) audio.
- Medical transcription supports PHI redaction (similar mechanism,
  different entity types).
- The `redacted_and_unredacted` output requires elevated IAM
  permissions and should be used carefully (the unredacted version
  contains PII).

### Redaction output example

**Input audio:** "My name is John Smith and my SSN is 123-45-6789."

**Redacted transcript:**
```
My name is [PII] and my SSN is [PII].
```

The original values ("John Smith", "123-45-6789") never appear in
the output file.

## Common pitfalls

### Pitfall 1: Diarization and channel identification both enabled

The job fails or produces unexpected output. **Fix:** use only one.
Diarization for mono, channel identification for stereo.

### Pitfall 2: PII redaction applied after transcription

Not possible. Redaction is a job-creation-time setting. **Fix:**
re-run the job with `--content-redaction-type PII` enabled.

### Pitfall 3: Redaction with non-English audio

PII redaction only supports en-US. **Fix:** for other languages,
transcribe normally and use Amazon Comprehend for post-hoc entity
detection and redaction.

### Pitfall 4: Diarization poor accuracy

Diarization is ML-based and can struggle with overlapping speech,
similar voices, or background noise. **Fix:** use stereo audio with
channel identification if possible. For mono, improve audio quality
(noise reduction) before transcription.

## Terraform example

```hcl
# Transcription job with diarization (via local-exec)
resource "null_resource" "transcription_job" {
  triggers = {
    audio_uri = var.input_audio_uri
  }

  provisioner "local-exec" {
    command = <<-EOF
      aws transcribe start-transcription-job \
        --transcription-job-name ${var.job_name} \
        --media MediaFileUri=${var.input_audio_uri} \
        --language-code ${var.language_code} \
        --show-speaker-labels \
        --settings VocabularyName=${var.vocabulary_name} \
        --content-redaction-type PII \
        --redaction-output redacted \
        --pii-entity-types "NAME,SSN,PHONE,EMAIL" \
        --output-bucket-name ${var.output_bucket} \
        --region ${var.region}
    EOF
  }
}
```
