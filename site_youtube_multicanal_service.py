"""HF65.22 — prepara Shorts originais e upload autorizado para canal YouTube.

Upload NUNCA e acionado automaticamente ao salvar ou publicar conteudo no site.
A comunicacao com a API depende de autorizacao OAuth do proprietario do canal.
"""
from __future__ import annotations

import io
import os
import re
import tempfile
import textwrap
from pathlib import Path
from typing import Any, Dict

import requests

from site_dicas_multicanal_service import youtube_export_text, CANAL_YOUTUBE_OFICIAL

YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def exportar_pacote_youtube(artigo: Dict[str, str]) -> bytes:
    """Pacote editorial de uma dica; nao requer acesso ao canal."""
    import zipfile
    d = youtube_export_text(artigo)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("01-roteiro-short.txt", d["script"] + "\n")
        z.writestr("02-titulo.txt", d["title"] + "\n")
        z.writestr("03-descricao.txt", d["description"] + "\n")
        z.writestr("04-link-site.txt", d["source_url"] + "\n")
        z.writestr("05-canal-youtube.txt", CANAL_YOUTUBE_OFICIAL + "\n")
        z.writestr("LEIA_ME.txt", "Conteudo original AlphaFest, para revisao antes de publicar no YouTube.\n"
                    "Destino pretendido: " + CANAL_YOUTUBE_OFICIAL + "\n"
                    "Este pacote nao foi enviado ao canal. Adicione imagens/locucao propria se desejar.\n")
    return buf.getvalue()


def _font(size: int, bold: bool = False):
    from PIL import ImageFont
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for name in candidates:
        if Path(name).exists():
            return ImageFont.truetype(name, size=size)
    return ImageFont.load_default()


def _lines(draw, text: str, font, max_width: int):
    words = str(text).split()
    lines, line = [], ""
    for word in words:
        trial = (line + " " + word).strip()
        if draw.textbbox((0,0), trial, font=font)[2] <= max_width or not line:
            line = trial
        else:
            lines.append(line);line = word
    if line: lines.append(line)
    return lines


def _slide(img, title: str, subtitle: str, index: int, total: int):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    w,h = img.size
    draw.rounded_rectangle((34,47,w-34,h-47),radius=32,fill=(246,251,255))
    draw.rounded_rectangle((34,47,w-34,194),radius=32,fill=(5,93,167))
    draw.rectangle((34,150,w-34,194),fill=(5,93,167))
    draw.text((70,95),"ALPHAFEST  |  DICAS",font=_font(27,True),fill="white")
    font_title=_font(48,True)
    y=300
    for line in _lines(draw,title,font_title,w-145)[:6]:
        draw.text((74,y),line,font=font_title,fill=(6,70,123))
        y+=65
    font_sub=_font(30)
    y=max(595,y+24)
    for line in _lines(draw,subtitle,font_sub,w-145)[:8]:
        draw.text((74,y),line,font=font_sub,fill=(34,87,125))
        y+=46
    draw.rounded_rectangle((70,h-200,w-70,h-118),radius=20,fill=(6,105,183))
    draw.text((95,h-182),"alphafest.com.br",font=_font(31,True),fill="white")
    draw.text((72,h-92),f"{index} / {total}   •   Estamos presentes em cada presente!",font=_font(18),fill=(73,113,145))


