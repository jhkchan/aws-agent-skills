---
name: polly-voice-deployer
description: 'Deploys Amazon Polly text-to-speech configurations with production defaults: engine selection (standard vs neural vs long-form vs generative), voice selection by language, SSML processing (phoneme, emphasis, break, prosody, say-as), lexicon management (custom pronunciation via PLS lexicons), speech marks generation for lip-sync and visual media sync, synthesize-speech API for real-time synthesis, start-speech-synthesis-task for asynchronous batch synthesis to S3, output formats (mp3, ogg_vorbis, pcm, json), sample rates (8000/16000/22050/24000), CloudWatch metrics monitoring, and pricing-per-character budgeting. Emits a READY_TO_DEPLOY checklist with verification commands. Use when configuring Polly TTS, synthesizing speech from text, deploying neural TTS voices, creating custom pronunciation lexicons, generating speech marks for lip-sync. Triggers: synthesize speech, polly neural voice, polly ssml, polly lexicon, speech marks, start speech synthesis task, polly engine selection, polly pricing per character.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with polly access and s3 PutObject on the output bucket. Works with Terraform aws_polly_lexicon resources and CloudFormation custom resources for Polly configurations.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AI/ML
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, polly, tts, cloudops, deploy, ai-ml, provisioning, neural-voice, ssml, lexicon, speech-marks
  dependencies: aws-orchestrator
  keywords: aws, polly, text to speech, tts, neural voice, cloudops, deploy, provisioning, ssml, lexicon, speech marks, synthesize speech, lip sync, pricing per character
  when_to_use: Invoke when the user wants to configure Amazon Polly for text-to-speech synthesis, select between standard/neural/long-form/ generative engines, use SSML tags for prosody control, create custom pronunciation lexicons, generate speech marks for lip-sync or captioning, run real-time synthesis via synthesize-speech, or batch-synthesize long text to S3 via start-speech-synthesis-task. Do NOT invoke for Amazon Transcribe (speech-to-text), Amazon Lex (conversational bots), or AWS Lambda function deployment.
---

# Polly Voice Deployer

An AWS CloudOps agent skill that deploys Amazon Polly text-to-speech
configurations with correct engine, voice, format, and pricing
defaults. The skill walks the operator through engine selection
(standard vs neural vs long-form vs generative), voice selection by
language and locale, SSML processing capabilities and per-engine
constraints, lexicon-based custom pronunciation, speech marks for
lip-sync alignment, the synthesize-speech real-time API vs the
start-speech-synthesis-task asynchronous API, output format and
sample rate selection, CloudWatch monitoring, and pricing-per-
character budgeting, captures all synthesis parameters, explains why
each default matters, and emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## Activation keywords

synthesize speech, polly neural voice, polly SSML, polly lexicon,
speech marks, start speech synthesis task, polly engine selection,
polly pricing per character.

## STRICT output contract

