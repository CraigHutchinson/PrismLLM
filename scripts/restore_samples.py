"""
Restore sample_data/*.md working copies from their broken template state.

By default only creates files that do not already exist (safe for first-run
setup without overwriting in-progress work).  Pass --force to overwrite.

Run directly:  python scripts/restore_samples.py
Force reset:   python scripts/restore_samples.py --force
Via Makefile:  make restore-samples
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def restore(root: Path = Path("."), force: bool = False) -> int:
    src = root / "sample_data" / "templates"
    dst = root / "sample_data"

    if not src.is_dir():
        print(f"Error: templates directory not found: {src}")
        return 1

    templates = sorted(src.glob("*.md"))
    if not templates:
        print("No templates found in sample_data/templates/")
        return 0

    created = skipped = 0
    for tmpl in templates:
        target = dst / tmpl.name
        if target.exists() and not force:
            print(f"  skipped (exists): {target.relative_to(root)}")
            skipped += 1
        else:
            shutil.copy2(tmpl, target)
            action = "restored" if target.exists() else "created"
            print(f"  {action}: {target.relative_to(root)}")
            created += 1

    parts = []
    if created:
        parts.append(f"{created} file(s) restored")
    if skipped:
        parts.append(f"{skipped} skipped (already exist — use --force to overwrite)")
    print(f"\n{', '.join(parts)}.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="Overwrite existing working copies")
    args = parser.parse_args()
    raise SystemExit(restore(force=args.force))
