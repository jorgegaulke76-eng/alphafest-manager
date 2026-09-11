"""Atalho oficial para gerar o ZIP de atualização limpo do AlphaFest Manager."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from update_hygiene import build_clean_update_zip


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--release-note", default="")
    args = parser.parse_args()
    result = build_clean_update_zip(args.root, args.output, release_note=args.release_note or None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