When this skill is invoked with a Polly text-to-speech deployment
request (synthesize speech, select an engine, configure SSML,
create a lexicon, generate speech marks, run a batch synthesis to
S3, or a partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `POLLY_VOICE:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-
based evals and downstream deployment pipelines rely on; deviating
from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before deployment |
| Step 1 — Engine selection (standard vs neural vs long-form vs generative) | Quality and cost decisions |
| Step 2 — Voice selection by language | Voice and locale matching |
| Step 3 — SSML processing (phoneme, emphasis, break, prosody) | Markup control |
| Step 4 — Lexicon management (custom pronunciation) | Pronunciation overrides |
| Step 5 — Speech marks (lip-sync alignment) | Visual media sync |
| Step 6 — synthesize-speech API (real-time) | Short-text synthesis |
| Step 7 — start-speech-synthesis-task (async to S3) | Long-text batch synthesis |
| Step 8 — Output format and sample rate | Audio encoding |
| Step 9 — CloudWatch metrics | Monitoring |
| Step 10 — Pricing per character | Cost budgeting |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/engine-and-voice-selection.md | Engine + voice detail |
| references/ssml-and-lexicons.md | SSML + lexicon detail |

## Mindset

**One-line takeaway:** Amazon Polly converts text to speech using
four engine types. Neural voices are higher quality but cost roughly
4x standard per character. SSML break and emphasis tags only work
with the standard engine. Lexicons map custom words to phonetic
equivalents. Speech marks are generated as a separate request and
returned as JSON line-delimited timestamps aligned to the audio.

Three misconceptions dominate Polly misdeployment at provisioning
time:

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#common-misconceptions-from-mindset).
> Three Polly misconceptions: neural SSML support, text-length limits, speech-mark delivery.

## Configuration dependency graph (novel heuristic)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#configuration-dependency-graph-sequencing-notes).
> How to sequence deployment using the dependency graph.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Engine selection | — (any engine can be chosen) | SSML `<break>` and `<emphasis>` silently ignored by neural/long-form/generative | voice list (per-engine voices differ) |
| Voice ID | engine must support the voice | requesting a standard-only voice with neural returns InvalidParameterValue | language and locale |
| Output format | — | pcm requires 8000/16000 sample rate; mp3/ogg support 22050/24000 | audio encoding |
| Sample rate | must be valid for output format | requesting 24000 with pcm silently coerces or errors | audio quality |
| Lexicon upload | lexicon Name must be unique in account+region | lexicon referenced in synthesis but not uploaded → synthesis fails with LexiconNotFound | custom pronunciation |
| SSML input | must be well-formed XML | `<break>`/`<emphasis>` silently ignored by neural engine | prosody control |
| Speech marks | separate synthesize-speech call with OutputFormat=json | requesting speech marks with OutputFormat=mp3 returns no marks | lip-sync / captioning |
| Async task (S3) | S3 bucket exists and Polly has WriteS3 access | task fails if S3 permissions missing; check task status | batch synthesis |

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#cross-dependency-gotchas).
> Baseline-miss rows and gotchas: engine/voice subsets, engine SSML support, format-rate coupling, separate marks call, per-region lexicons.

## Expert heuristic: engine selection decision tree

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-engine-selection-decision-tree).
> Engine selection balancing SSML needs, voice availability, and cost.

## Expert heuristic: real-time vs async synthesis

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-real-time-vs-async-synthesis).
> Real-time vs async path by text length and latency needs; marks are a separate request.

## Expert heuristic: pricing per character across engines

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-pricing-per-character-across-engines).
> Per-character pricing by engine with cost estimation and billing rules.

## Prerequisites (verify before deployment)

Before emitting deployment commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Input text available | Polly synthesizes from text input | Confirm text source and encoding (UTF-8) |
| Engine selected | Determines voice availability, SSML support, and cost | Decide: standard, neural, long-form, generative |
| Voice ID identified | Must be valid for the selected engine | `aws polly describe-voices --engine <engine>` |
| Language/locale matched | Voice must match the input text language | `aws polly describe-voices --language-code en-US` |
| Output format chosen | mp3, ogg_vorbis, pcm, or json (speech marks) | Decide based on downstream player |
| Sample rate valid for format | pcm = 8000/16000; mp3/ogg = 22050/24000 | Match format to rate |
| SSML tags engine-compatible | `<break>`/`<emphasis>` only work with standard engine | Verify engine if SSML uses these tags |
| S3 output bucket (async task) | Batch synthesis writes to S3 | `aws s3 ls s3://<bucket>` |
| IAM permissions | polly:SynthesizeSpeech or polly:StartSpeechSynthesisTask | Verify IAM policy |
| Lexicon uploaded (if referenced) | Lexicon must exist before synthesis calls it | `aws polly list-lexicons` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Engine selection (standard vs neural vs long-form vs generative)

Amazon Polly offers four TTS engines. Each has different quality,
voice availability, SSML support, and pricing.

| Engine | Quality | Voice availability | SSML support | Cost (per 1M chars) |
|---|---|---|---|---|
| standard | Good | ALL voices (all languages) | Full SSML (`<break>`, `<emphasis>`, `<prosody>`, `<phoneme>`, `<say-as>`) | $4.00 |
| neural | High | Subset of voices | Partial (`<prosody>`, `<phonome>`, `<say-as>`; NOT `<break>`, `<emphasis>`) | $16.00 |
| long-form | Highest (narrative) | Small subset (long-form-optimized voices) | Partial (`<prosody>`; NOT `<break>`, `<emphasis>`) | $100.00 |
| generative | Highest (conversational) | Small subset (generative voices) | Partial (`<prosody>`; NOT `<break>`, `<emphasis>`) | $120.00 |

**Critical SSML constraint:** the `<break>` and `<emphasis>` tags
are ONLY processed by the standard engine. Neural, long-form, and
generative engines silently ignore these tags. If the use case
requires precise pause control, the standard engine is mandatory.

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-1-engine-and-voice-discovery-commands).
> describe-voices listings per engine for voice discovery.

