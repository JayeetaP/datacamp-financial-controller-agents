from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = ROOT / "knowledge" / "confluence"
MANIFEST = ROOT / "knowledge" / "retrieval_manifest.json"


def _parse_document(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError(f"Missing YAML frontmatter: {path}")
    return yaml.safe_load(match.group(1)), match.group(2).strip()


def build_manifest() -> dict:
    records = []
    for path in sorted(KNOWLEDGE_DIR.rglob("*.md")):
        metadata, content = _parse_document(path)
        relative = path.relative_to(ROOT).as_posix()
        records.append(
            {
                **metadata,
                "path": relative,
                "title": content.splitlines()[0].removeprefix("# "),
                "content_hash": hashlib.sha256(content.encode()).hexdigest(),
                "synthetic": True,
                "semantic_terms": sorted(
                    {
                        word.lower()
                        for word in re.findall(r"[A-Za-z][A-Za-z-]+", content)
                        if len(word) > 3
                    }
                ),
            }
        )
    return {"version": "1.0", "synthetic": True, "documents": records}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if the manifest differs")
    args = parser.parse_args()
    manifest = build_manifest()
    content = json.dumps(manifest, indent=2) + "\n"
    if args.check:
        if not MANIFEST.exists() or MANIFEST.read_text(encoding="utf-8") != content:
            print("Knowledge retrieval manifest is out of date")
            return 1
        action = "Verified"
    else:
        MANIFEST.write_text(content, encoding="utf-8")
        action = "Indexed"
    print(f"{action} {len(manifest['documents'])} synthetic knowledge documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
