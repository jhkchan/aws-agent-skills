# Diagnostic Commands — Polly Voice Deployer

Pre-flight discovery and post-deployment verification commands moved out of the SKILL.md body. Loaded on demand.


## Step 1 — Engine and voice discovery commands

```bash
# List voices available for a specific engine
aws polly describe-voices --engine neural --language-code en-US \
  --query 'Voices[*].{Id:Id,Name:Name,Gender:Gender}' --output table

# List voices for standard engine (all voices)
aws polly describe-voices --engine standard --language-code en-US \
  --query 'Voices[*].{Id:Id,Name:Name,Gender:Gender}' --output table
```


## Step 2 — Voice discovery by language commands

```bash
# Discover voices for a language
aws polly describe-voices --language-code en-US \
  --query 'Voices[*].{Id:Id,Gender:Gender,Engine:[SupportsNeural,SupportsStandard]}' \
  --output table

# Check if a specific voice supports neural
aws polly describe-voices --engine neural \
  --query 'Voices[?Id==`Joanna`].{Id:Id,LanguageCode:LanguageCode}' --output table
```


## Step 7 — Verify async task S3 output

```bash
# Verify the S3 output
aws s3 ls s3://my-polly-output/audio/articles/$TASK_ID.mp3
```


## Step 9 — CloudWatch metrics commands

```bash
# Monitor character usage (for cost tracking)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Polly \
  --metric-name RequestCharacters \
  --start-time 2026-08-01T00:00:00Z \
  --end-time 2026-08-05T00:00:00Z \
  --period 86400 \
  --statistics Sum \
  --dimensions Name=Operation,Value=SynthesizeSpeech

# Set a billing alarm for character usage
aws cloudwatch put-metric-alarm \
  --alarm-name polly-character-budget \
  --namespace AWS/Polly \
  --metric-name RequestCharacters \
  --statistic Sum \
  --period 86400 \
  --threshold 1000000 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```


## Step 10 — Pricing estimation commands

```bash
# Estimate character count of input text
echo -n "Your input text here" | wc -c

# Monthly cost estimate (neural, 500K chars/month)
python3 -c "print(f'${500000 * 16 / 1000000:.2f}/month')"
```
