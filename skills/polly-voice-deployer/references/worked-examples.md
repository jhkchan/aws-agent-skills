# Worked Examples — Polly Voice Deployer

Filled-in synthesis examples moved out of the SKILL.md body. Loaded on demand.


## Step 5 — Speech marks generation and output

**Generate speech marks (separate request from audio):**

```bash
# Generate word and sentence marks
aws polly synthesize-speech \
  --engine standard \
  --voice-id Joanna \
  --output-format json \
  --sample-rate 22050 \
  --speech-mark-types '["word","sentence"]' \
  --text "Hello world. This is a test." \
  marks.json
```

**Output format (line-delimited JSON):**

```json
{"time":6,"type":"sentence","start":0,"end":26}
{"time":0,"type":"word","start":0,"end":5}
{"time":57,"type":"word","start":6,"end":11}
{"time":120,"type":"sentence","start":0,"end":26}
{"time":120,"type":"word","start":13,"end":17}
{"time":205,"type":"word","start":18,"end":20}
{"time":300,"type":"word","start":21,"end":25}
```

- `time`: offset in milliseconds from the start of the audio.
- `start`/`end`: character positions in the input text.
- `type`: the mark type (viseme, word, sentence, ssml).


## Step 6 — synthesize-speech real-time examples

```bash
# Real-time synthesis (plain text)
aws polly synthesize-speech \
  --engine neural \
  --voice-id Joanna \
  --output-format mp3 \
  --sample-rate 24000 \
  --text "Hello, this is a test of Amazon Polly neural voices." \
  output.mp3

# Real-time synthesis (SSML)
aws polly synthesize-speech \
  --engine standard \
  --voice-id Matthew \
  --output-format mp3 \
  --sample-rate 24000 \
  --text-type ssml \
  --text '<speak>Hello <break time="500ms"/> world.</speak>' \
  output.mp3

# Real-time synthesis with lexicon
aws polly synthesize-speech \
  --engine standard \
  --voice-id Joanna \
  --output-format mp3 \
  --sample-rate 24000 \
  --lexicon-names company-terms \
  --text "Welcome to AWS EC2." \
  output.mp3
```


## Step 7 — Async synthesis task commands

```bash
# Start an async synthesis task
TASK_ID=$(aws polly start-speech-synthesis-task \
  --engine neural \
  --voice-id Joanna \
  --output-format mp3 \
  --sample-rate 24000 \
  --output-s3-bucket-name my-polly-output \
  --output-s3-key-prefix audio/articles/ \
  --text "This is a very long text that exceeds the synthesize-speech limit..." \
  --query 'SynthesisTask.TaskId' --output text)

echo "Task ID: $TASK_ID"

# Check task status
aws polly get-speech-synthesis-task --task-id "$TASK_ID"

# List all synthesis tasks
aws polly list-speech-synthesis-tasks \
  --query 'SynthesisTasks[*].{TaskId:TaskId,Status:TaskStatus,OutputUri:OutputUri}' \
  --output table
```


## Step 8 — Output format and sample rate examples

```bash
# Telephony-quality output (PCM, 8000 Hz)
aws polly synthesize-speech \
  --engine standard \
  --voice-id Joanna \
  --output-format pcm \
  --sample-rate 8000 \
  --text "Press 1 for sales." \
  output.pcm

# High-quality MP3 output
aws polly synthesize-speech \
  --engine neural \
  --voice-id Joanna \
  --output-format mp3 \
  --sample-rate 24000 \
  --text "Welcome to the service." \
  output.mp3
```
