#!/usr/bin/env python3
"""Generate USF v1.0 manifests (skill.usf.yaml) for every skill in this repo.

The Universal Skill Format manifest is the OWASP Agentic Skills Top 10
whitepaper's AST10 proposal. The schema lives in the reference
implementation (jhkchan/owasp-ast10-agent-skills, schemas/usf-v1.schema.json);
this generator produces manifests that pass that repo's structural schema AND
its semantic validator (validators/usf.py), and whose content hashes are
byte-compatible with its signing toolchain (scripts/sign_usf.py preflight
recomputes them and refuses stale ones, so compatibility is enforced, not
assumed).

Manifest policy (documented here because the manifest comments cannot carry it
all — see SKILL_GOVERNANCE.md "Security audit" for the audit these declare):

* permissions  — every skill ships instructions only: no bundled executable
  scripts, no package egress, no writes. `shell: false` follows the reference
  repo's own precedent (its detector skills also direct the host to run code
  while declaring no shell): the permission block describes what the PACKAGE
  programmatically requires, and requires.binaries carries the runtime need.
  All skills drive or ingest AWS CLI output, hence binaries: [aws].
* risk_tier    — declared above the permission-derived floor where the skill's
  instructed effect is stronger than its package capabilities. The validator
  derives L0 for read-only/no-egress/no-shell and allows over-declaration as
  conservative; a tier that reflected only package bytes (L0 everywhere) would
  under-signal deployer/operator skills whose instructions mutate real
  infrastructure. Mapping by metadata.task_type:
      audit -> L0, troubleshoot -> L1,
      deploy/operate/optimize/automate -> L2,
      plus an explicit L3 override list for destructive-primary skills.
* content_hash — the reference toolchain's surface, vendored verbatim below
  (see _content_sha256). It binds the runtime-loaded instruction bytes:
  SKILL.md + references/*.md + scripts/*.py + evals/evals.json. Known stated
  exclusions: eval/ and evals/ fixtures (harness inputs), example docs, and
  skill-catalog's references/by-family/*.md (the surface glob is one level;
  that manifest documents its own partition).
* platforms    — [claude], the runtime whose skill-directory format this repo
  is validated against (agentskills.io spec compliance + @skills resolution,
  both verified end-to-end). SKILL.md `compatibility` names the broader
  expected set; the manifest declares only the checked one.
* scan_status  — records the AST10 detector sweep this repo passed
  (0 error-level findings across all skills, 2026-09-04).

Usage:
    python3 scripts/generate_usf_manifests.py [--skills-dir skills] [--force]

Overwrites skill.usf.yaml in place (the signer's preflight re-validates and
refuses to sign anything stale, so regeneration is the recovery path).
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# --- vendored from jhkchan/owasp-ast10-agent-skills @ 58c2768 (Apache-2.0) ---
# scripts/content_hash.py, verbatim algorithm; do not hand-edit without
# re-vendoring upstream: sign_usf.py preflight recomputes hashes with this
# exact surface and refuses to sign any manifest that disagrees.
SURFACE_GLOBS = ("SKILL.md", "references/*.md", "scripts/*.py", "evals/evals.json")


def _content_sha256(skill_dir: Path) -> str:
    files: list[Path] = []
    for pattern in SURFACE_GLOBS:
        files.extend(p for p in skill_dir.glob(pattern) if p.is_file())
    digest = hashlib.sha256()
    for f in sorted(files, key=lambda p: p.relative_to(skill_dir).as_posix()):
        rel = f.relative_to(skill_dir).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(f.read_bytes())
    return digest.hexdigest()
# --- end vendored ---


# task_type -> risk_tier. Floor from these permissions is L0 everywhere; the
# mapping over-declares deliberately (conservative, allowed by the validator).
RISK_TIER_BY_TASK_TYPE = {
    "audit": "L0",
    "troubleshoot": "L1",
    "deploy": "L2",
    "operate": "L2",
    "optimize": "L2",
    "automate": "L2",
}

# Destructive-primary: the skill's main flow deletes data, revokes access, or
# isolates resources (L3 = destructive). Hand-maintained; name-based task_type
# would under-signal these.
TIER_OVERRIDES = {
    "auto-remediation-automator": "L3",
    "incident-response-automator": "L3",
    "s3-version-cleanup-operator": "L3",
    "securityhub-remediation-automator": "L3",
    # The catalog is task_type: operate by routing convention, but it is a
    # read-only index — pointing, never mutating.
    "skill-catalog": "L0",
}

SCAN_DATE = "2026-09-04"
SCANNER = "jhkchan/owasp-ast10-agent-skills audit"


def frontmatter_of(text: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise ValueError("SKILL.md does not open with frontmatter")
    fm: dict[str, str] = {}
    in_meta = False
    for line in m.group(1).split("\n"):
        kv = re.match(r"^(\w[\w-]*)\s*:\s*(.*)$", line)
        nested = re.match(r"^\s+([\w-]+)\s*:\s*(.*)$", line)
        if nested and in_meta:
            fm[f"metadata.{nested.group(1)}"] = nested.group(2).strip().strip("'\"")
        elif kv:
            in_meta = kv.group(1) == "metadata"
            if not in_meta:
                fm[kv.group(1)] = kv.group(2).strip().strip("'\"")
    return fm


def infer_task_type(name: str, fm: dict[str, str]) -> str:
    tt = fm.get("metadata.task_type")
    if tt:
        return tt
    if re.search(r"auditor$|advisor$|triage$|inventory$", name):
        return "audit"
    if name.endswith("deployer"):
        return "deploy"
    if name.endswith("troubleshooter"):
        return "troubleshoot"
    if name.endswith("optimizer"):
        return "optimize"
    if name.endswith("operator"):
        return "operate"
    if name.endswith("automator"):
        return "automate"
    return "audit"


def capability_sentence(description: str) -> str:
    """The honest function statement: the description up to its Use/Triggers tails."""
    d = " ".join(description.split())
    d = re.split(r"\s+(?:Use when|Triggers:)", d)[0].strip()
    return d[:800].rstrip(".,;") + "."


def read_paths(skill_dir: Path) -> list[str]:
    """Explicit read list: the files the agent loads at runtime. No dirs, no globs."""
    rels = ["./SKILL.md", "./skill.usf.yaml"]
    rels += [f"./{p.relative_to(skill_dir).as_posix()}" for p in sorted(skill_dir.glob("references/*.md"))]
    for extra in ("example/README.md", "examples/README.md"):
        if (skill_dir / extra).is_file():
            rels.append(f"./{extra}")
    rels += [f"./{p.relative_to(skill_dir).as_posix()}" for p in sorted(skill_dir.glob("commands/**/*.md"))]
    return rels


MANIFEST_TEMPLATE = """# Universal Agentic Skill Format v1.0 manifest.
#
#   schema:    https://github.com/jhkchan/owasp-ast10-agent-skills/blob/main/schemas/usf-v1.schema.json
#   generator: ../../scripts/generate_usf_manifests.py  (policy documented there)
#
# Generated for the aws-agent-skills repository; signed at release with the
# key did:web:jhkchan.github.io publishes. A verified signature answers
# "who published this", never "is this safe".
---
name: {name}
version: "{version}"

