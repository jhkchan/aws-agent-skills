# Engine and Voice Selection — Polly Voice Deployer

Deep reference on Polly engine types (standard, neural, long-form,
generative), the voice catalog and per-engine availability, SSML
tag constraints per engine, the quality-vs-cost trade-off matrix,
and output format / sample rate coupling. Loaded on demand by the
skill — kept out of the main SKILL.md body so the deployment
procedure stays scannable.

## Engine fundamentals

### Standard engine

The standard engine is the original Polly TTS engine. It supports
ALL voices across ALL languages and provides full SSML tag support
including `<break>` and `<emphasis>`.

- **Quality:** Good (natural but detectably synthetic for complex
  prosody).
- **Latency:** 100-300ms typical.
- **Cost:** $4.00 per 1 million characters (lowest).
- **SSML:** Full support — `<break>`, `<emphasis>`, `<prosody>`,
  `<phoneme>`, `<say-as>`, `<sub>`, `<w>`, `<amazon:effect>`.
- **Use when:** cost-sensitive, high-volume, need `<break>`/`<emphasis>`,
  broad language coverage.

### Neural engine

The neural engine uses deep learning to produce higher-quality,
more natural speech. It supports a SUBSET of voices.

- **Quality:** High (significantly more natural than standard).
- **Latency:** 200-600ms typical.
- **Cost:** $16.00 per 1 million characters (4x standard).
- **SSML:** Partial — `<prosody>`, `<phoneme>`, `<say-as>`, `<sub>`.
  Does NOT support `<break>` or `<emphasis>`.
- **Use when:** user-facing quality matters, cost is acceptable,
  no `<break>`/`<emphasis>` requirement.

### Long-form engine

The long-form engine is optimized for narrated content (audiobooks,
podcasts, long articles). It produces the most natural pacing and
intonation for paragraph-length text.

- **Quality:** Highest for narrative content.
- **Latency:** Higher (optimized for quality, not real-time).
- **Cost:** $100.00 per 1 million characters.
- **SSML:** Partial — `<prosody>`. Does NOT support `<break>` or
  `<emphasis>`.
- **Use when:** audiobook, podcast, long-form narration where
  quality justifies cost.

### Generative engine

The generative engine uses diffusion-based models for the most
expressive, conversational voices. Limited voice set (expanding).

- **Quality:** Highest for conversational content.
- **Latency:** Higher (optimized for quality).
- **Cost:** $120.00 per 1 million characters.
- **SSML:** Partial — `<prosody>`. Does NOT support `<break>` or
  `<emphasis>`.
- **Use when:** conversational AI, virtual assistants, gaming NPCs.

## Voice catalog and engine availability

### Discovering voices per engine

```bash
# All standard voices for en-US
aws polly describe-voices --engine standard --language-code en-US \
  --query 'Voices[*].{Id:Id,Name:Name,Gender:Gender}' --output table

# All neural voices for en-US
aws polly describe-voices --engine neural --language-code en-US \
  --query 'Voices[*].{Id:Id,Name:Name,Gender:Gender}' --output table

# All long-form voices
aws polly describe-voices --engine long-form \
  --query 'Voices[*].{Id:Id,LanguageCode:LanguageCode}' --output table

# All generative voices
aws polly describe-voices --engine generative \
  --query 'Voices[*].{Id:Id,LanguageCode:LanguageCode}' --output table
```

### Common en-US voices and engine support

| Voice ID | Gender | Standard | Neural | Long-form | Generative |
|---|---|---|---|---|---|
| Joanna | Female | Yes | Yes | Yes | Yes |
| Matthew | Male | Yes | Yes | Yes | Yes |
| Stephen | Male | Yes | Yes | No | No |
| Kevin | Male | Yes | Yes | No | No |
| Danielle | Female | Yes | Yes | No | No |
| Gregory | Male | Yes | Yes | No | No |
| Salli | Female | Yes | No | No | No |
| Joey | Male | Yes | No | No | No |
| Kendra | Female | Yes | No | No | No |

**Key insight:** not all standard voices have neural, long-form, or
generative equivalents. Always verify with `describe-voices`.

