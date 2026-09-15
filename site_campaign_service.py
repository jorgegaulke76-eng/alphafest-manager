"""HF65 — Campanha Destaque Temporária e Reutilizável do site AlphaFest.

Camada isolada: recebe a configuração persistida pelo Manager e injeta um
bloco visual auto-contido no HTML já homologado. Não altera Catálogo, Galeria,
DNS, publicação Cloudflare nem as regras comerciais existentes.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict
from urllib.parse import quote

_BASE = Path(__file__).resolve().parent
_DEFAULT_ART = _BASE / "assets" / "campaigns" / "dia_cliente_2026.webp"
_THU_ASSET = _BASE / "assets" / "mascotes" / "thu_joinha.png"
_FOX_ASSET = _BASE / "assets" / "mascotes" / "fox_galeria.webp"

DEFAULT_CAMPAIGN_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "campaign_name": "Dia do Cliente 2026",
    "headline": "",
    "message": "",
    "image_src": "__DEFAULT_DIA_CLIENTE__",
    "show_mascots": True,
    "cta_kind": "whatsapp",  # whatsapp | link | none
    "cta_text": "Quero meu voucher",
    "cta_url": "",
    "whatsapp_message": "Olá! Vi a campanha no site da AlphaFest e quero aproveitar o voucher Mini Bubble.",
    "delay_seconds": 2,
    "duration_seconds": 9,
    "show_once_per_session": True,
    "start_date": "2026-09-15",
    "end_date": "2026-09-15",
}


def normalize_campaign_config(value: Any) -> Dict[str, Any]:
    cfg = dict(DEFAULT_CAMPAIGN_CONFIG)
    if isinstance(value, dict):
        cfg.update({k: v for k, v in value.items() if v is not None})
    cfg["enabled"] = bool(cfg.get("enabled"))
    cfg["campaign_name"] = str(cfg.get("campaign_name") or "Campanha").strip()[:120]
    cfg["headline"] = str(cfg.get("headline") or "").strip()[:180]
    cfg["message"] = str(cfg.get("message") or "").strip()[:700]
    cfg["image_src"] = str(cfg.get("image_src") or "").strip()
    cfg["show_mascots"] = bool(cfg.get("show_mascots", True))
    kind = str(cfg.get("cta_kind") or "whatsapp").strip().lower()
    cfg["cta_kind"] = kind if kind in {"whatsapp", "link", "none"} else "whatsapp"
    cfg["cta_text"] = str(cfg.get("cta_text") or "").strip()[:80]
    cfg["cta_url"] = str(cfg.get("cta_url") or "").strip()[:1000]
    cfg["whatsapp_message"] = str(cfg.get("whatsapp_message") or "").strip()[:600]
    try:
        cfg["delay_seconds"] = min(15, max(0, int(cfg.get("delay_seconds", 2))))
    except Exception:
        cfg["delay_seconds"] = 2
    try:
        cfg["duration_seconds"] = min(30, max(4, int(cfg.get("duration_seconds", 9))))
    except Exception:
        cfg["duration_seconds"] = 9
    cfg["show_once_per_session"] = bool(cfg.get("show_once_per_session", True))
    for key in ("start_date", "end_date"):
        raw = str(cfg.get(key) or "").strip()
        cfg[key] = raw if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw) else ""
    return cfg


@lru_cache(maxsize=8)
def _asset_data_uri(path_text: str) -> str:
    path = Path(path_text)
    if not path.is_file():
        return ""
    ext = path.suffix.lower()
    mime = {".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(ext, "application/octet-stream")
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def default_campaign_art_data_uri() -> str:
    return _asset_data_uri(str(_DEFAULT_ART))


def _image_src(cfg: Dict[str, Any]) -> str:
    src = str(cfg.get("image_src") or "").strip()
    if src == "__DEFAULT_DIA_CLIENTE__":
        return default_campaign_art_data_uri()
    if src.startswith("data:image/") or src.startswith("https://") or src.startswith("http://"):
        return src
    return ""


def _numero_whatsapp(empresa: Dict[str, Any]) -> str:
    numero = re.sub(r"\D", "", str((empresa or {}).get("whatsapp_catalogo") or (empresa or {}).get("celular") or ""))
    if numero and not numero.startswith("55"):
        numero = "55" + numero
    return numero


def _cta_href(cfg: Dict[str, Any], empresa: Dict[str, Any]) -> str:
    kind = cfg.get("cta_kind")
    if kind == "none" or not cfg.get("cta_text"):
        return ""
    if kind == "whatsapp":
        numero = _numero_whatsapp(empresa)
        if not numero:
            return ""
        msg = str(cfg.get("whatsapp_message") or "Olá! Vim pela campanha do site da AlphaFest.").strip()
        return f"https://wa.me/{numero}?text={quote(msg)}"
    url = str(cfg.get("cta_url") or "").strip()
    return url if re.match(r"^https?://", url, flags=re.I) else ""


def _campaign_key(cfg: Dict[str, Any]) -> str:
    raw = json.dumps(
        {
            "name": cfg.get("campaign_name"),
            "img": cfg.get("image_src"),
            "start": cfg.get("start_date"),
            "end": cfg.get("end_date"),
            "cta": cfg.get("cta_text"),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def inject_campaign(page: str, config: Any, empresa: Dict[str, Any], *, force_preview: bool = False) -> str:
    """Injeta a campanha sem tocar na estrutura homologada do site.

    ``force_preview`` existe apenas para prévia interna: permite ver a animação
    mesmo enquanto a campanha ainda está desligada. A versão publicada sempre
    respeita ``enabled``.
    """
    if not page:
        return page
    cfg = normalize_campaign_config(config)
    if not cfg.get("enabled") and not force_preview:
        return page

    src = _image_src(cfg)
    headline = str(cfg.get("headline") or "").strip()
    message = str(cfg.get("message") or "").strip()
    if not src and not headline and not message:
        return page

    thu_src = _asset_data_uri(str(_THU_ASSET)) if cfg.get("show_mascots") else ""
    fox_src = _asset_data_uri(str(_FOX_ASSET)) if cfg.get("show_mascots") else ""
    cta_href = _cta_href(cfg, empresa)
    cta_text = str(cfg.get("cta_text") or "").strip()
    key = _campaign_key(cfg)

    image_html = f'<img class="afc65-art" src="{html.escape(src, quote=True)}" alt="Campanha especial AlphaFest">' if src else ""
    copy_html = ""
    if headline or message:
        copy_html = '<div class="afc65-copy">' + (f'<strong>{html.escape(headline)}</strong>' if headline else "") + (f'<span>{html.escape(message)}</span>' if message else "") + '</div>'
    cta_html = f'<a class="afc65-cta" href="{html.escape(cta_href, quote=True)}" target="_blank" rel="noopener">{html.escape(cta_text)}</a>' if cta_href and cta_text else ""
    thu_html = f'<img class="afc65-mascot afc65-thu" src="{html.escape(thu_src, quote=True)}" alt="Thu">' if thu_src else ""
    fox_html = f'<img class="afc65-mascot afc65-fox" src="{html.escape(fox_src, quote=True)}" alt="Fox">' if fox_src else ""

    cfg_js = json.dumps(
        {
            "key": key,
            "delay": int(cfg["delay_seconds"]) * 1000,
            "duration": int(cfg["duration_seconds"]) * 1000,
            "once": bool(cfg.get("show_once_per_session", True)),
            "start": cfg.get("start_date") or "",
            "end": cfg.get("end_date") or "",
            "force": bool(force_preview),
        },
        ensure_ascii=False,
    )

    block = f'''
<style id="alphafest-campaign-hf65-style">
#afc65-root{{position:fixed;inset:0;z-index:99990;display:none;pointer-events:none;font-family:Inter,Arial,sans-serif}}
#afc65-root.afc65-active{{display:block}}
#afc65-root:before{{content:"";position:absolute;inset:0;background:rgba(8,37,74,.12);opacity:0;transition:opacity .45s ease;pointer-events:none}}
#afc65-root.afc65-show:before{{opacity:1}}
.afc65-card{{position:absolute;left:50%;top:50%;width:min(620px,68vw);max-height:86vh;transform:translate(-50%,-46%) scale(.9);opacity:0;transition:transform .56s cubic-bezier(.2,.8,.2,1),opacity .42s ease;background:#fff;border-radius:28px;box-shadow:0 28px 90px rgba(14,45,82,.30);overflow:hidden;pointer-events:auto;border:1px solid rgba(255,255,255,.7)}}
#afc65-root.afc65-show .afc65-card{{transform:translate(-50%,-50%) scale(1);opacity:1}}
.afc65-art{{display:block;width:100%;max-height:72vh;object-fit:contain;background:#fff}}
.afc65-copy{{display:flex;flex-direction:column;gap:6px;padding:16px 20px 4px;text-align:center;color:#0f376c}}.afc65-copy strong{{font-size:24px}}.afc65-copy span{{font-size:15px;line-height:1.45;color:#51677f}}
.afc65-actions{{display:flex;justify-content:center;padding:14px 20px 20px}}.afc65-cta{{display:inline-flex;align-items:center;justify-content:center;background:#10a94f;color:#fff!important;text-decoration:none!important;font-weight:900;border-radius:999px;padding:13px 24px;box-shadow:0 8px 20px rgba(16,169,79,.24)}}
.afc65-close{{position:absolute;right:12px;top:12px;z-index:5;width:38px;height:38px;border-radius:50%;border:0;background:rgba(255,255,255,.96);color:#0f376c;font-size:25px;line-height:1;box-shadow:0 5px 18px rgba(12,49,91,.18);cursor:pointer}}
.afc65-mascot{{position:absolute;z-index:2;pointer-events:none;filter:drop-shadow(0 16px 20px rgba(8,37,74,.20));opacity:0;transition:transform .72s cubic-bezier(.18,.82,.18,1),opacity .42s ease}}
.afc65-thu{{left:calc(50% - 565px);bottom:3vh;height:min(66vh,610px);max-width:31vw;object-fit:contain;transform:translateX(-120vw) rotate(-4deg)}}
.afc65-fox{{right:calc(50% - 585px);bottom:6vh;width:min(350px,29vw);transform:translateX(120vw) rotate(4deg)}}
#afc65-root.afc65-show .afc65-thu{{transform:translateX(0) rotate(-2deg);opacity:1}}#afc65-root.afc65-show .afc65-fox{{transform:translateX(0) rotate(2deg);opacity:1}}
#afc65-root.afc65-leave .afc65-card{{transform:translate(-50%,-44%) scale(.93);opacity:0}}#afc65-root.afc65-leave .afc65-thu{{transform:translateX(-120vw);opacity:0}}#afc65-root.afc65-leave .afc65-fox{{transform:translateX(120vw);opacity:0}}#afc65-root.afc65-leave:before{{opacity:0}}
@media(max-width:900px){{.afc65-card{{width:min(620px,88vw)}}.afc65-thu{{left:-3vw;height:46vh;opacity:.0!important}}.afc65-fox{{right:-4vw;width:30vw;opacity:.0!important}}}}
@media(max-width:620px){{#afc65-root:before{{background:rgba(8,37,74,.08)}}.afc65-card{{width:92vw;max-height:82vh;border-radius:20px}}.afc65-art{{max-height:68vh}}.afc65-copy strong{{font-size:20px}}.afc65-copy span{{font-size:14px}}.afc65-close{{width:36px;height:36px;right:8px;top:8px}}.afc65-mascot{{display:none!important}}}}
@media(prefers-reduced-motion:reduce){{.afc65-card,.afc65-mascot,#afc65-root:before{{transition:none!important}}}}
</style>
<div id="afc65-root" aria-live="polite" aria-label="Campanha especial AlphaFest">
  {thu_html}{fox_html}
  <div class="afc65-card">
    <button class="afc65-close" type="button" aria-label="Fechar campanha">×</button>
    {image_html}{copy_html}<div class="afc65-actions">{cta_html}</div>
  </div>
</div>
<script id="alphafest-campaign-hf65-script">
(function(){{
  const C={cfg_js};
  const root=document.getElementById('afc65-root'); if(!root) return;
  function todayLocal(){{const d=new Date();const y=d.getFullYear();const m=String(d.getMonth()+1).padStart(2,'0');const day=String(d.getDate()).padStart(2,'0');return y+'-'+m+'-'+day;}}
  const td=todayLocal(); if(!C.force && ((C.start&&td<C.start)||(C.end&&td>C.end))) return;
  const storageKey='af_campaign_seen_'+C.key;
  if(!C.force && C.once){{try{{if(sessionStorage.getItem(storageKey)==='1') return;}}catch(e){{}}}}
  let closed=false, timer=null;
  function markSeen(){{if(!C.force && C.once){{try{{sessionStorage.setItem(storageKey,'1');}}catch(e){{}}}}}}
  function hide(){{if(closed)return;closed=true;root.classList.add('afc65-leave');root.classList.remove('afc65-show');if(timer)clearTimeout(timer);setTimeout(function(){{root.className='';root.style.display='none';}},760);}}
  function show(){{if(closed)return;markSeen();root.classList.add('afc65-active');requestAnimationFrame(function(){{requestAnimationFrame(function(){{root.classList.add('afc65-show');}});}});timer=setTimeout(hide,C.duration);}}
  const close=root.querySelector('.afc65-close'); if(close) close.addEventListener('click',hide);
  const cta=root.querySelector('.afc65-cta'); if(cta) cta.addEventListener('click',function(){{setTimeout(hide,160);}});
  setTimeout(show,C.delay);
}})();
</script>
'''
    if "</body>" in page:
        return page.replace("</body>", block + "</body>", 1)
    return page + block
