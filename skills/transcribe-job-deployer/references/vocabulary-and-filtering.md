# Custom Vocabulary and Vocabulary Filtering — Transcribe Job Deployer

Deep reference on custom vocabularies (word boosting for domain
terms), vocabulary filters (masking/removing unwanted words), the
relationship between the two, vocabulary file formats, creation
and management, and applying them to transcription jobs. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
deployment procedure stays scannable.

## Custom vocabulary fundamentals

### What a custom vocabulary does

A custom vocabulary tells Transcribe to recognize and correctly
render specific words that the base model may struggle with:
acronyms, product names, domain terminology, and proper nouns. It
does NOT change overall accuracy — it boosts specific terms.

### Creating a custom vocabulary

#### Method 1: Phrase list (simple)

For simple word boosting without pronunciation overrides:

```bash
aws transcribe create-vocabulary \
  --vocabulary-name company-terms \
  --language-code en-US \
  --phrases "AWS" "EC2" "S3" "DynamoDB" "Lambda" "CloudFormation"
```

#### Method 2: Vocabulary file (advanced)

For entries with pronunciation overrides, display-as overrides,
or IPA phonetic transcription. The file is a tab-delimited table
on S3:

**Format:**

```
Phrase\tSoundsLike\tIPA\tDisplayAs
ec2\te c two\t\tEC2
s3\ts three\t\tS3
quinoa\t\tˈkiːnwɑː\tquinoa
Aortic stenosis\taortic stenosis\t\tAS
```

| Column | Description | Required |
|---|---|---|
| `Phrase` | The word or phrase as it appears in the audio | Yes |
| `SoundsLike` | How the word sounds (hyphenated syllables) | Optional |
| `IPA` | IPA phonetic transcription | Optional |
| `DisplayAs` | How the word should appear in the transcript | Optional |

```bash
# Upload the vocabulary file to S3 first
aws s3 cp medical-terms.txt s3://my-vocab-bucket/medical-terms.txt

# Create the vocabulary from the file
aws transcribe create-vocabulary \
  --vocabulary-name medical-terms \
  --language-code en-US \
  --vocabulary-file-uri s3://my-vocab-bucket/medical-terms.txt
```

### Vocabulary lifecycle

```text
PENDING → READY → FAILED
         (ready for use in jobs)
```

```bash
# Check vocabulary status
aws transcribe get-vocabulary \
  --vocabulary-name company-terms \
  --query 'VocabularyState' --output text
# Must return "READY" before referencing in a job

# List all vocabularies
aws transcribe list-vocabularies \
  --query 'Vocabularies[*].{Name:VocabularyName,State:VocabularyState,Language:LanguageCode}' \
  --output table

# Delete a vocabulary
aws transcribe delete-vocabulary \
  --vocabulary-name company-terms
```

### Applying a custom vocabulary

```bash
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --language-code en-US \
  --settings VocabularyName=company-terms \
  --output-bucket-name my-output-bucket
```

### Vocabulary constraints

- Language-specific: a vocabulary for en-US cannot be used with
  other languages.
- Must be READY before referencing in a job (takes seconds to
  minutes to process).
- Maximum 100 KB for phrase-list method.
- Maximum 100,000 characters for the vocabulary file.
- Works with standard transcription AND medical transcription.
- Custom vocabularies are FREE to apply (no additional cost).

## Vocabulary filter fundamentals

### What a vocabulary filter does

A vocabulary filter suppresses unwanted words in the transcript.
It can mask (replace with `***`), remove (delete entirely), or tag
(add metadata for post-processing) the filtered terms.

### Filter modes

| Mode | Behavior | Output example |
|---|---|---|
| `mask` | Replace with `***` | "The word is ***" |
| `remove` | Delete entirely | "The word is" |
| `tag` | Tag with metadata | "The word is [FILTERED:word1]" |

### Creating a vocabulary filter