### Multi-language voice selection

```bash
# List all available languages
aws polly describe-voices \
  --query 'Voices[*].LanguageCode' --output text | tr '\t' '\n' | sort -u

# Find voices for a specific language
aws polly describe-voices --language-code fr-FR \
  --query 'Voices[*].{Id:Id,Gender:Gender}' --output table
```

## SSML tag compatibility matrix

| SSML tag | Standard | Neural | Long-form | Generative |
|---|---|---|---|---|
| `<speak>` (root) | Yes | Yes | Yes | Yes |
| `<break>` | Yes | **No** | **No** | **No** |
| `<emphasis>` | Yes | **No** | **No** | **No** |
| `<prosody>` | Yes | Yes | Yes | Yes |
| `<phoneme>` | Yes | Yes | No | No |
| `<say-as>` | Yes | Yes | Yes | Yes |
| `<sub>` | Yes | Yes | No | No |
| `<w>` | Yes | Yes | No | No |
| `<amazon:effect>` | Yes | Yes | No | No |
| `<amazon:auto-breaths>` | Yes | No | No | No |

**The `<break>` and `<emphasis>` exclusion from non-standard
engines is the #1 deployment pitfall.** If the use case requires
precise pause timing or emphasis modulation, the standard engine
is the only option.

## Output format and sample rate coupling

| Output format | Valid sample rates | Audio type |
|---|---|---|
| mp3 | 22050, 24000 | Compressed, general-purpose |
| ogg_vorbis | 22050, 24000 | Compressed, web-optimized |
| pcm | 8000, 16000 | Raw, unheadered, telephony |
| json | N/A | Speech marks only (not audio) |

### Format selection guide

```text
Output format decision:
  ├── Web / mobile playback?
  │     → mp3 (broadest compatibility) or ogg_vorbis (smaller, web-native)
  ├── Telephony / IVR?
  │     → pcm at 8000 Hz (telephony standard)
  ├── Audio processing pipeline (raw samples)?
  │     → pcm at 16000 Hz (higher quality raw)
  └── Speech marks (lip-sync, captioning)?
        → json (NOT audio — separate request from audio synthesis)
```

### PCM caveat

PCM output is raw audio samples with NO header. To play a PCM file,
the player must know the sample rate and encoding (16-bit signed
little-endian mono). To convert PCM to WAV:

```bash
# Convert PCM to WAV (8000 Hz, 16-bit, mono)
ffmpeg -f s16le -ar 8000 -ac 1 -i output.pcm output.wav
```

## Quality vs cost trade-off

```text
Cost per 1 million characters (us-east-1):
  Standard:    $4.00    (baseline)
  Neural:      $16.00   (4x standard)
  Long-form:   $100.00  (25x standard)
  Generative:  $120.00  (30x standard)

Quality ranking (subjective, for conversational text):
  Generative ≈ Long-form > Neural > Standard

Decision framework:
  ├── IVR / telephony / high-volume notifications
  │     → Standard (cost dominates, quality adequate)
  ├── Customer-facing app / virtual assistant
  │     → Neural (quality matters, cost manageable)
  ├── Audiobook / podcast / long narration
  │     → Long-form (narrative quality justifies cost)
  └── Premium conversational AI / gaming
        → Generative (highest expressiveness)
```

## Terraform example

```hcl
# Upload a lexicon via local-exec
resource "null_resource" "polly_lexicon" {
  triggers = {
    content_hash = sha1(file("lexicons/company-terms.pls"))
  }

  provisioner "local-exec" {
    command = <<-EOF
      aws polly put-lexicon \
        --name company-terms \
        --content fileb://lexicons/company-terms.pls \
        --region ${var.region}
    EOF
  }
}

# CloudWatch alarm for character budget
resource "aws_cloudwatch_metric_alarm" "polly_budget" {
  alarm_name          = "polly-character-budget"
  namespace           = "AWS/Polly"
  metric_name         = "RequestCharacters"
  statistic           = "Sum"
  period              = 86400
  threshold           = 1000000
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
}
```
