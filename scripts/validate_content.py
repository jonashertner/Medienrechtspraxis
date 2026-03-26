#!/usr/bin/env python3
"""Validate content/ directory structure and meta.yaml files."""

import sys
from pathlib import Path

import yaml

CONTENT_DIR = Path("content")
REQUIRED_META_FIELDS = ["title", "slug", "description", "related_articles", "layers", "tags", "sort_order"]
VALID_LAYERS = ["summary", "doctrine", "caselaw"]


def validate() -> int:
    errors = 0

    if not CONTENT_DIR.exists():
        print(f"❌ Content directory not found: {CONTENT_DIR}")
        return 1

    topics = [d for d in CONTENT_DIR.iterdir() if d.is_dir()]
    print(f"Found {len(topics)} topic directories\n")

    for topic_dir in sorted(topics):
        slug = topic_dir.name
        meta_path = topic_dir / "meta.yaml"

        if not meta_path.exists():
            print(f"  ❌ {slug}: missing meta.yaml")
            errors += 1
            continue

        try:
            with open(meta_path) as f:
                meta = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"  ❌ {slug}: invalid YAML in meta.yaml: {e}")
            errors += 1
            continue

        # Check required fields
        for field in REQUIRED_META_FIELDS:
            if field not in meta:
                print(f"  ❌ {slug}: missing field '{field}' in meta.yaml")
                errors += 1

        # Check slug consistency
        if meta.get("slug") != slug:
            print(f"  ❌ {slug}: slug mismatch (meta says '{meta.get('slug')}')")
            errors += 1

        # Check layers
        layers_meta = meta.get("layers", {})
        content_status = []
        for layer in VALID_LAYERS:
            de_file = topic_dir / f"{layer}.md"
            en_file = topic_dir / f"{layer}.en.md"
            has_de = de_file.exists()
            has_en = en_file.exists()

            status = layers_meta.get(layer, {}).get("status", "missing")
            if has_de:
                size = de_file.stat().st_size
                content_status.append(f"{layer}: ✓ ({size:,} bytes)")
            else:
                content_status.append(f"{layer}: -")

        print(f"  {'✓' if errors == 0 else '!'} {slug}: {' | '.join(content_status)}")

    print(f"\n{'✓ All valid' if errors == 0 else f'❌ {errors} error(s) found'}")
    return 1 if errors > 0 else 0


if __name__ == "__main__":
    sys.exit(validate())