```bash
# Create from a word list
aws transcribe create-vocabulary-filter \
  --vocabulary-filter-name profanity-filter \
  --language-code en-US \
  --words "badword1" "badword2" "competitor-brand"

# Create from a file on S3
aws s3 cp filter-words.txt s3://my-vocab-bucket/filter-words.txt
aws transcribe create-vocabulary-filter \
  --vocabulary-filter-name competitor-filter \
  --language-code en-US \
  --vocabulary-filter-file-uri s3://my-vocab-bucket/filter-words.txt
```

### Applying a vocabulary filter

```bash
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --language-code en-US \
  --settings VocabularyFilterName=profanity-filter,VocabularyFilterMethod=mask \
  --output-bucket-name my-output-bucket
```

### Filter lifecycle

```bash
# Check filter status
aws transcribe get-vocabulary-filter \
  --vocabulary-filter-name profanity-filter

# List all filters
aws transcribe list-vocabulary-filters \
  --query 'VocabularyFilters[*].{Name:VocabularyFilterName,Language:LanguageCode}' \
  --output table

# Delete a filter
aws transcribe delete-vocabulary-filter \
  --vocabulary-filter-name profanity-filter
```

## Vocabulary vs filter: when to use each

```text
Decision guide:
  ├── Want to BOOST recognition of specific terms (company names, acronyms)?
  │     → Custom Vocabulary (helps Transcribe recognize the term correctly)
  │
  ├── Want to SUPPRESS specific terms (profanity, competitor names)?
  │     → Vocabulary Filter (removes or masks the term from output)
  │
  └── Both at the same time?
        → Yes, they are independent and can be used simultaneously
           e.g., boost "AWS" (vocabulary) + mask profanity (filter)
```

### Combined example

```bash
aws transcribe start-transcription-job \
  --transcription-job-name call-analysis \
  --media MediaFileUri=s3://calls/recordings/call-001.flac \
  --language-code en-US \
  --settings \
    VocabularyName=company-terms,\
    VocabularyFilterName=profanity-filter,\
    VocabularyFilterMethod=mask \
  --output-bucket-name calls-output
```

This simultaneously:
- Boosts recognition of company-specific terms (via vocabulary).
- Masks profanity in the output transcript (via filter).

## Common pitfalls

### Pitfall 1: Vocabulary not READY

The job fails because the vocabulary was referenced while still
in PENDING state. **Fix:** wait for READY status before starting
the job. Check with `get-vocabulary`.

### Pitfall 2: Wrong language code

A vocabulary created for en-US cannot be used with en-GB or
es-US. **Fix:** create separate vocabularies for each language.

### Pitfall 3: Filter mode not specified

Without `VocabularyFilterMethod`, the default behavior may not
match expectations. **Fix:** always specify mask, remove, or tag
explicitly.

### Pitfall 4: Confusing vocabulary with custom language model

A custom vocabulary boosts specific words. A custom language model
improves overall accuracy. They are different features. Vocabularies
are free; CLMs add cost. **Fix:** use vocabulary first, CLM only if
accuracy is still insufficient.

## Terraform example

```hcl
# Custom vocabulary (via local-exec)
resource "null_resource" "transcribe_vocabulary" {
  triggers = {
    phrases_hash = sha1(join(",", var.vocabulary_phrases))
  }

  provisioner "local-exec" {
    command = <<-EOF
      aws transcribe create-vocabulary \
        --vocabulary-name ${var.vocabulary_name} \
        --language-code ${var.language_code} \
        --phrases ${join(" ", [for p in var.vocabulary_phrases : "\"${p}\""])} \
        --region ${var.region}
    EOF
  }
}

# Vocabulary filter (via local-exec)
resource "null_resource" "transcribe_vocab_filter" {
  triggers = {
    words_hash = sha1(join(",", var.filter_words))
  }

  provisioner "local-exec" {
    command = <<-EOF
      aws transcribe create-vocabulary-filter \
        --vocabulary-filter-name ${var.filter_name} \
        --language-code ${var.language_code} \
        --words ${join(" ", [for w in var.filter_words : "\"${w}\""])} \
        --region ${var.region}
    EOF
  }
}
```