## Step 2 — Voice selection by language

Each Polly voice is identified by a Voice ID (e.g., `Joanna`,
`Matthew`, `Lupe`). Voices are language-specific. Not all voices
are available for all engines.

| Language code | Example voices | Neural available |
|---|---|---|
| en-US | Joanna, Matthew, Stephen, Kevin, Danielle, Gregory | Yes (Joanna, Matthew, Stephen, Kevin, Danielle, Gregory) |
| en-GB | Amy, Emma, Brian | Yes (Amy, Emma, Brian) |
| en-AU | Nicole, Olivia | Yes (Nicole, Olivia) |
| es-US | Lupe, Miguel, Penelope, Lucia, Diego | Partial (Lupe, Lucia, Diego) |
| fr-FR | Lea, Remi | Yes (Lea, Remi) |
| de-DE | Vicki, Daniel | Yes (Vicki, Daniel) |
| ja-JP | Kazuha, Tomoko | Partial |
| ko-KR | Seoyeon | Yes |
| zh-CN | Zhiyu | Yes |

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-2-voice-discovery-by-language-commands).
> describe-voices by language-code and per-voice neural support check.

**Select a voice that:**
1. Matches the input text language (language-code).
2. Is available on the chosen engine.
3. Has the desired gender and style.

## Step 3 — SSML processing (phoneme, emphasis, break, prosody)

SSML (Speech Synthesis Markup Language) provides fine-grained control
over pronunciation, pacing, emphasis, and prosody. Polly supports a
subset of SSML tags.

| SSML tag | Purpose | Engine support |
|---|---|---|
| `<break>` | Insert a pause (e.g., `<break time="500ms"/>`) | Standard ONLY |
| `<emphasis>` | Emphasize a word (e.g., `<emphasis level="strong">important</emphasis>`) | Standard ONLY |
| `<prosody>` | Control rate, pitch, volume (e.g., `<prosody rate="slow">text</prosody>`) | ALL engines |
| `<phoneme>` | Phonetic pronunciation via IPA (e.g., `<phoneme alphabet="ipa" ph="ˈtɒmɑtəʊ">tomato</phoneme>`) | Standard + Neural |
| `<say-as>` | Interpret text type (e.g., `<say-as interpret-as="date" format="mdy">01/15/2024</say-as>`) | ALL engines |
| `<speak>` | Root SSML element (wraps all SSML) | ALL engines |
| `<sub>` | Substitute pronunciation (e.g., `<sub alias=" Avenue">Ave</sub>`) | Standard + Neural |
| `<w>` | Part-of-speech override | Standard + Neural |
| `<amazon:effect>` | Whisper, dynamical range compression | Standard + Neural |

