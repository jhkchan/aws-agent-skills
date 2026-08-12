# Eval: async-s3-batch

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — long-form engine, voice Joanna en-US, async start-speech-synthesis-task to S3 bucket my-polly-output, MP3 24000 Hz, cost estimate for 50K chars

## Prompt

Configure Amazon Polly to batch-synthesize a 50,000-character
article to S3 using the long-form engine. Voice: Joanna (en-US).
Output format: MP3 at 24000 Hz. S3 output bucket:
my-polly-output, key prefix: audio/articles/. Region us-east-1.
Tags: Environment=production, UseCase=audiobook.
