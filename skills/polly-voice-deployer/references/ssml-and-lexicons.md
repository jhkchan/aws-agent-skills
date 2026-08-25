# SSML and Lexicons — Polly Voice Deployer

Deep reference on SSML (Speech Synthesis Markup Language) processing
in Polly, per-engine tag constraints, lexicon (PLS) management for
custom pronunciation, speech marks generation, and the two-request
pattern for synchronized audio + marks. Loaded on demand by the
skill — kept out of the main SKILL.md body so the deployment
procedure stays scannable.

## SSML fundamentals

### What SSML is

SSML is a W3C standard XML-based markup language for controlling
speech synthesis. Polly supports a subset of SSML 1.1. The input
text type is set via `--text-type ssml` on the CLI or
`TextType: ssml` in the API.

### Root element

All SSML input must be wrapped in `<speak>` tags:

```xml
<speak>
  Your text here.
</speak>
```

Without the `<speak>` root, Polly treats the input as plain text
even if `--text-type ssml` is specified.

## SSML tags in detail

### `<break>` — insert a pause (standard engine ONLY)

```xml
<speak>
  First sentence.
  <break time="500ms"/>
  Second sentence after a pause.
  <break strength="strong"/>
  Third sentence after a strong pause.
</speak>
```

**Attributes:**
- `time`: duration (e.g., `500ms`, `2s`).
- `strength`: `none`, `x-weak`, `weak`, `medium`, `strong`, `x-strong`.

**Engine support:** standard ONLY. Neural, long-form, and generative
silently ignore this tag.

### `<emphasis>` — emphasize a word (standard engine ONLY)

```xml
<speak>
  This is <emphasis level="strong">very important</emphasis>.
</speak>
```

**Attributes:**
- `level`: `strong`, `moderate`, `reduced`.

**Engine support:** standard ONLY. Neural, long-form, and generative
silently ignore this tag.

### `<prosody>` — control rate, pitch, volume (ALL engines)

```xml
<speak>
  <prosody rate="slow" pitch="-2st" volume="loud">
    Spoken slowly, lower pitch, and louder.
  </prosody>
</speak>
```

**Attributes:**
- `rate`: `x-slow`, `slow`, `medium`, `fast`, `x-fast`, or percentage
  (e.g., `90%`).
- `pitch`: `x-low`, `low`, `medium`, `high`, `x-high`, or semitone
  offset (e.g., `+5st`, `-2st`).
- `volume`: `silent`, `x-soft`, `soft`, `medium`, `loud`, `x-loud`,
  or relative dB (e.g., `+3dB`).

**Engine support:** ALL engines (standard, neural, long-form,
generative). This is the cross-engine alternative to `<break>` and
`<emphasis>`.

### `<phoneme>` — phonetic pronunciation

```xml
<speak>
  <phoneme alphabet="ipa" ph="ˈtɒmɑtəʊ">tomato</phoneme>
  <phoneme alphabet="x-sampa" ph="t@meiToU">tomato</phoneme>
</speak>
```

**Attributes:**
- `alphabet`: `ipa` or `x-sampa`.
- `ph`: the phonetic transcription.

**Engine support:** standard + neural. Not long-form or generative.

### `<say-as>` — interpret text type

```xml
<speak>
  <say-as interpret-as="date" format="mdy">01/15/2024</say-as>
  <say-as interpret-as="cardinal">12345</say-as>
  <say-as interpret-as="ordinal">3</say-as>
  <say-as interpret-as="telephone">+1-555-123-4567</say-as>
  <say-as interpret-as="spell-out">AWS</say-as>
</speak>
```

**Attributes:**
- `interpret-as`: `date`, `cardinal`, `ordinal`, `telephone`,
  `spell-out`, `unit`, `digits`, `fraction`, `expletive`, `address`,
  `interjection`.
- `format` (for dates): `mdy`, `dmy`, `ymd`, `md`, `dm`, `ym`, `my`,
  `y`, `m`, `d`.

**Engine support:** ALL engines.

### `<sub>` — substitute pronunciation

