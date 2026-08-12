# End-to-End Example: Polly Voice Deployment

A walkthrough showing how to use the `polly-voice-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying a real-time Amazon Polly neural TTS configuration
for a web application greeting system. The deployment needs:

- Engine: neural
- Voice: Joanna (en-US, Female)
- Output format: MP3 at 24000 Hz
- Lexicon: company-terms (custom pronunciation for "AWS", "EC2")
- Text: "Welcome to AWS. Your EC2 instance is ready."
- Synthesis mode: real-time (synthesize-speech)
- Region: us-east-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-polly-voice
```

Then paste the requirements.

### Option B: Natural language

```
You: "Configure Polly neural TTS with voice Joanna for a web
      app greeting. MP3 at 24000 Hz. Use the company-terms
      lexicon for AWS and EC2 pronunciation. Region us-east-1."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "configure polly neural voice"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
POLLY_VOICE: Joanna (neural engine, en-US)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Engine: neural
  [✓] Voice: Joanna (en-US, Female)
  [✓] Voice available on engine: PASS (Joanna supports neural)
  [✓] SSML compatibility: plain text (no SSML) — PASS
  [✓] Output format: mp3
  [✓] Sample rate: 24000 Hz — PASS (valid for mp3)
  [✓] Lexicon: company-terms — uploaded
  [✓] Synthesis mode: real-time (synthesize-speech)
  [✓] Speech marks: not required
  [✓] Estimated cost: $0.000832 (52 chars × $16/1M)
  [✓] Tags: Environment=production, UseCase=greeting
VERIFICATION_COMMANDS:
  aws polly describe-voices --engine neural --query 'Voices[?Id==`Joanna`]'
  aws polly list-lexicons --query 'Lexicons[?Name==`company-terms`]'
```

---

## Step 3 — Pre-deployment: upload the lexicon

```bash
# Create the PLS lexicon file
cat > company-terms.pls << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<lexicon version="1.0"
      xmlns="http://www.w3.org/2005/01/pronunciation-lexicon"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="http://www.w3.org/2005/01/pronunciation-lexicon
        http://www.w3.org/TR/2007/CR-pronunciation-lexicon-20071212/pls.xsd"
      alphabet="ipa"
      xml:lang="en-US">
  <lexeme>
    <grapheme>AWS</grapheme>
    <alias>A W S</alias>
  </lexeme>
  <lexeme>
    <grapheme>EC2</grapheme>
    <alias>E C two</alias>
  </lexeme>
</lexicon>
EOF

# Upload the lexicon
aws polly put-lexicon \
  --name company-terms \
  --content fileb://company-terms.pls \
  --region us-east-1
```

---

## Step 4 — Deploy: real-time synthesis

```bash
# Verify voice availability on neural engine
aws polly describe-voices --engine neural \
  --query 'Voices[?Id==`Joanna`].{Id:Id,LanguageCode:LanguageCode}' \
  --output table --region us-east-1

# Verify lexicon exists
aws polly list-lexicons \
  --query 'Lexicons[?Name==`company-terms`].Name' \
  --output text --region us-east-1

# Real-time synthesis with lexicon
aws polly synthesize-speech \
  --engine neural \
  --voice-id Joanna \
  --output-format mp3 \
  --sample-rate 24000 \
  --lexicon-names company-terms \
  --text "Welcome to AWS. Your EC2 instance is ready." \
  --region us-east-1 \
  greeting.mp3
```

---

## Step 5 — Post-deployment verification

```bash
# Verify the audio file was created
ls -la greeting.mp3

# Check audio metadata
ffprobe greeting.mp3

# Verify character count for cost estimation
echo -n "Welcome to AWS. Your EC2 instance is ready." | wc -c
# Output: 52

# Estimate cost (neural at $16/1M chars)
python3 -c "print(f'Cost: \${52 * 16 / 1000000:.6f}')"
# Output: Cost: $0.000832

# Monitor CloudWatch for synthesis volume
aws cloudwatch get-metric-statistics \
  --namespace AWS/Polly \
  --metric-name RequestCharacters \
  --start-time 2026-08-11T00:00:00Z \
  --end-time 2026-08-11T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --dimensions Name=Operation,Value=SynthesizeSpeech \
  --region us-east-1
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Engine vs SSML | Uses neural with `<break>` tags | Verifies SSML tags are engine-compatible | `<break>`/`<emphasis>` silently ignored by neural |
| Speech marks | Single request for audio + marks | Two separate requests (mp3 + json) | Marks are a different OutputFormat |
| Lexicon region | Uploads lexicon once, uses cross-region | Uploads per-region, verifies before synthesis | Lexicons are region-scoped |
| Sample rate | Uses 24000 with PCM | Matches format to rate (PCM = 8000/16000) | Invalid format-rate combos error or coerce |
| Cost estimation | No per-character estimate | Calculates by engine rate | Neural is 4x standard; long-form is 25x |
| Long text | Uses synthesize-speech for >3000 chars | Routes to start-speech-synthesis-task | Real-time API has payload limit |

---

## Related artifacts

- **Skill definition:** `skills/polly-voice-deployer/SKILL.md`
- **Engine and voice selection guide:** `skills/polly-voice-deployer/references/engine-and-voice-selection.md`
- **SSML and lexicons guide:** `skills/polly-voice-deployer/references/ssml-and-lexicons.md`
- **Eval suite:** `skills/polly-voice-deployer/evals/evals.json`
- **Legacy test cases:** `skills/polly-voice-deployer/eval/test-cases.yaml`
