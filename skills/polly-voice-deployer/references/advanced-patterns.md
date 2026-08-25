# Advanced Patterns — Polly Voice Deployer

Deep-dive material moved out of the SKILL.md body so the procedure stays scannable. Loaded on demand.


## Common misconceptions (from Mindset)

- **"Neural voices support all SSML tags."** They do not. The
  `<break>` and `<emphasis>` tags only work with the standard engine.
  Neural, long-form, and generative engines ignore these tags
  silently. If the use case requires precise pause control or
  emphasis modulation, use the standard engine or use `<prosody>`
  (which works across engines) for rate and pitch adjustments.

- **"Synthesize-speech can handle any text length."** It cannot.
  The real-time `synthesize-speech` API has a payload limit (~3000
  characters for most configurations). For longer text (articles,
  books, scripts), use the asynchronous `start-speech-synthesis-task`
  API which writes the output to S3 and handles arbitrarily long
  input within the service's maximum.

- **"Speech marks are returned with the audio."** They are not.
  Speech marks (word-level, sentence-level, viseme-level, SSML-tag
  timestamps) are generated as a SEPARATE `synthesize-speech` request
  with `OutputFormat=json` and `SpeechMarkTypes` specified. The
  marks are line-delimited JSON, each with `time`, `type`, `start`,
  and `end` fields, aligned to the corresponding audio file.


## Configuration dependency graph — sequencing notes

Polly configurations are NOT independent. Engine choice constrains
available voices AND SSML tag support. Voice choice constrains
language. Output format constrains sample rate. Lexicons must be
uploaded before synthesis references them. Speech marks require a
separate request. Use this graph to sequence deployment.


## Cross-dependency gotchas

**The SSML-break-on-neural row is the one a baseline model misses.**
The SSML `<break>` and `<emphasis>` tags are widely documented but
only work with the standard engine. A naive deployment specifies
neural for quality and includes `<break time="500ms"/>` in the
SSML — the synthesis succeeds but the pause is silently omitted.
The procedure below forces an explicit engine-vs-SSML compatibility
check.

**Cross-dependency gotchas:**
- Engine determines available voices. Neural, long-form, and
  generative each have a SUBSET of the standard voice catalog. Not
  all standard voices have neural equivalents.
- Engine determines SSML support. `<break>` and `<emphasis>` are
  standard-engine-only. `<prosody>` works on all engines.
- Output format and sample rate are coupled. PCM supports only
  8000 and 16000 Hz. MP3 and OGG support 22050 and 24000 Hz.
- Speech marks use `OutputFormat=json` — this is a DIFFERENT call
  from the audio synthesis. The marks align to the audio by
  timestamp.
- Lexicons are per-region. A lexicon uploaded in us-east-1 is not
  available in eu-west-1.


## Expert heuristic: engine selection decision tree

A baseline model says "use neural for better quality." The correct
heuristic considers SSML requirements, voice availability, and cost.

```text
Engine selection:
  ├── Need <break> or <emphasis> SSML tags?
  │     → MUST use standard engine (these tags ignored by neural/long-form/generative)
  ├── Need highest conversational quality for long-form content (audiobooks, podcasts)?
  │     → long-form engine (supports select voices, higher quality prosody)
  ├── Need newest generative voices (conversational, expressive)?
  │     → generative engine (limited voice set, highest quality)
  ├── Need broad language/voice coverage at lower cost?
  │     → standard engine (all languages, all voices, lowest cost)
  ├── Need neural quality with <prosody> for rate/pitch?
  │     → neural engine (<prosody> works; <break>/<emphasis> do NOT)
  └── Cost-sensitive, high-volume?
        → standard engine (4x cheaper than neural per character)
```

**Key implication:** if the use case requires precise pause control
via `<break>`, the operator MUST choose standard engine. There is
no workaround for neural. For rate/pitch modulation, `<prosody>`
works across engines and is the cross-engine alternative.


## Expert heuristic: real-time vs async synthesis

The choice between `synthesize-speech` and `start-speech-synthesis-
task` depends on text length and latency requirements.

```text
Synthesis path:
  ├── Text < 3000 chars AND need real-time response?
  │     → synthesize-speech API (returns audio stream directly in the response)
  ├── Text > 3000 chars OR batch processing acceptable?
  │     → start-speech-synthesis-task (async, writes to S3)
  │        Task status: queued → inProgress → completed | failed
  │        Check: get-speech-synthesis-task --task-id <id>
  ├── Need speech marks (lip-sync)?
  │     → SEPARATE synthesize-speech call with OutputFormat=json
  │        Audio and marks are two different requests
  └── Need both audio AND marks for the same text?
        → Two calls: one for audio (OutputFormat=mp3), one for marks (OutputFormat=json)
```

**Key implication:** speech marks are NEVER returned with the audio
stream. They are a separate request. The timestamps in the marks
file align to the audio file's timeline.


## Expert heuristic: pricing per character across engines

Polly pricing is per-character of INPUT text (not per second of
output audio). Engine and region affect the rate.

```text
Pricing (us-east-1, approximate):
  Standard engine:  $4.00 per 1 million characters
  Neural engine:    $16.00 per 1 million characters (4x standard)
  Long-form engine: $100.00 per 1 million characters
  Generative engine:$120.00 per 1 million characters

  Cost estimation:
    10,000 chars × standard  = $0.04
    10,000 chars × neural    = $0.16
    10,000 chars × long-form = $1.00

  SSML tags are NOT counted in character pricing — only the text
  content between tags is billed. Lexicon names and speech mark
  requests are billed at the same per-character rate.
```

**Key implication:** the 4x cost difference between standard and
neural is the dominant budget factor. For high-volume workloads,
standard may be sufficient. For user-facing conversational quality,
neural or long-form is worth the premium.


## Step 11 — Recent features

**Recent AWS features (2023-2026):**

- **Generative engine (2024-2025):** New engine type using
  diffusion-based models for the most natural, expressive, and
  conversational voices. Limited voice set (expanding). Highest cost
  per character but highest quality.

- **Long-form engine enhancements (2023-2024):** Improved prosody
  for narrated content (audiobooks, podcasts). The long-form engine
  produces more natural pacing and intonation for paragraph-length
  text compared to neural.

- **Neural voice expansion (2023-2024):** Additional neural voices
  added across multiple languages, including new conversational
  styles for customer service and gaming.

- **CloudWatch enhanced metrics (2023-2024):** Per-engine and per-
  voice metric dimensions for granular cost attribution.

- **S3 output SSE-KMS support (2023-2024):** Async synthesis tasks
  now support server-side encryption with KMS-managed keys
  (SSE-KMS) on the output S3 bucket.

- **Speech mark viseme improvements (2024-2025):** Additional
  viseme codes for improved 3D avatar lip-sync accuracy, including
  support for more languages.