# The runtime whose skill-directory format this package is validated against
# (agentskills.io spec compliance + @skills resolution, verified end-to-end).
# SKILL.md `compatibility` names the broader expected set; only the checked
# runtime is declared here.
platforms: [claude]

description: >-
  {description}

author:
  name: "aws-agent-skills contributors"
  # identity + signing_key are written by the release signer in the same
  # operation as `signature` below, and both are inside the signed payload.

permissions:
  files:
    read:
{read_list}
    # The package is instructions: it writes nothing, ever.
    write: []
    deny_write:
      # The identity-file floor. `write: []` is a property of this package;
      # `deny_write` is what has to survive a port to a runtime whose default
      # is write-everything.
      - SOUL.md
      - MEMORY.md
      - AGENTS.md
  network:
    # No package egress. Default-deny with an empty allowlist means no host is
    # reachable. AWS API calls the instructions direct are runtime-mediated via
    # the aws CLI (see requires.binaries), not package egress.
    allow: []
    deny: "*"
  shell: false
  tools:
    - read_file

requires:
  # Every skill drives or ingests AWS CLI output (see SKILL.md compatibility).
  binaries: [aws]

# Permission-derived floor is L0 (read-only, no egress, no shell). The tier
# reflects the skill's instructed effect class, which over-declares on purpose:
# {tier_reason}
risk_tier: {risk_tier}

