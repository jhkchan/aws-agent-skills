# Job Scoping and Data Identifiers — Macie Data Classifier

Deep reference on classification job scoping (bucket inclusion/exclusion
patterns, tag-based criteria, sampling depth), managed data identifier
categories and selection, custom data identifier regex construction
and quality scoring, and finding type/severity taxonomy. Loaded on
demand by the skill — kept out of the main SKILL.md body so the audit
procedure stays scannable.

## Classification job scoping in detail

### Scoping block structure

Macie classification jobs use a nested AND/OR criterion structure
within `s3JobDefinition.scoping`:

```json
{
  "s3JobDefinition": {
    "scoping": {
      "includes": {
        "and": [
          {
            "simpleScopeTerm": {
              "comparator": "EQ",
              "key": "S3_BUCKET",
              "values": ["s3://finance-data", "s3://customer-records"]
            }
          },
          {
            "tagScopeTerm": {
              "comparator": "EQ",
              "key": "Environment",
              "values": ["production"]
            }
          }
        ]
      },
      "excludes": {
        "and": [
          {
            "simpleScopeTerm": {
              "comparator": "STARTS_WITH",
              "key": "S3_OBJECT",
              "values": ["*.log", "*.tmp"]
            }
          }
        ]
      }
    }
  }
}
```

### Scoping criterion types

| Criterion type | Key | Use case |
|---|---|---|
| Bucket name | `S3_BUCKET` | Include/exclude by bucket |
| Object key | `S3_OBJECT` | Include/exclude by object prefix or suffix |
| Tag | (tag key) | Include/exclude by bucket or object tag |
| Account | `ACCOUNT_ID` | Multi-account scoping |

### Comparator values

| Comparator | Meaning |
|---|---|
| `EQ` | Equals (exact match) |
| `NE` | Not equals |
| `STARTS_WITH` | Prefix match |
| `CONTAINS` | Substring match |
| `ENDS_WITH` | Suffix match |

### Common scoping patterns

**Pattern 1: Targeted includes (known sensitive buckets)**

```json
{
  "includes": {
    "and": [{
      "simpleScopeTerm": {
        "comparator": "EQ",
        "key": "S3_BUCKET",
        "values": ["s3://pii-data", "s3://financial-records"]
      }
    }]
  }
}
```

**Pattern 2: Broad scan with excludes (catch-all minus known noise)**

```json
{
  "includes": {
    "and": [{
      "simpleScopeTerm": {
        "comparator": "STARTS_WITH",
        "key": "S3_BUCKET",
        "values": ["s3://"]
      }
    }]
  },
  "excludes": {
    "and": [{
      "simpleScopeTerm": {
        "comparator": "EQ",
        "key": "S3_BUCKET",
        "values": ["s3://logs", "s3://temp-uploads"]
      }
    }]
  }
}
```

**Pattern 3: Tag-based (scalable with tagging discipline)**

```json
{
  "includes": {
    "and": [{
      "tagScopeTerm": {
        "comparator": "EQ",
        "key": "DataClass",
        "values": ["sensitive", "restricted"]
      }
    }]
  }
}
```

### Sampling depth

| Setting | Behavior | Use case |
|---|---|---|
| `sampleDeep: false` | Full scan — all objects in scope | High-sensitivity deterministic scan |
| `sampleDeep: true` | Sampled — subset of objects per bucket | Quick assessment, low-sensitivity |

## Managed data identifiers

### Categories and examples

