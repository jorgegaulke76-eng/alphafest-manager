"""Guarda PDFs DAS em bucket privado; nunca cria URLs públicas.
Apenas chamadas no backend com chave service_role. Uma gravação rejeitada não tem fallback local.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from urllib.parse import quote
import requests
import cloud_db
BUCKET="das-mei-privado"

def _connection():
    if cloud_db.credential_mode() != 'service':
        raise RuntimeError('Armazenamento DAS exige chave de servidor no Streamlit Secrets')
    url,_=cloud_db._config()
    return url, cloud_db._headers()

def _bucket():
    url,headers=_connection()
    req=cloud_db._SESSION.get(f'{url}/storage/v1/bucket/{BUCKET}',headers=headers,timeout=15)
    if req.ok:
        info=req.json()
        if info.get('public'): raise RuntimeError('Bucket fiscal não pode ser público')
        return
    if req.status_code not in (400,404): req.raise_for_status()
    req=cloud_db._SESSION.post(f'{url}/storage/v1/bucket',headers=headers,json={'id':BUCKET,'name':BUCKET,'public':False},timeout=15)
    if not req.ok and req.status_code != 409: req.raise_for_status()

def upload(pdf,competencia,tipo):
    if pdf is None: return ''
    raw=bytes(pdf.getbuffer())
    if not raw.startswith(b'%PDF-') or len(raw)>8*1024*1024:
        raise ValueError('Selecione um PDF válido de até 8 MB')
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',str(competencia)) or tipo not in ('guia','comprovante'):
        raise ValueError('Documento fiscal inválido')
    _bucket()
    path=f'{competencia}/{tipo}-{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")}.pdf'
    url,headers=_connection()
    r=cloud_db._SESSION.post(f'{url}/storage/v1/object/{BUCKET}/{quote(path,safe="/")}',headers={**headers,'Content-Type':'application/pdf','x-upsert':'false'},data=raw,timeout=45)
    r.raise_for_status()
    return path

def download(path):
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])/(guia|comprovante)-\d+\.pdf',str(path)):
        raise ValueError('Caminho de documento inválido')
    url,headers=_connection()
    r=cloud_db._SESSION.get(f'{url}/storage/v1/object/{BUCKET}/{quote(path,safe="/")}',headers=headers,timeout=45)
    r.raise_for_status()
    return bytes(r.content)
