"""HF65.24.25 — vitrine de entrega rápida, sem cadastro paralelo."""
from __future__ import annotations
import html
import json
from site_vitrine_service import selecionar_produtos_vitrine

STYLE = """
.af-fast{background:#eff8ff;padding:38px 20px 45px;scroll-margin-top:135px}
.af-fast-inner{max-width:1240px;margin:auto}
.af-fast h2{margin:0 0 8px;color:#13538b;font-size:clamp(25px,3vw,35px)}
.af-fast .af-fast-lead{color:#45637b;margin:0 0 22px;font-size:14px}
.af-fast-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.af-fast-card{background:white;border:1px solid #d7eafa;border-radius:17px;padding:12px;display:flex;flex-direction:column;box-shadow:0 8px 22px #10476b0c}
.af-fast-photo{aspect-ratio:1/1;border-radius:12px;background:#f5faff;overflow:hidden;display:grid;place-items:center}
.af-fast-photo img{width:100%;height:100%;object-fit:contain}
.af-fast-card strong{display:block;margin:12px 2px;color:#193e62;font-size:15px}
.af-fast-card small{display:block;color:#647990;margin:0 2px 12px}
.af-fast-card button{margin-top:auto;border:0;background:#087bd1;color:white;border-radius:10px;padding:12px;cursor:pointer;font-weight:800}
.af-fast-card button:hover{background:#0564b1}
@media(max-width:850px){.af-fast-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:460px){.af-fast-grid{gap:8px}.af-fast-card{padding:8px}.af-fast-card strong{font-size:13px}.af-fast-card button{font-size:12px;padding:10px 7px}}
"""
SCRIPT = """
(function(){
 document.querySelectorAll('.af-fast-open').forEach(function(btn){
  btn.addEventListener('click',function(){
   const nome=this.getAttribute('data-name')||'';
   const original=[...document.querySelectorAll('#produtos .product-card')].find(function(c){return c.dataset.detailName===nome});
   if(!original){document.getElementById('produtos')?.scrollIntoView({behavior:'smooth'});return;}
   if(original.style.display==='none'){
     const all=document.querySelector('.filter[data-cat="todos"]');if(all)all.click();
     const query=document.getElementById('search');if(query){query.value='';query.dispatchEvent(new Event('input',{bubbles:true}));}
   }
   document.getElementById('produtos')?.scrollIntoView({behavior:'smooth',block:'start'});
   setTimeout(function(){original.click()},160);
  });
 });
})();
"""

def inject_fast_delivery(pagina, catalogo):
    elegiveis = selecionar_produtos_vitrine(catalogo, usar_taxonomia_catalogo=True)
    # Só produtos marcados explicitamente para entrega rápida; não inferir disponibilidade pelo nome.
    marcados = {str(p.get('Nome') or '').strip() for p in catalogo if isinstance(p, dict) and p.get('EntregaRapidaSite')}
    escolhidos = [p for p in elegiveis if str(p.get('nome') or '').strip() in marcados][:12]
    if not escolhidos:
        return pagina
    cards=[]
    for p in escolhidos:
        nome=str(p.get('nome') or '').strip()
        imagem=str(p.get('imagem_principal') or '').strip()
        # Preferir src da ficha já gerada e resolvida; não expor caminhos locais.
        from re import search, escape
        trecho=search(r'<article\s+class="product-card[^>]*data-detail-name="'+escape(html.escape(nome,quote=True))+r'".*?</article>',pagina,flags=__import__('re').S)
        if not trecho:
            continue
        foto=search(r'<div class="photo">(.*?)</div>',trecho.group(0),flags=__import__('re').S)
        imagem_html=foto.group(1) if foto else '<span>AlphaFest</span>'
        cards.append('<article class="af-fast-card"><div class="af-fast-photo">'+imagem_html+'</div><strong>'+html.escape(nome)+'</strong><small>Produção sob consulta · confirme o prazo</small><button class="af-fast-open" data-name="'+html.escape(nome,quote=True)+'" type="button">Ver produto e adicionar ao orçamento</button></article>')
    if not cards:
        return pagina
    sec='<section class="af-fast" id="entrega-rapida"><div class="af-fast-inner"><h2>⚡ Ideias para entrega rápida</h2><p class="af-fast-lead">Selecionamos opções para sua próxima comemoração. Disponibilidade e prazo são confirmados pela AlphaFest no atendimento.</p><div class="af-fast-grid">'+''.join(cards)+'</div></div></section>'
    target='<main class="main" id="produtos">'
    if target not in pagina:
        return pagina
    pagina=pagina.replace(target,sec+target,1)
    pagina=pagina.replace('</head>','<style id="af-fast-style">'+STYLE+'</style></head>',1)
    pagina=pagina.replace('</body>','<script id="af-fast-script">'+SCRIPT+'</script></body>',1)
    return pagina