```xml
<speak>
  I live on Park <sub alias="Avenue">Ave</sub>.
  The <sub alias="Doctor">Dr.</sub> is in.
</speak>
```

**Engine support:** standard + neural.

## Lexicon management (PLS)

### What lexicons are

Lexicons use the W3C Pronunciation Lexicon Specification (PLS) to
map written words (graphemes) to custom pronunciations (aliases or
phonetic transcriptions). This is useful for:

- Company names and product names (e.g., "AWS" → "A W S").
- Domain terminology (medical, legal, technical).
- Acronyms and abbreviations.
- Regional pronunciation variants.

### PLS lexicon format

```xml
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
  <lexeme>
    <grapheme>S3</grapheme>
    <phoneme>ɛs θriː</phoneme>
  </lexeme>
</lexicon>
```

### Upload and manage lexicons

```bash
# Upload a lexicon
aws polly put-lexicon \
  --name company-terms \
  --content fileb://company-terms.pls

# List all lexicons
aws polly list-lexicons \
  --query 'Lexicons[*].{Name:Name,LanguageCode:Attributes.LanguageCode}' \
  --output table

# Get a specific lexicon's content
aws polly get-lexicon --name company-terms

# Delete a lexicon
aws polly delete-lexicon --name company-terms
```

### Using lexicons in synthesis

```bash
aws polly synthesize-speech \
  --engine standard \
  --voice-id Joanna \
  --output-format mp3 \
  --sample-rate 24000 \
  --lexicon-names company-terms \
  --text "Welcome to AWS. Your EC2 instance is ready." \
  output.mp3
```

Up to 5 lexicons can be referenced in a single synthesis call:

```bash
--lexicon-names company-terms medical-terms name-pronunciations
```

### Lexicon constraints

- **Per-region:** lexicons are stored per-region. Upload to each
  region where they are needed.
- **Per-account:** lexicons are scoped to the account that uploaded
  them.
- **Name uniqueness:** lexicon names must be unique within an
  account and region.
- **Size limit:** maximum 100,000 characters per lexicon.
- **Lexeme limit:** maximum 50,000 lexemes per lexicon.
- **Engine compatibility:** lexicons work with ALL engines
  (standard, neural, long-form, generative).

## Speech marks

### What speech marks are

Speech marks are timestamp-aligned markers that map text positions
to audio positions. They are essential for:

- **Lip-sync animation:** viseme marks drive mouth shapes.
- **Captioning:** word and sentence marks align text to audio.
- **Text highlighting:** karaoke-style text highlighting as audio
  plays.

### Speech mark types

| Type | Description | Fields |
|---|---|---|
| `viseme` | Mouth shape code (from a set of 15 Polly visemes) | `time`, `value` (viseme code) |
| `word` | Word boundary | `time`, `start`, `end` (char positions) |
| `sentence` | Sentence boundary | `time`, `start`, `end` |
| `ssml` | SSML tag position | `time`, `value` (tag name) |

### Generating speech marks (separate request)

Speech marks are generated as a SEPARATE call from the audio:

```bash
# Request 1: Audio
aws polly synthesize-speech \
  --engine neural \
  --voice-id Joanna \
  --output-format mp3 \
  --sample-rate 24000 \
  --text "Hello world. This is a test." \
  audio.mp3

# Request 2: Speech marks (same engine, voice, text, sample rate)
aws polly synthesize-speech \
  --engine neural \
  --voice-id Joanna \
  --output-format json \
  --sample-rate 24000 \
  --speech-mark-types '["word","sentence","viseme"]' \
  --text "Hello world. This is a test." \
  marks.json
```

### Output format (line-delimited JSON)

```json
{"time":0,"type":"sentence","start":0,"end":27}
{"time":0,"type":"word","start":0,"end":5}
{"time":148,"type":"viseme","start":0,"end":5,"value":"p"}
{"time":200,"type":"word","start":6,"end":11}
{"time":370,"type":"viseme","start":6,"end":11,"value":"t"}
{"time":450,"type":"sentence","start":0,"end":27}
```

