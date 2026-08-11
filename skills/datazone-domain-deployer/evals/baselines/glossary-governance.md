# Baseline (no-skill) — glossary-governance

> This is the response a model produces **without** the skill
> definition. It creates the glossary terms but treats them as labels
> rather than the policy engine. Misses that glossary terms carry
> subscription policies that determine approval routing, the Lambda
> auto-classification setup pattern, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the domain and glossary:

```bash
aws datazone create-domain --name governed-catalog
aws datazone create-glossary-term --name "Public"
aws datazone create-glossary-term --name "Internal"
aws datazone create-glossary-term --name "Confidential"
aws datazone create-glossary-term --name "Restricted"
```

Then tag assets with these terms. Metadata enrichment can be done
manually.