| Category | Identifier examples |
|---|---|
| PII | `NAME`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `MAILING_ADDRESS`, `SSN_US`, `PASSPORT_US` |
| Financial | `CREDIT_CARD_NUMBER`, `BANK_ACCOUNT_NUMBER`, `ABA_ROUTING_NUMBER`, `SWIFT_CODE` |
| Credentials | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_KEY`, `PRIVATE_KEY`, `API_KEY`, `JWT` |
| Healthcare | `MEDICAL_RECORD_NUMBER_US`, `HEALTH_INSURANCE_CLAIM_NUMBER_US` |
| Personal | `DATE_OF_BIRTH`, `DRIVER_LICENSE_US`, `NATIONAL_INSURANCE_NUMBER_UK` |

### Managed identifier selector

| Selector value | Coverage |
|---|---|
| `ALL` | All managed identifiers across all categories |
| `RECOMMENDED` | A curated subset (excludes some specialized detectors) |
| `LIST` | Explicit list of identifier IDs (custom subset) |

**Audit recommendation:** for healthcare or financial organizations,
use `ALL` to ensure specialized detectors are included.

## Custom data identifiers

### Structure

```json
{
  "name": "Employee ID",
  "regex": "\\bEMP-\\d{6}\\b",
  "keywords": ["employee", "emp-id", "staff-id"],
  "ignoreWords": ["example", "test", "sample", "dummy"],
  "maximumMatchDistance": 50
}
```

| Field | Purpose |
|---|---|
| `regex` | The pattern to match (PCRE-compatible) |
| `keywords` | Words that must appear near the match (proximity filter) |
| `ignoreWords` | Words that suppress a match if present |
| `maximumMatchDistance` | Max characters between keyword and match |

### Regex quality scoring rubric

```text
+1  Word boundaries (\b) present
+1  Bounded quantifiers ({n,m}, not {1,})
+1  Specific character classes ([A-Z0-9], not .)
+1  Format-specific delimiters (dashes, prefixes)
+1  Ignore-words list configured
-2  Nested quantifiers ((a+)+, (.*)*)
-1  Wildcard prefix/suffix (.*pattern)
-1  No boundaries on common patterns (\d+)

Score 4-5: healthy
Score 2-3: review needed
Score 0-1: high risk (timeout / false-positive flood)
```

### Common regex mistakes

**Mistake 1: Unbounded quantifier on digits**

```text
BAD:  \d{1,19}
GOOD: \b\d{3}-\d{2}-\d{4}\b (SSN format)

Why: \d{1,19} matches every 1-19 digit sequence in every file —
timestamps, IDs, phone numbers, prices. This produces thousands of
false positives per scan.
```

**Mistake 2: Catastrophic backtracking**

```text
BAD:  (a+)+b
GOOD: a+b

Why: nested quantifiers cause exponential backtracking on long
strings. A 1000-character line without 'b' can take minutes to
evaluate. This causes job timeouts.
```

**Mistake 3: No word boundaries**

```text
BAD:  KEY-[A-Z0-9]{20}
GOOD: \bKEY-[A-Z0-9]{20}\b

Why: without \b, the regex matches inside longer strings.
"XKEY-ABCD...0XYZ" matches, producing false positives.
```

## Finding type taxonomy

### SensitiveData findings

| Finding type | Description |
|---|---|
| `SensitiveData:S3Object/CreditCard` | Credit card number detected |
| `SensitiveData:S3Object/AwsCredentials` | AWS access key or secret key |
| `SensitiveData:S3Object/Ssn` | US Social Security Number |
| `SensitiveData:S3Object/ApiKey` | Generic API key pattern |
| `SensitiveData:S3Object/CustomIdentifier` | Matched a custom data identifier |

### Policy findings

| Finding type | Description |
|---|---|
| `Policy:IAMUser/S3/BucketPublic` | Bucket is publicly accessible |
| `Policy:IAMUser/S3/BucketSharedExternally` | Bucket shared with external account |
| `Policy:IAMUser/S3/BucketReplicationExternal` | Replication to external account |

### Severity mapping

| Severity | Typical finding types |
|---|---|
| High | `AwsCredentials`, `CreditCard`, `BucketPublic` with sensitive data |
| Medium | `Ssn`, `Email`, `ApiKey`, `BucketSharedExternally` |
| Low | Policy findings without detected sensitive data |

## Terraform examples

```hcl
# Classification job with scoping
resource "aws_macie2_classification_job" "daily_pii_scan" {
  job_type     = "SCHEDULED"
  name         = "daily-pii-scan"
  s3_job_definition {
    bucket_definitions {
      account_id = "123456789012"
      buckets    = ["pii-data", "financial-records"]
    }
    scoping {
      includes {
        and {
          simple_scope_term {
            comparator = "EQ"
            key        = "S3_OBJECT"
            values     = ["*.log"]
          }
        }
      }
    }
  }
  schedule_frequency {
    daily_schedule_times = ["05:00"]
  }
}

# Custom data identifier with healthy regex
resource "aws_macie2_custom_data_identifier" "employee_id" {
  name          = "Employee ID"
  regex         = "\\bEMP-\\d{6}\\b"
  keywords      = ["employee", "emp-id"]
  ignore_words  = ["example", "test", "sample"]
}

# Findings filter (ARCHIVE — not SUPPRESS)
resource "aws_macie2_findings_filter" "archive_low_severity" {
  name   = "archive-low-severity"
  action = "ARCHIVE"
  finding_criteria {
    criterion {
      field    = "severity"
      eq       = ["Low"]
    }
  }
}
```