## Extended from SKILL.md

## Expert heuristic: custom vocabulary vs custom language model

## Expert heuristic: custom vocabulary vs custom language model

Both improve accuracy but work differently and have different
costs.

```text
Accuracy improvement options:
  ├── Few specific terms (company names, acronyms, product names)?
  │     → Custom Vocabulary (free to apply, just upload a vocabulary file)
  │        Boosts recognition of specific words
  │        No training data needed — just a word list with optional pronunciations
  │
  ├── Broader domain vocabulary (medical, legal, technical)?
  │     → Custom Language Model (requires training text, adds cost per minute)
  │        Improves OVERALL accuracy by training on domain-specific text
  │        Requires: 1,000 - 100,000 training sentences in a text file on S3
  │        Choose BaseModelName: NarrowBand (phone audio, 8kHz) or WideBand (high-quality, 16kHz+)
  │
  └── Both can be used simultaneously
        → Custom vocabulary for specific terms + CLM for overall accuracy
```

**Key implication:** start with a custom vocabulary (free, simple).
If accuracy is still insufficient, add a custom language model
(requires training data, adds ~$0.00075/second additional cost).

## Step 3 — Custom vocabulary creation and application

**Create a custom vocabulary from a list:**

```bash
# Create vocabulary from a simple phrase list
aws transcribe create-vocabulary \
  --vocabulary-name company-terms \
  --language-code en-US \
  --phrases "AWS" "EC2" "S3" "DynamoDB" "Lambda"

# Create vocabulary from a file (for complex entries with pronunciations)
aws transcribe create-vocabulary \
  --vocabulary-name medical-terms \
  --language-code en-US \
  --vocabulary-file-uri s3://my-vocab-bucket/medical-terms.txt
```

**Vocabulary file format (table-style, tab-delimited):**

```
Phrase\tSoundsLike\tIPA\tDisplayAs
Aortic stenosis\taortic stenosis\t\tAS
Myocardial infarction\tmyocardial infarction\t\tMI
```

**Apply a custom vocabulary to a job:**

```bash
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --language-code en-US \
  --settings VocabularyName=company-terms \
  --output-bucket-name my-output-bucket
```

**Check vocabulary status:**

```bash
aws transcribe get-vocabulary \
  --vocabulary-name company-terms \
  --query 'VocabularyState' --output text
# Must be READY before referencing in a job
```

## Step 4 — Vocabulary filter CLI

```bash
# Create a vocabulary filter
aws transcribe create-vocabulary-filter \
  --vocabulary-filter-name profanity-filter \
  --language-code en-US \
  --words "word1" "word2" "word3"

# Apply filter to a job with mask mode
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --language-code en-US \
  --settings VocabularyFilterName=profanity-filter,VocabularyFilterMethod=mask \
  --output-bucket-name my-output-bucket
```

## Step 8 — Custom language model creation and application

```bash
# Training data must be a text file on S3 (1,000-100,000 sentences)
aws transcribe create-language-model \
  --model-name my-domain-model \
  --language-code en-US \
  --base-model-name WideBand \
  --input-data-uri s3://my-training-bucket/training-corpus.txt
```

## Step 8 — Apply CLM to a job / training status

```bash
aws transcribe start-transcription-job \
  --transcription-job-name my-job \
  --media MediaFileUri=s3://bucket/audio.wav \
  --language-code en-US \
  --model-settings LanguageModelName=my-domain-model \
  --output-bucket-name my-output-bucket
```

**Check model training status:**

```bash
aws transcribe describe-language-model \
  --model-name my-domain-model \
  --query 'ModelStatus' --output text
# Must be TRAINED before referencing in a job
```

## Step 8 — CLM constraints

**CLM constraints:**
- Training data must be 1,000 to 100,000 sentences of domain text.
- Training takes 30 minutes to several hours depending on data size.
- Adds ~$0.00075 per second of audio to the standard transcription cost.
- Language-specific: a model trained for en-US cannot be used for
  other languages.
- NOT supported for medical transcription jobs.
