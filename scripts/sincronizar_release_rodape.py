"""Sincroniza o identificador do rodapé com novas releases HF do GitHub.

O script não altera dados e não modifica versões se o commit não indicar HF nova.
Usado no workflow do GitHub após merges na branch main.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

_HF_FINAL = re.compile(r"-HF(\d{2,3})$")
_HF_COMMIT = re.compile(r"(?<![A-Za-z0-9])HF(\d{2,3})(?![\d.])", re.I)
_VERSION_FILES = ("VERSAO", "VERSAO.txt", "RELEASE_INFO.json")


def sincronizar_release(
    root: Path,
    mensagem_commit: str,
    sha: str,
    data_commit: str,
) -> bool:
    """Retorna True se os três arquivos foram atualizados. Não faz push."""
    root = Path(root)
    versao = (root / "VERSAO.txt").read_text(encoding="utf-8").strip()
    versao_auxiliar = (root / "VERSAO").read_text(encoding="utf-8").strip()
    release_path = root / "RELEASE_INFO.json"
    info = json.loads(release_path.read_text(encoding="utf-8"))
    if versao != versao_auxiliar or info.get("version") != versao:
        raise ValueError("Metadados divergentes. Atualização automática interrompida.")
    atual = _HF_FINAL.search(versao)
    if not atual:
        raise ValueError("Versão atual não termina com um identificador HF numérico.")
    hfs = [int(v) for v in _HF_COMMIT.findall(mensagem_commit)]
    if not hfs:
        return False
    proxima = max(hfs)
    # Nunca reduzir o número da versão; nem considerar as subséries HF65.24.x.
    if proxima <= int(atual.group(1)):
        return False
    data = datetime.fromisoformat(data_commit.replace("Z", "+00:00"))
    if data.tzinfo is None:
        raise ValueError("Data do commit sem fuso horário.")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("SHA do commit inválido.")
    nova = versao[:atual.start()] + f"-HF{proxima}"
    info["version"] = nova
    info["created_at"] = data.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    info["description"] = f"HF{proxima}: sincronização automática após merge no GitHub."
    info["source_commit"] = sha
    (root / "VERSAO").write_text(nova + "\n", encoding="utf-8")
    (root / "VERSAO.txt").write_text(nova + "\n", encoding="utf-8")
    release_path.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--message", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    alterou = sincronizar_release(args.root, args.message, args.sha, args.date)
    print("release_sync=changed" if alterou else "release_sync=unchanged")


if __name__ == "__main__":
    main()
