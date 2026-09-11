"""Atalho oficial para gerar o ZIP de atualização limpo do AlphaFest Manager."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from update_hygiene import build_clean_update_zip
from release_diagnostics import run_release_diagnostics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--release-note", default="")
    args = parser.parse_args()
    diagnostics = run_release_diagnostics(args.root)
    if not diagnostics.ok:
        raise RuntimeError("Diagnóstico da release reprovado: " + " | ".join(diagnostics.problems))
    result = build_clean_update_zip(args.root, args.output, release_note=args.release_note or None)
    result["release_diagnostics"] = diagnostics.to_dict()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
