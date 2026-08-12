# End-to-End Example: Transcribe Job Deployment

A walkthrough showing how to use the `transcribe-job-deployer`
skill from invocation through verification. Mirrors the
structured-eval pattern of shipping a concrete worked example per
skill.

---

## Scenario

You are deploying a batch Amazon Transcribe configuration for
meeting transcription with speaker diarization and a custom
vocabulary. The deployment needs:

- Input audio: s3://my-input-bucket/audio/meeting.wav (mono WAV)
- Language: en-US (specified)
- Speaker diarization: enabled (3 expected speakers)
- Custom vocabulary: company-terms (READY state)
- Output bucket: s3://my-output-bucket
- Subtitle formats: SRT and VTT
- Audio duration: 1 hour (3600 seconds)
- Region: us-east-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-transcribe-job
```

Then paste the requirements.

### Option B: Natural language

```
You: "Configure Transcribe to transcribe a 1-hour meeting
      recording from S3. Mono WAV, en-US. Enable speaker
      diarization for 3 speakers. Use the company-terms
      vocabulary. Output to S3 with SRT and VTT subtitles.
      Region us-east-1."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "configure transcribe batch job"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

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

---

## Step 3 — Pre-deployment: verify prerequisites

```bash
# Verify custom vocabulary is READY
aws transcribe get-vocabulary \
  --vocabulary-name company-terms \
  --query 'VocabularyState' --output text --region us-east-1
# Expected: READY

# Verify input audio exists
aws s3 ls s3://my-input-bucket/audio/meeting.wav --region us-east-1

# Verify output bucket exists
aws s3 ls s3://my-output-bucket/ --region us-east-1

# Verify audio format (should be mono)
ffprobe -i meeting.wav -show_channels
# Expected: channels=1 (mono)
```

---

## Step 4 — Deploy: start transcription job

```bash
# Start the batch transcription job with diarization + vocabulary + subtitles
aws transcribe start-transcription-job \
  --transcription-job-name meeting-transcription-001 \
  --media MediaFileUri=s3://my-input-bucket/audio/meeting.wav \
  --language-code en-US \
  --show-speaker-labels \
  --settings VocabularyName=company-terms \
  --subtitles Formats=srt,vtt \
  --output-bucket-name my-output-bucket \
  --region us-east-1
```

---

## Step 5 — Monitor job status

```bash
# Check job status (poll until COMPLETED)
aws transcribe get-transcription-job \
  --transcription-job-name meeting-transcription-001 \
  --query 'TranscriptionJob.TranscriptionJobStatus' --output text --region us-east-1
# Lifecycle: QUEUED → IN_PROGRESS → COMPLETED

# Get full job details including output URIs
aws transcribe get-transcription-job \
  --transcription-job-name meeting-transcription-001 \
  --query 'TranscriptionJob.{Status:TranscriptionJobStatus,Output:Transcript.TranscriptFileUri,Subtitles:Subtitles.SubtitleFileUris}' \
  --output table --region us-east-1
```

---

## Step 6 — Post-deployment verification

```bash
# Verify transcript JSON was written
aws s3 ls s3://my-output-bucket/meeting-transcription-001.json --region us-east-1

# Verify SRT subtitle file
aws s3 ls s3://my-output-bucket/meeting-transcription-001.srt --region us-east-1

# Verify VTT subtitle file
aws s3 ls s3://my-output-bucket/meeting-transcription-001.vrt --region us-east-1

# Download and inspect transcript (check speaker labels)
aws s3 cp s3://my-output-bucket/meeting-transcription-001.json - --region us-east-1 | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
labels = data.get('results', {}).get('speaker_labels', {})
print(f\"Speakers detected: {labels.get('speakers', 'N/A')}\")
segments = labels.get('segments', [])
for seg in segments[:3]:
    print(f\"  {seg['speaker_label']}: {seg['start_time']}s - {seg['end_time']}s\")
"

# Estimate cost (standard batch at $0.024/sec)
python3 -c "print(f'Cost: \${3600 * 0.024:.2f}')"
# Output: Cost: $86.40
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Diarization vs channel ID | May enable both | Checks audio format, picks one | Mutually exclusive features |
| Vocabulary status | References without checking READY | Verifies READY before job start | Job fails if vocab is PENDING |
| PII redaction | Applies after transcription | Configures at job creation time | Cannot redact retroactively |
| Medical API | Uses standard API for clinical | Routes to start-medical-transcription-job | Separate API, specialized model |
| Cost estimation | No per-second estimate | Calculates by type (standard vs medical vs CLM) | Medical is $0.0276/s; CLM adds $0.00075/s |
| Custom vocabulary vs CLM | Confuses the two | Clarifies: vocab is free (word boost), CLM costs (accuracy boost) | Different features with different costs |
| S3 permissions | Starts job without verifying access | Checks GetObject on input + PutObject on output | Job fails silently without permissions |
| Output formats | Expects SRT/VTT without requesting | Explicitly sets --subtitles Formats=srt,vtt | Only JSON is generated by default |

---

## Related artifacts

- **Skill definition:** `skills/transcribe-job-deployer/SKILL.md`
- **Vocabulary and filtering guide:** `skills/transcribe-job-deployer/references/vocabulary-and-filtering.md`
- **Diarization and redaction guide:** `skills/transcribe-job-deployer/references/diarization-and-redaction.md`
- **Eval suite:** `skills/transcribe-job-deployer/evals/evals.json`
- **Legacy test cases:** `skills/transcribe-job-deployer/eval/test-cases.yaml`
