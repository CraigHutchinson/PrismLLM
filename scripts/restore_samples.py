"""
Reset sample_data/*.md working copies to their broken template state.

Run directly:  python scripts/restore_samples.py
Via Makefile:  make restore-samples
"""
from __future__ import annotations

import shutil
from pathlib import Path


def restore(root: Path = Path(".")) -> int:
    src = root / "sample_data" / "templates"
    dst = root / "sample_data"

    if not src.is_dir():
        print(f"Error: templates directory not found: {src}")
        return 1

    templates = sorted(src.glob("*.md"))
    if not templates:
        print("No templates found in sample_data/templates/")
        return 0

    for tmpl in templates:
        target = dst / tmpl.name
        shutil.copy2(tmpl, target)
        print(f"  restored: {target.relative_to(root)}")

    print(f"\n{len(templates)} file(s) restored from sample_data/templates/")
    return 0


if __name__ == "__main__":
    raise SystemExit(restore())