def gerar_short_mp4(artigo: Dict[str,str], *, seconds_per_slide: int = 4, fps: int = 8) -> bytes:
    """Gera video vertical silencioso com texto original; nunca publica no YouTube.

    Utiliza opencv-python-headless e pillow, ja previstos nas dependencias do Manager.
    Possui limite de tamanho/duracao para evitar travar a aplicacao.
    """
    import cv2
    import numpy as np
    from PIL import Image
    title = str(artigo.get("title") or "Dicas AlphaFest")[:130]
    script = str(artigo.get("script") or "").strip()
    if not script: raise ValueError("Roteiro vazio: edite a dica antes de gerar um Short.")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+",script) if s.strip()]
    # Texto da capa + ate 5 mensagens + final (maximo de 7 slides = 28s)
    sections = [(title,"Dicas rápidas para o seu evento")]
    for sent in sentences[:5]:
        sections.append((sent,""))
    sections.append(("Gostou da dica?","Veja mais ideias e personalizados no nosso site."))
    w,h = 540,960
    with tempfile.TemporaryDirectory(prefix="alphafest_youtube_") as folder:
        path=os.path.join(folder,"alpha_short.mp4")
        writer=cv2.VideoWriter(path,cv2.VideoWriter_fourcc(*"mp4v"),float(fps),(w,h))
        if not writer.isOpened(): raise RuntimeError("Este servidor nao possui codec de video MP4; use o pacote editorial.")
        try:
            for i,(heading,sub) in enumerate(sections,1):
                frame=Image.new("RGB",(w,h),(217,240,252))
                _slide(frame,heading,sub,i,len(sections))
                bgr=cv2.cvtColor(np.asarray(frame),cv2.COLOR_RGB2BGR)
                for _ in range(int(fps*seconds_per_slide)):
                    writer.write(bgr)
        finally:
            writer.release()
        raw=Path(path).read_bytes()
    if len(raw)<1000: raise RuntimeError("Falha na geracao do arquivo MP4.")
    return raw


def _youtube_access_token(credentials: Dict[str, str], timeout: int = 18) -> str:
    """Renova token OAuth obtido pelo proprietario do canal; nunca usa login/senha."""
    keys = ("client_id","client_secret","refresh_token")
    if any(not str(credentials.get(k) or "").strip() for k in keys):
        raise ValueError("YouTube ainda nao conectado pelo proprietario do canal (OAuth).")
    r=requests.post("https://oauth2.googleapis.com/token",timeout=timeout,data={
        "grant_type":"refresh_token",**{k:credentials[k] for k in keys},
    })
    r.raise_for_status()
    token = r.json().get("access_token")
    if not token: raise RuntimeError("Google nao retornou autorizacao para upload.")
    return str(token)


def publicar_video_privado_youtube(
    video_mp4: bytes, artigo: Dict[str,str], credentials: Dict[str,str], timeout: int = 120
) -> str:
    """Envia MP4 somente em modo PRIVADO e somente quando o usuario clicar em enviar.

    Requer escopo OAuth youtube.upload autorizado previamente. Codigo de cliente
    e refresh_token ficam apenas em Streamlit Secrets, nao no banco editorial.
    """
    if len(video_mp4)>80_000_000: raise ValueError("Video maior que o limite seguro de 80MB.")
    if not video_mp4: raise ValueError("Nenhum video foi enviado.")
    token=_youtube_access_token(credentials)
    data=youtube_export_text(artigo)
    req={"snippet":{"title":data["title"],"description":data["description"],"categoryId":"26"},
         "status":{"privacyStatus":"private","selfDeclaredMadeForKids":False}}
    headers={"Authorization":"Bearer "+token,"X-Upload-Content-Length":str(len(video_mp4)),
             "X-Upload-Content-Type":"video/mp4","Content-Type":"application/json"}
    r=requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                    json=req,headers=headers,timeout=20)
    r.raise_for_status()
    url=r.headers.get("Location")
    if not url or not url.startswith("https://www.googleapis.com/"):
        raise RuntimeError("A API nao retornou um destino de upload confiavel.")
    done=requests.put(url,data=video_mp4,headers={"Authorization":"Bearer "+token,
        "Content-Length":str(len(video_mp4)),"Content-Type":"video/mp4"},timeout=timeout)
    done.raise_for_status()
    vid=str(done.json().get("id") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}",vid):
        raise RuntimeError("O YouTube nao confirmou o identificador do video.")
    return vid
