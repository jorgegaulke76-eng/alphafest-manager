#!/usr/bin/env python3
"""Homologacao HF58 RC4: preflight fechado para um pacote RC4 exato.

Sem conexao ao banco, sem acesso a API, sem publicar e sem modificar dados.
"""
import hashlib
import json
import os
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
EXPECTED_MANIFEST_SHA256 = '62772e0b495d190deda7cbc27744f4d247382700d97836655f45753d5025a7da'
EXPECTED_VERSION = '20.4.9-I8.13.5-HF53.3-HF8-HF65.24.58'


def fail(message):
    print('BLOQUEADO:', message, flush=True)
    raise SystemExit(2)


def check():
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        if os.environ.get('GITHUB_REF') != 'refs/heads/homologacao-hf58':
            fail('Execucao remota apenas na branch homologacao-hf58.')
    for key in ('SUPABASE_URL', 'SUPABASE_KEY', 'SUPABASE_ANON_KEY',
                'SUPABASE_SERVICE_KEY', 'SUPABASE_SERVICE_ROLE_KEY'):
        if os.environ.get('GITHUB_ACTIONS') == 'true' and os.environ.get(key):
            fail(f'A variavel {key} nao pode estar preenchida no runner.')
    for name in ('.env', '.env.local', 'credentials.json', 'service-account.json',
                 '.streamlit/secrets.toml'):
        if (ROOT / name).exists():
            fail(f'Arquivo de credenciais inesperado: {name}.')
    for p in ROOT.rglob('*'):
        if not p.is_file() or '.git' in p.parts:
            continue
        if p.name in {'secrets.toml', 'service-account.json', 'credentials.json'}:
            fail(f'Arquivo sensivel detectado: {p.relative_to(ROOT)}')
    manifest_path = ROOT / 'UPDATE_MANIFEST.json'
    if not manifest_path.is_file():
        fail('Manifesto RC4 nao encontrado.')
    blob = manifest_path.read_bytes()
    if hashlib.sha256(blob).hexdigest() != EXPECTED_MANIFEST_SHA256:
        fail('O manifesto RC4 foi alterado; use o pacote original.')
    manifest = json.loads(blob)
    files = manifest.get('files') or []
    if manifest.get('version') != EXPECTED_VERSION:
        fail('Versao incorreta no manifesto.')
    if manifest.get('validation', {}).get('status') != 'HOMOLOGACAO_PARCIAL':
        fail('O pacote precisa continuar como HOMOLOGACAO_PARCIAL.')
    if manifest.get('file_count') != 522 or len(files) != 522:
        fail('Quantidade de arquivos do pacote RC4 alterada.')
    if any((ROOT / f).read_text(encoding='utf-8').strip() != EXPECTED_VERSION
           for f in ('VERSAO', 'VERSAO.txt')):
        fail('VERSAO e VERSAO.txt precisam indicar RC4.')
    seen=set()
    for item in files:
        rel=str(item.get('path') or '')
        pure=PurePosixPath(rel)
        if not rel or pure.is_absolute() or '..' in pure.parts or rel in seen:
            fail('Caminho invalido no manifesto: '+rel)
        seen.add(rel)
        f=ROOT.joinpath(*pure.parts)
        if not f.is_file():
            fail('Arquivo do RC4 ausente: '+rel)
        if f.stat().st_size != item.get('size'):
            fail('Arquivo com tamanho divergente: '+rel)
        hash_arquivo=hashlib.sha256(f.read_bytes()).hexdigest()
        if hash_arquivo != item.get('sha256'):
            fail('Arquivo foi alterado: '+rel)
    print(f'PREFLIGHT APROVADO - {len(files)} arquivos RC4 conferidos contra hashes SHA-256.', flush=True)
    print('Confirmada branch de homologacao quando no GitHub Actions; dados sensiveis basicos ausentes.', flush=True)
    print('Status do pacote permanece HOMOLOGACAO_PARCIAL; nenhuma instalacao autorizada.', flush=True)
    return 0

if __name__ == '__main__':
    sys.exit(check())