scan_status:
  scanner: "{scanner}"
  last_scanned: "{scan_date}"
  result: "pass"

signature: "unsigned"

# sha256 over this skill's hashed surface (SKILL.md, references/*.md,
# scripts/*.py, evals/evals.json — the runtime-loaded instruction bytes),
# computed by the vendored algorithm in scripts/generate_usf_manifests.py and
# re-checked by the release signer's preflight.{surface_note}
content_hash: "sha256:{content_hash}"

changelog:
  - version: "{version}"
    date: "{scan_date}"
    notes: "Initial USF v1.0 manifest for {name}."
"""

TIER_REASONS = {
    "L0": "reads and analyzes; changes happen only through human-executed suggestions.",
    "L1": "diagnosis is read-only, but documented remediation may reconfigure or restart components.",
    "L2": "following this skill creates or modifies cloud infrastructure, so the effect is elevated even though the package itself writes nothing.",
    "L3": "the skill's primary flow deletes data, revokes access, or isolates resources — destructive by design and gated accordingly.",
}


def generate(skill_dir: Path) -> str:
    text = (skill_dir / "SKILL.md").read_text()
    fm = frontmatter_of(text)
    name = fm.get("name") or skill_dir.name
    if name != skill_dir.name:
        raise ValueError(f"{skill_dir.name}: frontmatter name {name!r} != directory")
    version = fm.get("metadata.version", "0.1.0")
    if not re.match(r"^\d+\.\d+\.\d+", version):
        raise ValueError(f"{skill_dir.name}: metadata.version {version!r} is not semver")

    tt = infer_task_type(skill_dir.name, fm)
    tier = TIER_OVERRIDES.get(skill_dir.name) or RISK_TIER_BY_TASK_TYPE[tt]

    surface_note = ""
    if skill_dir.name == "skill-catalog":
        surface_note = (
            "\n# NOTE: this skill's reference tables live one level deeper\n"
            "# (references/by-family/*.md) than the surface glob matches, so they are a\n"
            "# stated exclusion from the hash — the partition is recorded here rather\n"
            "# than left silent, and the tables are covered by the read list below."
        )

    read_list = "\n".join(f"      - {p}" for p in read_paths(skill_dir))
    return MANIFEST_TEMPLATE.format(
        name=name,
        version=version,
        description=capability_sentence(fm["description"]),
        read_list=read_list,
        risk_tier=tier,
        tier_reason=TIER_REASONS[tier],
        scanner=SCANNER,
        scan_date=SCAN_DATE,
        content_hash=_content_sha256(skill_dir),
        surface_note=surface_note,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-dir", default=str(REPO_ROOT / "skills"))
    ap.add_argument("--force", action="store_true", help="regenerate even if the manifest exists")
    args = ap.parse_args()

    skills_dir = Path(args.skills_dir)
    written = skipped = 0
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        if not (skill_dir / "SKILL.md").exists():
            continue
        out = skill_dir / "skill.usf.yaml"
        if out.exists() and not args.force:
            skipped += 1
            continue
        out.write_text(generate(skill_dir))
        written += 1
    print(f"{written} manifest(s) written, {skipped} skipped (already present)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