> Moved to [references/ssml-and-lexicons.md](references/ssml-and-lexicons.md#step-3-ssml-examples-standard-vs-neural).
> Full-tag SSML for standard engine; prosody/phoneme-only SSML for neural.

**Critical:** if the SSML uses `<break>` or `<emphasis>` and the
engine is neural/long-form/generative, the tags are silently ignored.
The synthesis succeeds but the pauses and emphasis do not appear in
the output audio. This is the #1 Polly deployment surprise.

## Step 4 — Lexicon management (custom pronunciation)

Lexicons (PLS — Pronunciation Lexicon Specification) allow custom
pronunciation mappings. A lexicon maps a word to its phonetic
equivalent so that Polly pronounces it correctly every time.

**Lexicon use cases:**
- Company names, product names, and acronyms.
- Domain-specific terminology (medical, legal, technical).
- Regional pronunciation variants.

> Moved to [references/ssml-and-lexicons.md](references/ssml-and-lexicons.md#step-4-lexicon-management-commands).
> PLS lexicon file, put-lexicon upload, lexicon use in synthesis, list/get verification, constraints.

## Step 5 — Speech marks (lip-sync alignment)

Speech marks are timestamp-aligned markers that map text positions
to audio positions. They are essential for lip-sync animation,
captioning, and highlighting text as audio plays.

**Speech mark types:**

| Type | Description | Use case |
|---|---|---|
| `viseme` | Visual mouth-shape codes for animation | 3D avatar lip-sync |
| `word` | Word-level start/end timestamps | Text highlighting, caption sync |
| `sentence` | Sentence boundaries | Caption segmentation |
| `ssml` | SSML tag timestamps | SSML mark navigation |

> Moved to [references/worked-examples.md](references/worked-examples.md#step-5-speech-marks-generation-and-output).
> Speech-mark synthesis command, line-delimited JSON output, and field semantics.

**Critical:** speech marks are generated as a SEPARATE call from the
audio. The audio synthesis (OutputFormat=mp3) and the marks
synthesis (OutputFormat=json) must use the SAME engine, voice, text,
sample rate, and lexicons for the timestamps to align correctly.

## Step 6 — synthesize-speech API (real-time)

The `synthesize-speech` API is the real-time synthesis endpoint. It
returns the audio stream directly in the HTTP response. Use for
short text (under ~3000 characters) where low latency is required.

> Moved to [references/worked-examples.md](references/worked-examples.md#step-6-synthesize-speech-real-time-examples).
> Plain-text, SSML, and lexicon real-time synthesis invocations.

**API constraints:**
- Maximum input text length: ~3000 characters (varies by configuration).
- Returns audio as a binary stream in the response body.
- Synchronous — the caller waits for synthesis to complete.
- Latency: typically 200-600ms for neural, 100-300ms for standard.

## Step 7 — start-speech-synthesis-task (async to S3)

The `start-speech-synthesis-task` API is the asynchronous synthesis
endpoint for long text. It writes the output audio file to a
specified S3 bucket. Use for batch processing, long-form content
(articles, books), and pre-generation of audio assets.

> Moved to [references/worked-examples.md](references/worked-examples.md#step-7-async-synthesis-task-commands).
> start-speech-synthesis-task with S3 output, status check, and task listing.

**Task lifecycle:**
- `scheduled` → `queued` → `inProgress` → `completed` | `failed`
- On completion, the audio file is available at the S3 URI:
  `s3://<bucket>/<key-prefix>/<task-id>.mp3`

**S3 IAM permissions required:**
Polly needs `s3:PutObject` on the output bucket. The service-linked
role `PollySynthesisTaskServiceRole` is typically auto-managed.

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-7-verify-async-task-s3-output).
> S3 listing check for the completed async synthesis output.

## Step 8 — Output format and sample rate

Output format and sample rate are coupled. Not all combinations are
valid.

| Output format | Valid sample rates | Use case |
|---|---|---|
| mp3 | 22050, 24000 | General-purpose audio playback |
| ogg_vorbis | 22050, 24000 | Web audio, streaming |
| pcm | 8000, 16000 | Telephony, raw audio processing |
| json | N/A (speech marks only) | Speech marks / lip-sync |

> Moved to [references/worked-examples.md](references/worked-examples.md#step-8-output-format-and-sample-rate-examples).
> Telephony PCM 8000 Hz and high-quality MP3 24000 Hz synthesis.

**Mismatching format and sample rate** (e.g., PCM at 24000 Hz) will
produce an error or silently coerce the output.

## Step 9 — CloudWatch metrics

Polly publishes metrics to CloudWatch for monitoring synthesis
volume, errors, and latency.

| Metric | Description |
|---|---|
| `RequestCharacters` | Total characters processed (for billing estimation) |
| `ResponseLatency` | Average synthesis latency |
| `2XXCount` / `4XXCount` / `5XXCount` | HTTP response code counts |
| `ThrottledCount` | Throttled request count (if exceeding limits) |

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-9-cloudwatch-metrics-commands).
> get-metric-statistics for RequestCharacters and a character-budget billing alarm.

## Step 10 — Pricing per character

Polly pricing is per-character of input text. SSML tags are NOT
counted — only the text content between tags.

| Engine | Price per 1M characters (us-east-1) | Notes |
|---|---|---|
| standard | $4.00 | All voices, full SSML |
| neural | $16.00 | 4x standard; subset of voices |
| long-form | $100.00 | Audiobook-quality narration |
| generative | $120.00 | Most expressive conversational voices |

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-10-pricing-estimation-commands).
> Character-count and monthly cost estimation one-liners.

**Free tier:** 5 million characters per month for standard voices,
1 million characters per month for neural voices (for the first 12
months).

## Step 11 — Recent features

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-11-recent-features).
> Recent AWS features (2023-2026): generative engine, long-form enhancements, neural expansion, enhanced metrics, SSE-KMS, viseme improvements.

## NEVER do these things

1. **NEVER use `<break>` or `<emphasis>` SSML tags with neural,
   long-form, or generative engines.** These tags are ONLY processed
   by the standard engine. Neural and others silently ignore them.
   If the use case requires pause control, use standard engine or
   `<prosody rate>` for timing adjustment.

2. **NEVER assume speech marks are returned with the audio.** Speech
   marks are a SEPARATE `synthesize-speech` call with
   `OutputFormat=json` and `SpeechMarkTypes` specified. The audio
   and marks are two different requests.

3. **NEVER use `synthesize-speech` for long text (>3000 chars).**
   The real-time API has a payload limit. For longer text, use
   `start-speech-synthesis-task` which writes to S3 and handles
   arbitrarily long input.

4. **NEVER request a sample rate incompatible with the output
   format.** PCM supports only 8000 and 16000 Hz. MP3 and OGG
   support 22050 and 24000 Hz. Mismatching produces errors or
   silent coercion.

5. **NEVER assume all voices are available on all engines.** Neural,
   long-form, and generative each support a SUBSET of the standard
   voice catalog. Always verify with `describe-voices --engine`.

6. **NEVER assume lexicons are global.** Lexicons are per-region.
   A lexicon uploaded in us-east-1 is NOT available in eu-west-1.
   Upload to each region where needed.

7. **NEVER forget to verify the S3 output for async tasks.** The
   task may fail due to IAM permissions or bucket policy. Always
   check `get-speech-synthesis-task` status and verify the S3
   object exists.

8. **NEVER estimate cost without checking the engine rate.** Neural
   is 4x standard, long-form is 25x standard, generative is 30x
   standard. High-volume workloads must budget by engine.

9. **NEVER use PCM output for web playback.** PCM is raw, unheadered
   audio. Use MP3 or OGG for web and mobile applications. PCM is
   for telephony and audio processing pipelines.

10. **NEVER reference a lexicon before uploading it.** The synthesis
    call will fail with `LexiconNotFound`. Always `put-lexicon`
    before referencing it in `synthesize-speech`.

## Output format

```text
POLLY_VOICE: <voice-id> (<engine> engine, <language-code>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Engine: standard | neural | long-form | generative
  [✓|✗] Voice: <voice-id> (<language-code>, <gender>)
  [✓|✗] Voice available on engine: PASS | FAIL (voice not supported)
  [✓|✗] SSML compatibility: <tags used> — PASS (all tags supported) | FAIL (<break>/<emphasis> not supported on neural)
  [✓|✗] Output format: mp3 | ogg_vorbis | pcm | json
  [✓|✗] Sample rate: <rate> Hz — PASS (valid for format) | FAIL (invalid for format)
  [✓|✗] Lexicon: <name> — uploaded | not referenced
  [✓|✗] Synthesis mode: real-time (synthesize-speech) | async (start-speech-synthesis-task → s3://<bucket>/<key>)
  [✓|✗] Speech marks: <types> (separate request) | not required
  [✓|✗] Estimated cost: $<amount> (<char-count> chars × $<rate>/1M)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws polly describe-voices --engine <engine> --query 'Voices[?Id==`<voice-id>`]'
  aws polly list-lexicons --query 'Lexicons[?Name==`<lexicon>`]'
  aws polly get-speech-synthesis-task --task-id <task-id>
```

### Worked example — neural voice real-time synthesis

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
  [✓] Estimated cost: $0.00 (52 chars × $16/1M = $0.000832)
  [✓] Tags: Environment=production, UseCase=greeting
VERIFICATION_COMMANDS:
  aws polly describe-voices --engine neural --query 'Voices[?Id==`Joanna`]'
  aws polly list-lexicons --query 'Lexicons[?Name==`company-terms`]'
```

## Error handling

> Moved to [references/error-handling.md](references/error-handling.md#error-handling).
> Symptom-by-symptom fixes: missing pauses, S3 access denied, voice/lexicon not found, empty marks, garbled PCM.
## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — expert-heuristic deep dives, misconceptions, dependency-graph notes, recent AWS features (2023-2026)
- [worked-examples](references/worked-examples.md) — filled-in synthesis examples (speech marks, real-time, async, output formats)
- [diagnostic-commands](references/diagnostic-commands.md) — voice discovery, task verification, CloudWatch, and pricing commands
- [error-handling](references/error-handling.md) — symptom-by-symptom troubleshooting
- [engine-and-voice-selection](references/engine-and-voice-selection.md) — engine and voice selection detail (existing)
- [ssml-and-lexicons](references/ssml-and-lexicons.md) — SSML and lexicon detail plus examples (existing)

## Domain

AWS CloudOps / Amazon Polly Text-to-Speech Configuration & Voice
Synthesis Deployment.

## AWS documentation

- **Amazon Polly Developer Guide** — https://docs.aws.amazon.com/polly/latest/dg/what-is.html
- **Synthesize speech** — https://docs.aws.amazon.com/polly/latest/dg/API_SynthesizeSpeech.html
- **Start speech synthesis task** — https://docs.aws.amazon.com/polly/latest/dg/API_StartSpeechSynthesisTask.html
- **SSML tags** — https://docs.aws.amazon.com/polly/latest/dg/ssml.html
- **Lexicons** — https://docs.aws.amazon.com/polly/latest/dg/managing-lexicons.html
- **Speech marks** — https://docs.aws.amazon.com/polly/latest/dg/speechmarks.html
- **Voice list** — https://docs.aws.amazon.com/polly/latest/dg/voicelist.html
- **Engine types** — https://docs.aws.amazon.com/polly/latest/dg/choosing-the-engine.html
- **Pricing** — https://aws.amazon.com/polly/pricing/
- **CloudWatch metrics** — https://docs.aws.amazon.com/polly/latest/dg/cloudwatch-monitoring.html
