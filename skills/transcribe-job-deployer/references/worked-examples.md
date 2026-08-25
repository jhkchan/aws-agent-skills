# Worked Examples — Transcribe Job Deployer

Step-by-step CLI walkthroughs moved verbatim from SKILL.md. Loaded on demand.

## Step 1 — Batch transcription CLI

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

## Step 2 — Language: specified vs auto-identify CLI

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

## Step 10 — Subtitle / output format CLI

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

## Step 12 — Cost estimation examples

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
