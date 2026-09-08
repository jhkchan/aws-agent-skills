#!/usr/bin/env python3
"""Generate index/skills.json — the compact catalog the npm package ships.

The npm package cannot carry the full skills tree (eval fixtures would push it
past 25MB), so the discovery CLI falls back to this index when skills/ is
absent. It carries exactly what list/route/status need: identity, description,
task type, family, version, and routing keywords. Regenerate after any skill
change (CI should diff it):

    python3 scripts/generate_skill_index.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from generate_usf_manifests import frontmatter_of, infer_task_type  # noqa: E402


def main() -> int:
    skills = []
    for d in sorted((REPO_ROOT / "skills").iterdir()):
        if d.name.startswith(".") or not (d / "SKILL.md").exists():
            continue
        fm = frontmatter_of((d / "SKILL.md").read_text())
        keywords = [k.strip() for k in re.split(r"[,;]", fm.get("metadata.keywords", "")) if k.strip()]
        skills.append({
            "name": fm.get("name", d.name),
            "description": fm.get("description", ""),
            "taskType": infer_task_type(d.name, fm),
            "family": fm.get("metadata.family", ""),
            "version": fm.get("metadata.version", "0.1.0"),
            "keywords": keywords,
            "hasEval": (d / "eval").is_dir() or (d / "evals").is_dir(),
            "hasReferences": (d / "references").is_dir(),
        })
    out = REPO_ROOT / "index" / "skills.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(skills, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(skills)} skills -> {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