- `time`: milliseconds from the start of the audio.
- `start`/`end`: character positions in the input text.
- `value`: viseme code (for viseme marks only).

### Critical alignment requirement

The speech marks request MUST use the same engine, voice ID, input
text, sample rate, and lexicons as the audio request. Any difference
will cause the timestamps to drift and the marks will not align
with the audio.

### Polly viseme set

Polly uses 15 viseme codes mapped to IPA mouth shapes:

| Viseme | Mouth shape | Example sound |
|---|---|---|
| `p` | Lips together | p, b, m |
| `f` | Lower lip to teeth | f, v |
| `T` | Tongue between teeth | th |
| `s` | Tongue near alveolar | s, z |
| `t` | Tongue tip up | t, d, n, l |
| `S` | Tongue further back | sh, zh |
| `k` | Tongue back up | k, g, ng |
| `i` | Lips spread | i, ee |
| `e` | Slightly spread | e, ay |
| `a` | Open mouth | a, ah |
| `o` | Rounded lips | o, oh |
| `u` | Tightly rounded | u, oo |
| `O` | Very open rounded | aw, ow |
| `r` | Tongue curled | r, er |
| `sil` | Silence (mouth closed) | pause |

## Common pitfalls

### Pitfall 1: `<break>` on neural engine

The synthesis succeeds but the pause is absent. The operator does
not notice until playback. **Fix:** use standard engine for `<break>`,
or use `<prosody rate="slow">` on neural for timing.

### Pitfall 2: Speech marks not aligning with audio

The marks request used a different engine, voice, or sample rate
than the audio request. **Fix:** ensure both requests use identical
parameters.

### Pitfall 3: Lexicon not found

The lexicon was uploaded in a different region. **Fix:** upload the
lexicon in each region where synthesis runs. Verify with
`list-lexicons`.

### Pitfall 4: SSML not parsed (plain text output)

The `--text-type ssml` flag was omitted. Polly treats the input as
plain text and reads the SSML tags literally. **Fix:** always
specify `--text-type ssml` when using SSML markup.


## Step 3 — SSML examples (standard vs neural)

**Example SSML for standard engine (full tag support):**

```xml
<speak>
  Welcome to the service.
  <break time="500ms"/>
  Please listen <emphasis level="strong">carefully</emphasis>.
  <prosody rate="90%" pitch="+5%">This is the important part.</prosody>
  The word <phoneme alphabet="ipa" ph="ˈtɒmɑtəʊ">tomato</phoneme>
  is pronounced differently in British English.
</speak>
```

**Example SSML for neural engine (no break/emphasis):**

```xml
<speak>
  Welcome to the service.
  Please listen carefully.
  <prosody rate="90%" pitch="+5%">This is the important part.</prosody>
  The word <phoneme alphabet="ipa" ph="ˈtɒmɑtəʊ">tomato</phoneme>
  is pronounced differently in British English.
</speak>
```


## Step 4 — Lexicon management commands

**Upload a lexicon:**

```bash
# Create a PLS lexicon file
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
  <lexeme>
    <grapheme>S3</grapheme>
    <phoneme>ɛs θriː</phoneme>
  </lexeme>
</lexicon>
EOF

# Upload the lexicon to Polly
aws polly put-lexicon \
  --name company-terms \
  --content fileb://company-terms.pls
```

**Use a lexicon in synthesis:**

```bash
aws polly synthesize-speech \
  --engine standard \
  --voice-id Joanna \
  --output-format mp3 \
  --sample-rate 24000 \
  --lexicon-names company-terms \
  --text "Welcome to AWS. Your EC2 instance on S3 is ready." \
  output.mp3
```

**List and verify lexicons:**

```bash
# List all lexicons in the account+region
aws polly list-lexicons \
  --query 'Lexicons[*].Name' --output table

# Get details of a specific lexicon
aws polly get-lexicon --name company-terms
```

**Lexicon constraints:**
- Lexicons are per-region. Upload to each region where they are
  needed.
- Lexicon names must be unique within an account and region.
- A synthesis request can reference up to 5 lexicons.
- Lexicons apply to all engines (standard, neural, long-form).
