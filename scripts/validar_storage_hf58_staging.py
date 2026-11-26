"""Conferência REAL do upload de arte, SOMENTE em projeto Supabase isolado.

Não lê secrets do Manager, não importa app.py e não grava app_data.
O modo de execução é manual e exige sentinela previamente colocada em
um bucket catalogo de um projeto de homologação separado da produção.
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
from unittest.mock import patch

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BUCKET = "catalogo"
PASTA_EXCLUSIVA = "HF58_STAGING_ONLY"
CONFIRMACAO = "EU_CONFIRMO_PROJETO_DE_TESTES"
PNG_FICTICIO = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO0f9S0AAAAASUVORK5CYII="
)


class BloqueioHomologacao(Exception):
    """Impede transferência de dados quando o isolamento não foi comprovado."""


@dataclass(frozen=True)
class DestinoHomologacao:
    url: str
    referencia: str
    producao: str
    sentinela: str


def _parsear_ref(url: str) -> tuple[str, str]:
    """Aceita SOMENTE a URL nativa HTTPS de um projeto Supabase distinto."""
    texto = (url or "").strip().rstrip("/")
    parsed = urlparse(texto)
    if (parsed.scheme != "https" or parsed.username or parsed.password
            or parsed.port is not None or parsed.query or parsed.fragment
            or parsed.path not in ("", "/")):
        raise BloqueioHomologacao("Informe somente a URL HTTPS nativa do projeto Supabase.")
    match = re.fullmatch(r"([a-z0-9]{10,32})\.supabase\.co", parsed.hostname or "")
    if not match:
        raise BloqueioHomologacao("Projeto Supabase inválido: não usar localhost, URL personalizada ou domínio desconhecido.")
    return f"https://{match.group(1)}.supabase.co", match.group(1)


def validar_destinos(
    staging_url: str,
    producao_url: str,
    referencia_digitada: str,
    confirmacao: str,
) -> DestinoHomologacao:
    """Antes de ler credenciais ou acessar HTTP, verifica duas URLs distintas."""
    stage, stage_ref = _parsear_ref(staging_url)
    prod, prod_ref = _parsear_ref(producao_url)
    if stage == prod or stage_ref == prod_ref:
        raise BloqueioHomologacao("BLOQUEADO: homologação e produção apontam para o mesmo projeto.")
    if referencia_digitada.strip() != stage_ref:
        raise BloqueioHomologacao("BLOQUEADO: referência repetida não corresponde ao projeto de homologação.")
    if confirmacao.strip() != CONFIRMACAO:
        raise BloqueioHomologacao("BLOQUEADO: falta confirmação manual do isolamento.")
    return DestinoHomologacao(
        url=stage, referencia=stage_ref, producao=prod_ref,
        sentinela=f"HF58_HOMOLOGACAO_{stage_ref}.txt",
    )


def _headers(chave: str) -> dict[str, str]:
    resultado = {"apikey": chave}
    # Chaves modernas sb_secret_/sb_publishable_ são opacas, não JWT.
    if not chave.startswith(("sb_secret_", "sb_publishable_")):
        resultado["Authorization"] = "Bearer " + chave
    return resultado


def verificar_precondicoes(destino: DestinoHomologacao, chave: str, sessao: requests.Session) -> None:
    """Zero operações de escrita: bucket público e sentinela exclusiva obrigatórios."""
    if not chave or len(chave.strip()) < 20:
        raise BloqueioHomologacao("BLOQUEADO: chave de homologação ausente ou inválida.")
    try:
        bucket = sessao.get(
            f"{destino.url}/storage/v1/bucket/{BUCKET}",
            headers=_headers(chave), timeout=15,
        )
        if bucket.status_code != 200:
            raise BloqueioHomologacao("Bucket catalogo indisponível na homologação ou acesso não autorizado.")
        dados = bucket.json()
        if not isinstance(dados, dict) or dados.get("id") != BUCKET or dados.get("public") is not True:
            raise BloqueioHomologacao("BLOQUEADO: bucket catalogo da homologação precisa ser público e confirmado.")
        marcador = sessao.get(
            f"{destino.url}/storage/v1/object/public/{BUCKET}/{destino.sentinela}",
            timeout=15,
        )
        conteudo = f"ALPHAFEST_HF58_STAGING_ONLY:{destino.referencia}\n".encode("utf-8")
        if marcador.status_code != 200 or marcador.content.strip() != conteudo.strip():
            raise BloqueioHomologacao("BLOQUEADO: sentinela de homologação ausente, errada ou ilegível.")
    except requests.RequestException:
        raise BloqueioHomologacao("Falha de rede durante preflight. Nenhum upload foi iniciado.") from None
    except (TypeError, ValueError):
        raise BloqueioHomologacao("Resposta inválida do bucket de homologação.") from None


def exercitar_upload(destino: DestinoHomologacao, chave: str, sessao: requests.Session) -> str:
    """Usa a função real cloud_db.upload_library_file apenas no destino homologado.

    Envia um PNG 1x1 fictício em pasta exclusiva, confere hash e exclui o objeto
    específico. Não cria pastas oficiais nem lê/grava app_data.
    """
    verificar_precondicoes(destino, chave, sessao)
    import cloud_db

    obj = SimpleNamespace(
        name="HF58_FICTICIO_1PX.png",
        type="image/png",
        getbuffer=lambda: memoryview(PNG_FICTICIO),
    )
    prefixo = (
        f"{destino.url}/storage/v1/object/public/{BUCKET}/"
        f"biblioteca/{PASTA_EXCLUSIVA}/"
    )
    salvo = ""
    erro = ""
    limpeza = False
    try:
        with tempfile.TemporaryDirectory(prefix="hf58-staging-local-") as pasta:
            with patch.object(cloud_db, "_config", return_value=(destino.url, chave)), \
                 patch.object(cloud_db, "_SESSION", sessao):
                salvo = cloud_db.upload_library_file(
                    obj, produto_nome=PASTA_EXCLUSIVA, local_upload_dir=pasta,
                )
            if not salvo or not salvo.startswith(prefixo):
                raise BloqueioHomologacao("O upload remoto não foi confirmado. Nenhum sucesso deve ser registrado.")
            if list(Path(pasta).rglob("*")):
                raise BloqueioHomologacao("Arquivo inesperado no fallback local; transferência rejeitada.")
            resposta = sessao.get(salvo, timeout=15)
            if resposta.status_code != 200:
                raise BloqueioHomologacao("A leitura pública do arquivo de teste falhou.")
            if hashlib.sha256(resposta.content).digest() != hashlib.sha256(PNG_FICTICIO).digest():
                raise BloqueioHomologacao("O SHA-256 dos bytes recuperados não confere com o PNG fictício.")
    except requests.RequestException:
        erro = "Falha de rede na transferência de teste."
    except BloqueioHomologacao as exc:
        erro = str(exc)
    finally:
        # Exclui SOMENTE o objeto gerado nesta execução e neste prefixo fixo.
        if salvo and salvo.startswith(prefixo):
            endereco_exclusao = salvo.replace(
                f"/object/public/{BUCKET}/", f"/object/{BUCKET}/", 1
            )
            try:
                removido = sessao.delete(
                    endereco_exclusao, headers=_headers(chave), timeout=15,
                )
                limpeza = removido.status_code in (200, 204)
            except requests.RequestException:
                limpeza = False
    if erro:
        if salvo and not limpeza:
            raise BloqueioHomologacao(
                erro + " Atenção: não foi possível confirmar exclusão do objeto fictício no bucket de testes."
            )
        raise BloqueioHomologacao(erro)
    if not salvo or not limpeza:
        raise BloqueioHomologacao(
            "Não foi possível confirmar a exclusão do PNG fictício. "
            "Conferir a pasta biblioteca/HF58_STAGING_ONLY do bucket de homologação."
        )
    return "APROVADO: envio, download SHA-256 e exclusão do PNG fictício no Supabase isolado."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verificação do upload com projeto Supabase de TESTES separado."
    )
    parser.add_argument("--executar", action="store_true", help="Habilitar preflight e ensaio remoto manual")
    args = parser.parse_args(argv)
    if not args.executar:
        print("ALPHAFEST HF65.24.58 | VERIFICAÇÃO DE STORAGE — SIMULAÇÃO DESATIVADA")
        print("Nenhum dado foi enviado. Use --executar APENAS com projeto de homologação separado.")
        print("Pré-requisitos: bucket público catalogo e sentinela específica do projeto de testes.")
        return 0
    print("AVISO: este comando envia e exclui UM PNG fictício em um projeto de HOMOLOGAÇÃO.")
    print("Não copie credenciais neste chat nem no GitHub.")
    try:
        staging_url = input("URL HTTPS do projeto SUPABASE de homologação: ").strip()
        producao_url = input("URL HTTPS do projeto de PRODUÇÃO (somente URL, sem chave): ").strip()
        referencia = input("Repita o ID da HOMOLOGAÇÃO (subdomínio da URL): ").strip()
        print(f"Confirmação obrigatória: {CONFIRMACAO}")
        confirmacao = input("Digite a confirmação: ").strip()
        destino = validar_destinos(staging_url, producao_url, referencia, confirmacao)
        print(f"Sentinela necessária no bucket catalogo: {destino.sentinela}")
        print(f"Conteúdo EXATO da sentinela: ALPHAFEST_HF58_STAGING_ONLY:{destino.referencia}")
        resposta = input("A sentinela já está nesse bucket de TESTES? (SIM): ").strip()
        if resposta != "SIM":
            raise BloqueioHomologacao("Sentinela não confirmada; operação não iniciada.")
        chave = getpass.getpass("Chave SOMENTE do projeto de homologação (não exibida): ").strip()
        with requests.Session() as sessao:
            resultado = exercitar_upload(destino, chave, sessao)
        print(resultado)
        return 0
    except BloqueioHomologacao as exc:
        print("TESTE BLOQUEADO / NÃO APROVADO: " + str(exc))
        return 2
    except (EOFError, KeyboardInterrupt):
        print("Teste interrompido sem nova solicitação.")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
